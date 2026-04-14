---
id: TASK-07
title: GitHub Actions workflow
status: Done
assignee: []
created_date: '2026-04-14 09:18'
updated_date: '2026-04-14 11:17'
labels: []
milestone: m-0
dependencies:
  - TASK-06
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: high
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create the GitHub Actions workflow file at `.github/workflows/update-feed.yml` that runs the VulnFeed script daily and deploys the output to GitHub Pages.

The workflow has two jobs:

**Job 1: `update`** — runs on ubuntu-latest:
1. Checkout the repo
2. Set up Python 3.12
3. Install dependencies from requirements.txt
4. Run `ruff check .` and `ruff format --check .` (lint/format gate)
5. Run `python vulnfeed.py` with `GITHUB_TOKEN` from `secrets.GITHUB_TOKEN`
6. If `public/feed.xml` changed, commit and push it (use `git add public/feed.xml` then `git diff --cached --quiet` to detect changes — this handles the first run where the file doesn't exist yet)

**Job 2: `deploy`** — runs after `update`, deploys to GitHub Pages:
1. Checkout main branch
2. Pull latest (to include any feed.xml commit from the update job)
3. Use `actions/configure-pages@v5`
4. Use `actions/upload-pages-artifact@v3` with `path: public`
5. Use `actions/deploy-pages@v4`

Triggers: `schedule` (cron `0 4 * * *` for daily 4am UTC) and `workflow_dispatch` (manual).

Permissions needed: `contents: write`, `pages: write`, `id-token: write`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 .github/workflows/update-feed.yml exists
- [x] #2 Workflow triggers on schedule (cron '0 4 * * *') and workflow_dispatch
- [x] #3 Permissions include contents: write, pages: write, id-token: write
- [x] #4 Update job: checks out repo, sets up Python 3.12, installs requirements, runs ruff check and format check, runs vulnfeed.py with GITHUB_TOKEN, commits and pushes feed.xml only if changed
- [x] #5 Deploy job: depends on update job, checks out main, pulls latest, configures pages, uploads public/ as artifact, deploys to GitHub Pages
- [x] #6 Workflow YAML is valid (no syntax errors)
- [x] #7 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Verification completed with PASS_WITH_WARNINGS.

Changed file reviewed in full: `.github/workflows/update-feed.yml`.

Acceptance criteria evidence:
- Workflow file exists and includes triggers for `schedule` (`0 4 * * *`) and `workflow_dispatch`.
- Permissions include `contents: write`, `pages: write`, `id-token: write`.
- `update` job includes checkout, Python 3.12 setup, dependency install, `ruff check .`, `ruff format --check .`, `python vulnfeed.py` with `GITHUB_TOKEN`, and conditional commit/push logic for `public/feed.xml` using `git diff --cached --quiet`.
- `deploy` job depends on `update`, checks out `main`, pulls latest main, configures pages, uploads `public` artifact, and deploys pages.
- YAML syntax validated via `.venv/bin/python -c "import pathlib,yaml; yaml.safe_load(...)"`.
- Lint/format checks passed: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`.

Automated verification evidence:
- `.venv/bin/python -m pytest tests/ -v` → 7 passed.
- `.venv/bin/ruff check .` → passed.
- `.venv/bin/ruff format --check .` → passed.

Warning:
- Unrelated working-tree change present in `.gitignore` during verification (not part of TASK-07 scope). Recommend confirming whether this belongs to a separate task/commit before merge.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
