"""Re-checks registry entries in a pull request: the pinned download still has the same
sha256 and still passes the safety check. Run by .github/workflows/registry-check.yml.

    python registry/verify_entries.py registry/mods/a.json [registry/mods/b.json ...]
"""
import hashlib
import json
import sys

import safety_check

REQUIRED = ("id", "name", "version", "repo", "commit", "download", "zip_root", "sha256", "folder")


def verify(path):
    with open(path, encoding="utf-8") as f:
        e = json.load(f)
    missing = [k for k in REQUIRED if not e.get(k)]
    if missing:
        return f"missing fields: {', '.join(missing)}"
    if e["download"] != f"https://codeload.github.com/{e['repo']}/zip/{e['commit']}":
        return "download must be the codeload zip of the pinned commit"
    if any(c in e["folder"] for c in "/\\:") or e["folder"] in (".", ".."):
        return f"bad folder name '{e['folder']}'"
    data = safety_check.http_get(e["download"])
    if hashlib.sha256(data).hexdigest() != e["sha256"]:
        return "sha256 doesn't match the download"
    report = safety_check.check_zip(data, e.get("path", ""))
    if report["result"] != "pass":
        return "safety check failed:\n" + safety_check.markdown(report)
    if report["zip_root"] != e["zip_root"]:
        return "zip_root doesn't match the folder in the download"
    return None


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    bad = 0
    for path in sys.argv[1:]:
        problem = verify(path)
        print(f"{'FAIL' if problem else 'ok  '} {path}" + (f": {problem}" if problem else ""))
        bad += bool(problem)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
