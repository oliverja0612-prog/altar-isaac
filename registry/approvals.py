"""Says whether a submission PR has enough admin approvals to go live.

    python registry/approvals.py <login> [<login> ...]

Pass the logins whose latest review on the PR is APPROVED. Exits 0 when enough of them
are admins in registry/admins.json, 1 otherwise. Used by .github/workflows/mod-approve.yml.
"""
import sys

from submission import approvals_needed, load_admins


def main():
    admins = {a["github"].lower() for a in load_admins()["admins"]}
    approved = {login.lower() for login in sys.argv[1:]} & admins
    need = approvals_needed()
    print(f"{len(approved)}/{need} admin approvals: {', '.join(sorted(approved)) or 'none'}")
    sys.exit(0 if len(approved) >= need else 1)


if __name__ == "__main__":
    main()
