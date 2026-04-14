---
id: TASK-07
title: GitHub Actions workflow
status: To Do
assignee: []
created_date: '2026-04-14 09:18'
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
- [ ] #1 .github/workflows/update-feed.yml exists
- [ ] #2 Workflow triggers on schedule (cron '0 4 * * *') and workflow_dispatch
- [ ] #3 Permissions include contents: write, pages: write, id-token: write
- [ ] #4 Update job: checks out repo, sets up Python 3.12, installs requirements, runs ruff check and format check, runs vulnfeed.py with GITHUB_TOKEN, commits and pushes feed.xml only if changed
- [ ] #5 Deploy job: depends on update job, checks out main, pulls latest, configures pages, uploads public/ as artifact, deploys to GitHub Pages
- [ ] #6 Workflow YAML is valid (no syntax errors)
- [ ] #7 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
