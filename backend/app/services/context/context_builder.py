import logging

logger = logging.getLogger(__name__)

def parse_diff(diff_text):
    """Parses raw diff text into a dict of {filename: [lines]}."""
    files = {}
    current_file = None
    
    if not diff_text:
        return {}

    for line in diff_text.split("\n"):
        if line.startswith("diff --git"):
            parts = line.split(" ")
            if len(parts) > 2:
                # Safely extract path: b/folder/file.py -> folder/file.py
                b_path = parts[3]
                current_file = b_path[2:] if b_path.startswith("b/") else b_path
                files[current_file] = []
        elif current_file:
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+") or line.startswith("-"):
                files[current_file].append(line)
    
    logger.info(f"Parsed {len(files)} changed files from diff.")
    return files

def build_repo_context(repo_path, diff_text, commits):
    """Combines all PR data into a single context object."""
    return {
        "diff": parse_diff(diff_text),
        "diff_text": diff_text or "",
        "commits": commits,
        "repo_path": repo_path
    }