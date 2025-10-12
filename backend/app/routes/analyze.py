from fastapi import APIRouter, Query
import tempfile
import subprocess
import shutil
import os
import json
from git import Repo

router = APIRouter()

# Map file extensions to analyzers
ANALYZERS = {
    ".py": {
        "name": "Python",
        "commands": [
            ("bandit", ["bandit", "-r", "{file}", "-f", "json"]),
            ("pylint", ["pylint", "{file}", "--output-format=json", "--disable=import-error"])
        ]
    },
    ".js": {
        "name": "JavaScript",
        "commands": [
            ("eslint", [r"C:\Users\shaur\AppData\Roaming\npm\eslint.cmd", "{file}", "-c", "{config}", "-f", "json"])
        ]
    },
    ".ts": {
        "name": "TypeScript",
        "commands": [
            ("eslint", [r"C:\Users\shaur\AppData\Roaming\npm\eslint.cmd", "{file}", "-c", "{config}", "-f", "json"])
        ]
    }
}

def get_files_by_language(path: str):
    """Return a dict of language -> list of file paths."""
    files_dict = {}
    for root, _, files in os.walk(path):
        for f in files:
            ext = os.path.splitext(f)[1]
            if ext in ANALYZERS:
                files_dict.setdefault(ext, []).append(os.path.join(root, f))
    return files_dict

def run_tool(tool_name, cmd_template, file_path, config=None):
    """Run a tool on a single file and return JSON output or error."""
    cmd = [arg.format(file=file_path, config=config) for arg in cmd_template]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
        return output.decode("utf-8")
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8") if e.output else f"Error running {' '.join(cmd)}"
    except FileNotFoundError:
        return f"Tool '{tool_name}' not installed or path is incorrect."

def parse_output(tool_name, file_path, output):
    """Parse analyzer output into structured issues."""
    parsed = []
    try:
        data = json.loads(output)
        if tool_name == "bandit":
            for r in data.get("results", []):
                parsed.append({
                    "tool": tool_name,
                    "line": r.get("line_number"),
                    "column": None,
                    "type": "security",
                    "message": r.get("issue_text"),
                    "severity": r.get("issue_severity"),
                    "confidence": r.get("issue_confidence")
                })
        elif tool_name == "pylint":
            for r in data:
                parsed.append({
                    "tool": tool_name,
                    "line": r.get("line"),
                    "column": r.get("column"),
                    "type": r.get("type"),
                    "message": r.get("message"),
                    "symbol": r.get("symbol")
                })
        elif tool_name == "eslint":
            for r in data:
                for msg in r.get("messages", []):
                    parsed.append({
                        "tool": tool_name,
                        "line": msg.get("line"),
                        "column": msg.get("column"),
                        "type": "error" if msg.get("severity") == 2 else "warning",
                        "message": msg.get("message")
                    })
    except Exception:
        parsed.append({
            "tool": tool_name,
            "line": None,
            "column": None,
            "type": "unknown",
            "message": output
        })
    return parsed

@router.get("/analyze")
def analyze_repo(repo_url: str = Query(..., description="GitHub repository URL")):
    temp_dir = tempfile.mkdtemp()
    results = {}
    summary = {}

    try:
        # Clone repository
        Repo.clone_from(repo_url, temp_dir)

        # Detect files
        files_by_lang = get_files_by_language(temp_dir)
        if not files_by_lang:
            return {"status": "success", "repo": repo_url, "results": {}, "summary": {}, "message": "No supported files found."}

        # JS/TS dependencies (optional)
        eslint_config_path = None
        if any(ext in files_by_lang for ext in [".js", ".ts"]):
            pkg_json = os.path.join(temp_dir, "package.json")
            if os.path.exists(pkg_json):
                subprocess.run(["npm", "install"], cwd=temp_dir, check=False, shell=True)

            # Create temporary ESLint config if missing
            eslint_config_path = os.path.join(temp_dir, "eslint.config.js")
            if not os.path.exists(eslint_config_path):
                with open(eslint_config_path, "w") as f:
                    f.write("""
module.exports = {
  root: true,
  env: { node: true, es2021: true },
  extends: ["eslint:recommended"],
  parserOptions: { ecmaVersion: 12, sourceType: "module" },
  rules: {}
};
""")

        # Analyze each file individually
        for ext, files in files_by_lang.items():
            lang_name = ANALYZERS[ext]["name"]
            results[lang_name] = []
            total_issues = 0

            for file_path in files:
                rel_path = os.path.relpath(file_path, temp_dir)  # relative to repo root
                file_issues = []
                for tool_name, cmd_template in ANALYZERS[ext]["commands"]:
                    if tool_name == "eslint":
                        cmd = [arg.format(file=rel_path, config=eslint_config_path) for arg in cmd_template]
                        try:
                            output = subprocess.check_output(
                                cmd, stderr=subprocess.STDOUT, shell=True, cwd=temp_dir
                            ).decode("utf-8")
                        except subprocess.CalledProcessError as e:
                            output = e.output.decode("utf-8") if e.output else f"Error running {' '.join(cmd)}"
                        except FileNotFoundError:
                            output = f"Tool '{tool_name}' not installed or path is incorrect."
                    else:
                        output = run_tool(tool_name, cmd_template, file_path)

                    parsed = parse_output(tool_name, file_path, output)
                    file_issues.extend(parsed)
                    total_issues += len(parsed)

                results[lang_name].append({
                    "file": rel_path,
                    "path": file_path,
                    "issues": file_issues
                })

            summary[lang_name] = {
                "files_analyzed": len(files),
                "total_issues": total_issues
            }

        return {
            "status": "success",
            "repo": repo_url,
            "languages": list(results.keys()),
            "summary": summary,
            "results": results
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
