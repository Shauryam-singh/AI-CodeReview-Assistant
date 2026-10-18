import ast
import os
from app.services.limits import MAX_FILE_SIZE_BYTES, MAX_SCAN_FILES

def scan_single_file_ast(repo_path, rel_path):
    findings = []
    full_path = os.path.join(repo_path, rel_path)

    if not rel_path.endswith(".py") or not os.path.exists(full_path):
        return []

    if os.path.getsize(full_path) > MAX_FILE_SIZE_BYTES:
        return []

    try:
        with open(full_path, "r", encoding="utf-8") as file:
            tree = ast.parse(file.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                
                if func_name in ["eval", "exec"]:
                    findings.append({
                        "file": rel_path,
                        "line": node.lineno,
                        "message": f"Dangerous function '{func_name}' detected.",
                        "severity": "HIGH",
                        "tool": "python-ast"
                    })
    except Exception:
        pass
    return findings

def scan_python_ast(path):
    findings = []
    scanned = 0

    for root, _, files in os.walk(path):
        if scanned >= MAX_SCAN_FILES:
            print(f"AST scan capped at {MAX_SCAN_FILES} files.")
            return findings
        for f in files:
            if scanned >= MAX_SCAN_FILES:
                break
            if f.endswith(".py"):
                full_path = os.path.join(root, f)
                relative_path = os.path.relpath(full_path, path)
                scanned += 1
                try:
                    if os.path.getsize(full_path) > MAX_FILE_SIZE_BYTES:
                        continue
                    with open(full_path, "r", encoding="utf-8") as file:
                        tree = ast.parse(file.read())
                    
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            func_name = ""
                            if isinstance(node.func, ast.Name):
                                func_name = node.func.id
                            
                            if func_name in ["eval", "exec"]:
                                findings.append({
                                    "file": relative_path,
                                    "line": node.lineno,
                                    "message": f"Dangerous function '{func_name}' can lead to Remote Code Execution.",
                                    "severity": "HIGH",
                                    "tool": "python-ast"
                                })
                except Exception:
                    continue
    return findings