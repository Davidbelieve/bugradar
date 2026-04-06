import os
import sys
import requests
from datetime import datetime
from radon.complexity import cc_visit

def scan_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
       code = f.read()
    results = []
    for block in cc_visit(code):
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
            "verdict": verdict,
            "file": filepath
        })
    return results


def main():
    github_token = os.environ.get("GITHUB_TOKEN")
    pr_number = os.environ.get("PR_NUMBER")
    repo = os.environ.get("REPO")

    py_files = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in [".git", "__pycache__", "venv", "action"]]
        for fname in files:
            if fname.endswith(".py"):
                py_files.append(os.path.join(root, fname))

    all_results = []
    for filepath in py_files:
        try:
            all_results.extend(scan_file(filepath))
        except Exception as e:
            print("Skipping " + filepath + ": " + str(e))

    high_risk = [r for r in all_results if r["verdict"] == "High Risk"]
    medium_risk = [r for r in all_results if r["verdict"] == "Medium Risk"]
    low_risk = [r for r in all_results if r["verdict"] == "Low Risk"]

    report = []
    report.append("## BugOracle Defect Scan Report")
    report.append("Files scanned: " + str(len(py_files)))
    report.append("Functions analysed: " + str(len(all_results)))
    report.append("High: " + str(len(high_risk)) + " | Medium: " + str(len(medium_risk)) + " | Low: " + str(len(low_risk)))

    if high_risk:
        report.append("### High Risk Functions")
        for r in high_risk:
            report.append("- " + r["function"] + " in " + r["file"] + " complexity " + str(r["complexity"]))

    if medium_risk:
        report.append("### Medium Risk Functions")
        for r in medium_risk:
            report.append("- " + r["function"] + " in " + r["file"] + " complexity " + str(r["complexity"]))

    comment_body = "\n".join(report)
    print(comment_body)

    if github_token and pr_number and repo:
        url = "https://api.github.com/repos/" + repo + "/issues/" + pr_number + "/comments"
        headers = {"Authorization": "Bearer " + github_token, "Accept": "application/vnd.github+json"}
        resp = requests.post(url, headers=headers, json={"body": comment_body})
        print("Posted comment: " + str(resp.status_code))
    else:
        print("No token - printing only.")

    payload = {
        "repo": repo if repo else "unknown",
        "pr_number": int(pr_number) if pr_number else 0,
        "files_scanned": len(py_files),
        "high_risk": len(high_risk),
        "medium_risk": len(medium_risk),
        "low_risk": len(low_risk),
        "timestamp": datetime.utcnow().isoformat()
    }
    print("Attempting API call...")
    try:
        r2 = requests.post("https://bugradar.onrender.com/scan-report", json=payload, timeout=10)
        print("Scan report sent: " + str(r2.status_code))
    except Exception as ex:
        print("Could not send report: " + str(ex))
    
    if high_risk:
        print("FAIL: " + str(len(high_risk)) + " high risk functions found")
        sys.exit(1)

if __name__ == "__main__":
    main()