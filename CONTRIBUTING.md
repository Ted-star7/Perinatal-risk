# Contributing

`main` is protected and always demo-able. The scrum master is the only one who
merges. Everyone else works on a branch and opens a pull request.

## The loop (every task)

```bash
git checkout main && git pull          # always start from fresh main
git checkout -b feat/short-name        # one task per branch
# ... work, only inside YOUR folder ...
git add -p && git commit -m "feat: ..."
git push -u origin feat/short-name
# open a PR into main on GitHub, fill the template, request review
```

Branch prefixes: `feat/`, `fix/`, `data/`, `model/`, `docs/`, `chore/`.

## Rules that prevent merge pain

- Small PRs merged daily beat giant week-long branches.
- Stay inside your own folder. `contracts/` changes affect everyone and need
  the integrator's review — flag them in the PR title.
- Never commit DHS data, CSVs, `.env`, or model binaries (the `.gitignore` and
  pre-commit hook block them — do not bypass).
- If your branch goes stale, rebase it on `main` locally and force-push YOUR
  branch. Never resolve conflicts on `main`.

## For the integrator (merge checklist)

1. CI is green.
2. PR is small and single-purpose.
3. No data / secret / binary files slipped in.
4. If it touches `contracts/`, extra scrutiny — it changes the shared truth.
5. **Squash-merge**, then delete the branch.

## Pre-commit hook (run once per clone)

```bash
pip install pre-commit && pre-commit install
```
