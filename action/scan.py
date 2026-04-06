import os
import sys
import json
import requests
from radon.complexity import cc_visit
from radon.raw import analyze

def scan_python_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    blocks = cc_visit(code)
    results = []
    for block in blocks:
        if block.complexity <= 5:
            verdict = "Low Risk"
        elif block.complexity <= 10:
            verdict = "Medium Risk"
        else:
            verdict = "High Risk"
        results.append({
            "function": block.name,
            "complexity": block.complexity,
            "line": block.lineno,
            "verdict": verdict
        })
    return results

def main():
    github_token = os.environ.get("GITHUB_TOKEN")
    pr_number = os.environ.get("PR_NUMBER")
    repo = os.environ.get("REPO")

    py_files = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "venv"]]
        for f in files:
            if f.endswith(".py") and "action" not in root:
                py_files.append(os.path.join(root, f))

    all_results = []
    for filepath in py_files:
        try:
            results = scan_python_file(filepath)
            for r in results:
                r["file"] = filepath
            all_results.extend(results)
        except Exception as e:
            print(f"Skipping {filepath}: {e}")

    high_risk = [r for r in all_results if r["verdict"] == "High Risk"]
    medium_risk = [r for r in all_results if r["verdict"] == "Medium Risk"]
    low_risk = [r for r in all_results if r["verdict"] == "Low Risk"]

    lines = ["## 🔮 BugOracle Defect Scan Report\n"]
    lines.append(f"**Files scanned:** {len(py_files)}  ")
    lines.append(f"**Functions analysed:** {len(all_results)}  ")
    lines.append(f"🔴 High Risk: {len(high_risk)} | 🟡 Medium Risk: {len(medium_risk)} | 🟢 Low Risk: {len(low_risk)}\n")

    if high_risk:
        lines.append("### 🔴 High Risk Functions")
        for r in high_risk:
            lines.append(f"- `{r['function']}` in `{r['file']}` — complexity **{r['complexity']}** (line {r['line']})")

    if medium_risk:
        lines.append("\n### 🟡 Medium Risk Functions")
        for r in medium_risk:
            lines.append(f"- `{r['function']}` in `{r['file']}` — complexity **{r['complexity']}** (line {r['line']})")

    comment_body = "\n".join(lines)
    print(comment_body)

    if github_token and pr_number and repo:
        url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }
        resp = requests.post(url, headers=headers, json={"body": comment_body})
        print(f"Posted comment: {resp.status_code}")
    else:
        print("No GitHub token/PR info — printing report only.")

        if high_risk:    
            print(f"\n❌ {len(high_risk)} high risk function(s) found — failing check")    
            sys.exit(1)    

if __name__ == "__main__":
    main()    