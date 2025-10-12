from fastapi import APIRouter, Query
import requests
import tempfile
import subprocess
import os
import json

router = APIRouter()

ANALYZERS = {
    ".py": { "name": "Python", "commands": [("bandit", ["bandit", "-r", "{file}", "-f", "json"]), ("pylint", ["pylint", "{file}", "--output-format=json", "--disable=import-error"])] },
    ".js": { "name": "JavaScript", "commands": [("eslint", [r"C:\Users\shaur\AppData\Roaming\npm\eslint.cmd", "{file}", "-c", "{config}", "-f", "json"])] },
    ".ts": { "name": "TypeScript", "commands": [("eslint", [r"C:\Users\shaur\AppData\Roaming\npm\eslint.cmd", "{file}", "-c", "{config}", "-f", "json"])] },
}

def run_tool(tool_name, cmd_template, file_path, config=None, cwd=None):
    cmd = [arg.format(file=file_path, config=config) for arg in cmd_template]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, cwd=cwd)
        return output.decode("utf-8")
    except subprocess.CalledProcessError as e:
        return e.output.decode("utf-8") if e.output else f"Error running {' '.join(cmd)}"
    except FileNotFoundError:
        return f"Tool '{tool_name}' not installed or path is incorrect."

def parse_output(tool_name, file_path, output):
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
                    "severity": r.get("issue_severity")
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

@router.get("/analyze-pr")
def analyze_pr(pr_url: str = Query(..., description="GitHub Pull Request URL")):
    temp_dir = tempfile.mkdtemp()
    results = {}
    summary = {}

    try:
        # Parse owner, repo, PR number
        parts = pr_url.rstrip("/").split("/")
        owner, repo, pull_number = parts[-4], parts[-3], parts[-1]

        # Fetch PR files from GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/files"
        headers = {"Accept": "application/vnd.github.v3+json"}
        r = requests.get(api_url, headers=headers)
        r.raise_for_status()
        pr_files = r.json()

        if not pr_files:
            return {"status": "success", "repo": repo, "results": {}, "summary": {}, "message": "No files changed in PR."}

        # Prepare ESLint config
        eslint_config_path = os.path.join(temp_dir, "eslint.config.js")
        with open(eslint_config_path, "w") as f:
            f.write("""
module.exports = { root: true, env: { node: true, es2021: true }, extends: ["eslint:recommended"], parserOptions: { ecmaVersion: 12, sourceType: "module" }, rules: {} };
""")

        # Analyze each changed file
        for file_info in pr_files:
            filename = file_info["filename"]
            ext = os.path.splitext(filename)[1]
            if ext not in ANALYZERS:
                continue

            # Fetch raw content
            raw_url = file_info["contents_url"].replace("{+path}", filename)
            content_resp = requests.get(raw_url)
            content_resp.raise_for_status()
            file_path = os.path.join(temp_dir, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content_resp.text)

            file_issues = []
            for tool_name, cmd_template in ANALYZERS[ext]["commands"]:
                output = run_tool(tool_name, cmd_template, file_path, config=eslint_config_path, cwd=temp_dir)
                file_issues.extend(parse_output(tool_name, file_path, output))

            lang_name = ANALYZERS[ext]["name"]
            results.setdefault(lang_name, []).append({
                "file": filename,
                "path": file_path,
                "issues": file_issues
            })
            summary.setdefault(lang_name, {"files_analyzed": 0, "total_issues": 0})
            summary[lang_name]["files_analyzed"] += 1
            summary[lang_name]["total_issues"] += len(file_issues)

        return {
            "status": "success",
            "repo": f"{owner}/{repo}",
            "languages": list(results.keys()),
            "summary": summary,
            "results": results
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
