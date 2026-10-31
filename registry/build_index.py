"""Builds the site's mod list: site/registry/index.json from registry/mods/*.json, plus the
admin team from registry/admins.json. Run by .github/workflows/pages.yml before deploying.

The Altar app and the Discord bot read the same file:
https://oliverja0612-prog.github.io/altar-isaac/registry/index.json
"""
import datetime
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "site", "registry")


def main():
    mods = []
    for path in sorted(glob.glob(os.path.join(HERE, "mods", "*.json"))):
        with open(path, encoding="utf-8") as f:
            mods.append(json.load(f))
    mods.sort(key=lambda m: m["name"].lower())
    admins = json.load(open(os.path.join(HERE, "admins.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    index = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": "oliverja0612-prog/altar-isaac",
        "admins": admins["admins"],
        "roles": admins["roles"],
        "approvals_required": max(1, min(admins.get("approvals_required", 2), len(admins["admins"]))),
        "mods": mods,
    }
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)
    print(f"index.json: {len(mods)} mods")


if __name__ == "__main__":
    main()
