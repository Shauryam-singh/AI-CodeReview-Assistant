import logging
import re

# Initialize logger
logger = logging.getLogger(__name__)

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_commentable_lines(diff_text):
    """Walk unified-diff hunks and collect line numbers a PR review may
    anchor to: {"path": {"RIGHT": set(...), "LEFT": set(...)}}.

    RIGHT holds new-file lines (added + context), LEFT holds old-file lines
    (deleted + context). GitHub rejects inline comments on lines outside
    these ranges with 422, so callers filter against this map first.
    """
    files = {}
    path = None
    in_hunk = False
    old_no = new_no = 0

    if not diff_text:
        return {}

    lines = diff_text.split("\n")
    if lines and lines[-1] == "":
        # artifact of the trailing newline, not a blank context line
        lines = lines[:-1]

    for line in lines:
        if line.startswith("diff --git "):
            in_hunk = False
            parts = line.split(" ")
            if len(parts) > 3:
                raw_path = parts[3]
                path = raw_path[2:] if raw_path.startswith("b/") else raw_path
                files.setdefault(path, {"RIGHT": set(), "LEFT": set()})
            else:
                path = None
            continue

        match = _HUNK_RE.match(line)
        if match:
            if path is None:
                in_hunk = False
                continue
            old_no = int(match.group(1))
            new_no = int(match.group(2))
            in_hunk = True
            files.setdefault(path, {"RIGHT": set(), "LEFT": set()})
            continue

        if not in_hunk or path is None:
            continue

        if line.startswith("+"):
            files[path]["RIGHT"].add(new_no)
            new_no += 1
        elif line.startswith("-"):
            files[path]["LEFT"].add(old_no)
            old_no += 1
        elif line.startswith("\\"):
            continue  # "\ No newline at end of file"
        elif line.startswith(" ") or line == "":
            files[path]["RIGHT"].add(new_no)
            files[path]["LEFT"].add(old_no)
            new_no += 1
            old_no += 1
        else:
            in_hunk = False

    logger.info(
        "Commentable lines parsed for %d file(s).", sum(1 for f in files.values() if f["RIGHT"] or f["LEFT"])
    )
    return files


def parse_diff(diff_text):
    files = {}
    current_file = None
    
    if not diff_text:
        logger.warning("No diff text provided to parse_diff.")
        return {}

    lines = diff_text.split("\n")
    logger.info(f"Parsing diff: {len(lines)} lines detected.")

    for line in lines:
        if line.startswith("diff --git"):
            parts = line.split(" ")
            if len(parts) > 2:
                # Use the 'b' path as the file identifier
                # Handle cases where path might be prefixed with b/
                raw_path = parts[3]
                current_file = raw_path[2:] if raw_path.startswith("b/") else raw_path
                
                files[current_file] = []
                logger.debug(f"Found modified file: {current_file}")
                
        elif current_file:
            # Skip the '---' and '+++' headers in the diff
            if line.startswith("+++") or line.startswith("---"):
                continue
                
            if line.startswith("+") or line.startswith("-"):
                files[current_file].append(line)

    # Summary Log
    detected_files = list(files.keys())
    logger.info(f"Diff parsing complete. Files identified: {len(detected_files)}")
    if detected_files:
        logger.debug(f"Files list: {detected_files}")
    else:
        logger.warning("Diff parser found 0 files. Check if the diff format is standard git.")

    return files