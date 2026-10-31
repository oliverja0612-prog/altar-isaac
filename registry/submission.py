"""Turns a "Submit a mod" issue into a registry entry (run by .github/workflows/mod-submission.yml).

    python registry/submission.py <issue-body.md> <issue number> <submitter login>

Reads the issue form, runs the safety check on the mod's repo, and writes:
  report.md                    the comment posted on the issue
  pr.md                        the body of the review pull request
  registry/mods/<id>.json      the entry itself, only when the check passes
and the step outputs result, id, name, version (to $GITHUB_OUTPUT).
"""
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import safety_check  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
MODS = os.path.join(HERE, "mods")


def form_fields(body):
    """GitHub issue forms render as '### Label' headings followed by the answer."""
    fields, current = {}, None
    for line in body.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            fields[current] = []
        elif current is not None:
            fields[current].append(line)
    clean = {}
    for k, v in fields.items():
        text = "\n".join(v).strip()
        clean[k] = "" if text == "_No response_" else text
    return clean


def field(fields, *names):
    for n in names:
        for k, v in fields.items():
            if k.startswith(n):
                return v
    return ""


def repo_from(text):
    text = text.strip().rstrip("/")
    m = re.search(r"github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?(?:/.*)?$", text)
    if m:
        return m.group(1)
    return text if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", text) else ""


def load_admins():
    with open(os.path.join(HERE, "admins.json"), encoding="utf-8") as f:
        return json.load(f)


def approvals_needed():
    a = load_admins()
    return max(1, min(a.get("approvals_required", 2), len(a["admins"])))


def slug(name):
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s[:48] or "mod"


def output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    lines = [f"{k}={str(v).replace(chr(10), ' ')}" for k, v in kv.items()]
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    body_path, issue, submitter = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    fields = form_fields(open(body_path, encoding="utf-8").read())
    repo = repo_from(field(fields, "github repo", "repo"))
    ref = field(fields, "release", "version", "tag") or "main"
    path = field(fields, "folder", "path").strip().strip("/")
    form_name = field(fields, "mod name", "name")
    form_desc = field(fields, "description", "what does")

    if not repo:
        report = {"result": "fail", "findings": [{"level": "fail",
                  "message": "the GitHub repo field must be a link like https://github.com/you/your-mod"}],
                  "stats": {"files": 0, "bytes": 0}}
    else:
        report = safety_check.check_repo(repo, ref.split()[0], path)

    meta = report.get("metadata") or {}
    name = (meta.get("name") or form_name or (repo.split("/")[-1] if repo else "mod")).strip()
    mod_id = slug(name)
    version = (meta.get("version") or ref).strip()

    # a name belongs to the first repo that registered it; the same repo can send updates
    existing = os.path.join(MODS, f"{mod_id}.json")
    if report["result"] == "pass" and os.path.isfile(existing):
        old = json.load(open(existing, encoding="utf-8"))
        if old.get("repo", "").lower() != repo.lower():
            report["result"] = "fail"
            report["findings"].append({"level": "fail", "message": f"the name '{name}' is already taken by {old['repo']}"})

    md = safety_check.markdown(report)
    if report["result"] == "pass":
        entry = {
            "id": mod_id,
            "name": name,
            "version": version,
            "author": submitter,
            "description": form_desc or meta.get("description", ""),
            "repo": repo,
            "ref": ref,
            "commit": report["commit"],
            "path": path,
            "folder": (meta.get("directory") or mod_id).strip(),
            "download": report["download"],
            "zip_root": report["zip_root"],
            "sha256": report["sha256"],
            "size": report["size"],
            "files": report["stats"]["files"],
            "warnings": sum(1 for f in report["findings"] if f["level"] == "warn"),
            "issue": issue,
            "submitted": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        os.makedirs(MODS, exist_ok=True)
        with open(existing, "w", encoding="utf-8") as f:
            json.dump(entry, f, indent=2)
            f.write("\n")
        need = approvals_needed()
        md += (f"\n\nA review pull request has been opened. {need} admin approval{'s' if need > 1 else ''} "
               f"and **{name} {version}** goes live on the site and in the Altar app.")
        pr = (f"Adds **{name} {version}** by @{submitter} from [{repo}](https://github.com/{repo}/tree/{report['commit']}"
              f"{'/' + path if path else ''}).\n\nCloses #{issue}\n\n{safety_check.markdown(report)}\n\n"
              "Admins: read the warnings (if any), look at the code, then approve. It merges and goes live "
              "automatically once the required approvals are in.")
        with open("pr.md", "w", encoding="utf-8") as f:
            f.write(pr)
    else:
        md += "\n\nFix the problems above, then edit this issue (or push a new release and edit the version) to run the check again."
    with open("report.md", "w", encoding="utf-8") as f:
        f.write(md)
    output(result=report["result"], id=mod_id, name=name, version=version)


if __name__ == "__main__":
    main()
