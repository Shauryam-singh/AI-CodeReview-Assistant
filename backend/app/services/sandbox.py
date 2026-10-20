import os
import signal
import subprocess
import sys
import shutil

SANDBOX_MEMORY_MB = int(os.getenv("SANDBOX_MEMORY_MB", "1024"))
# RLIMIT_NPROC counts threads too (Linux), and FastAPI's threadpool alone
# defaults to 40 — 64 was too low and made git unable to fork remote helpers.
SANDBOX_MAX_PROCS = int(os.getenv("SANDBOX_MAX_PROCS", "256"))
SANDBOX_NO_NETWORK = os.getenv("SANDBOX_NO_NETWORK", "0") == "1"


class SandboxedProcess:
    """Popen wrapper that kills the whole process tree on timeout/exit."""

    def __init__(self, popen, posix_group=False):
        self.popen = popen
        self.posix_group = posix_group

    def communicate(self, timeout=None):
        return self.popen.communicate(timeout=timeout)

    def kill_tree(self):
        try:
            if self.posix_group:
                os.killpg(self.popen.pid, signal.SIGKILL)
            elif sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/PID", str(self.popen.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=10,
                )
            else:
                self.popen.kill()
        except Exception:
            try:
                self.popen.kill()
            except Exception:
                pass


def _windows_job_object(process, memory_mb, max_procs):
    """Attach process to a Windows Job Object with memory/process caps.

    Best-effort: any failure just means the process runs without the extra
    limits (timeouts still apply)."""
    import ctypes
    from ctypes import wintypes

    JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
    JOB_OBJECT_LIMIT_ACTIVE_PROCESS = 0x00000008
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [("ReadOperationCount", ctypes.c_uint64),
                    ("WriteOperationCount", ctypes.c_uint64),
                    ("OtherOperationCount", ctypes.c_uint64),
                    ("ReadTransferCount", ctypes.c_uint64),
                    ("WriteTransferCount", ctypes.c_uint64),
                    ("OtherTransferCount", ctypes.c_uint64)]

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD)]

    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t)]

    kernel32 = ctypes.windll.kernel32
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        return False

    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = (
        JOB_OBJECT_LIMIT_PROCESS_MEMORY
        | JOB_OBJECT_LIMIT_ACTIVE_PROCESS
        | JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    )
    info.BasicLimitInformation.ActiveProcessLimit = max_procs
    info.ProcessMemoryLimit = memory_mb * 1024 * 1024

    if not kernel32.SetInformationJobObject(
        job, 9, ctypes.byref(info), ctypes.sizeof(info)
    ):
        kernel32.CloseHandle(job)
        return False

    # Small race: process may run briefly before assignment. Acceptable —
    # limits still apply for the rest of (typically long) scan/clone runs.
    if not kernel32.AssignProcessToJobObject(job, process._handle):
        kernel32.CloseHandle(job)
        return False
    return True


def _build_linux_wrapper(cmd, network=True):
    """Thread-safe resource limits via prlimit(1) or sh+ulimit.

    (preexec_fn is unsafe with FastAPI's threadpool, so we avoid it.)"""
    mem_kb = SANDBOX_MEMORY_MB * 1024
    fsize_blocks = SANDBOX_MEMORY_MB * 2048  # POSIX: ulimit -f is 512B units

    if shutil.which("prlimit"):
        wrapped = [
            "prlimit",
            f"--as={mem_kb * 1024}",
            f"--fsize={fsize_blocks * 512}",
            f"--nproc={SANDBOX_MAX_PROCS}",
            "--",
        ] + list(cmd)
    else:
        wrapped = [
            "sh", "-c",
            'ulimit -v {vm} -f {fs} 2>/dev/null; exec "$@"'.format(
                vm=mem_kb, fs=fsize_blocks
            ),
            "sandbox",
        ] + list(cmd)

    # Block network when the caller doesn't need it (scans), or when
    # explicitly configured. Clone/semgrep-auto need network, so they pass
    # network=True and are only isolated if SANDBOX_NO_NETWORK=1.
    if (not network or SANDBOX_NO_NETWORK) and shutil.which("unshare"):
        wrapped = ["unshare", "--net", "--"] + wrapped
    return wrapped


def sandboxed_run(cmd, timeout, cwd=None, network=True, limits=True):
    """Run cmd with resource limits + hard timeout, killing the whole tree.

    - Linux (Render): prlimit/sh ulimit caps for memory, file size, procs;
      optional network namespace when SANDBOX_NO_NETWORK=1 or network=False.
    - Windows: Job Object memory/process caps + taskkill tree-kill.
    - Always: wall-clock timeout with process-tree kill.
    - limits=False: skip the memory/process caps (timeout + tree-kill still
      apply) — used as a retry path when the container itself refuses forks.
    """
    cmd = [str(c) for c in cmd]
    posix_group = False

    if sys.platform == "win32":
        final_cmd = cmd
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    else:
        if limits:
            final_cmd = _build_linux_wrapper(cmd, network=network)
        else:
            # No prlimit/ulimit, but keep network isolation if requested.
            final_cmd = list(cmd)
            if (not network or SANDBOX_NO_NETWORK) and shutil.which("unshare"):
                final_cmd = ["unshare", "--net", "--"] + final_cmd
        posix_group = True
        creationflags = 0

    popen = subprocess.Popen(
        final_cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="ignore",
        start_new_session=posix_group,
        creationflags=creationflags,
    )

    if sys.platform == "win32" and limits:
        _windows_job_object(popen, SANDBOX_MEMORY_MB, SANDBOX_MAX_PROCS)

    proc = SandboxedProcess(popen, posix_group=posix_group)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, popen.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        proc.kill_tree()
        try:
            proc.communicate(timeout=10)
        except Exception:
            pass
        raise
