# Altar mod library

How a mod gets from someone's GitHub repo onto the site, the Altar app and the Discord bot.

```
"Submit a mod" issue ──► mod-submission.yml ──► safety_check.py ──► report comment on the issue
                                                      │ pass
                                                      ▼
                         review PR (submission/<issue>) + commit status "safety"
                                                      │ admins approve
                                                      ▼
                         mod-approve.yml: enough admin approvals? ──► merge ──► pages.yml
                                                      ▼
                         site/registry/index.json ──► site · Altar app Browse · Discord bot
```

| File | What it does |
|---|---|
| `safety_check.py` | Downloads the repo at one exact commit and scans it. Run by hand: `python registry/safety_check.py owner/repo v1.0.0 --path mods/my_mod` |
| `submission.py` | Reads the issue form, runs the check, writes `mods/<id>.json` |
| `verify_entries.py` | Re-checks changed entries in pull requests people open by hand |
| `approvals.py` | Counts admin approvals on a submission PR |
| `build_index.py` | Builds `site/registry/index.json` when the site deploys |
| `admins.json` | The admin team, their roles and how many approvals a mod needs |
| `mods/*.json` | One file per published mod, pinned to a commit + sha256 |

## Roles

- **owner**: approves mods, runs the repo (branch rules, releases, admins).
- **reviewer**: approves or rejects mod submissions.

To **approve**, open the review PR → *Files changed* → *Review changes* → *Approve*.
To **reject**, close the PR with a comment; the submitter is told on their issue.
To **take a mod down**, delete its `mods/<id>.json` and push.

## Adding the second admin

1. Invite them: repo **Settings → Collaborators → Add people** (Write access).
2. Add them to `admins.json`:
   ```json
   { "github": "their-name", "role": "reviewer" }
   ```
3. Add `@their-name` to the `/registry/` line in `.github/CODEOWNERS`.
4. Raise the branch rule to two approvals:
   ```
   gh api -X PATCH repos/oliverja0612-prog/altar-isaac/branches/main/protection/required_pull_request_reviews -F required_approving_review_count=2
   ```

`approvals_required` in `admins.json` is already 2; while there is only one admin it counts as 1.
