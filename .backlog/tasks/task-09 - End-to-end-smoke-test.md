---
id: TASK-09
title: End-to-end smoke test
status: To Do
assignee: []
created_date: '2026-04-14 09:18'
labels: []
milestone: m-0
dependencies:
  - TASK-08
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: medium
ordinal: 9000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Run the full VulnFeed pipeline locally against the real GitHub API to verify everything works end-to-end before shipping.

Steps to perform:
1. Activate the venv and set `GITHUB_TOKEN` (use `gh auth token` if gh CLI is available)
2. Run `python vulnfeed.py` — should create `public/feed.xml` with real advisory data
3. Inspect the first 50 lines of `public/feed.xml` — verify it's valid RSS XML with `<channel>`, `<item>` elements, and titles in `[SEVERITY] repo — summary` format
4. Run `python -m pytest tests/ -v` — all tests should pass
5. Run `ruff check .` and `ruff format --check .` — no errors
6. If any adjustments were needed during smoke testing, commit them

This is a manual verification task. No new code should be needed unless bugs are found.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 python vulnfeed.py completes without errors when run with a valid GITHUB_TOKEN
- [ ] #2 public/feed.xml is created and contains valid RSS XML
- [ ] #3 Feed contains <channel> and <item> elements
- [ ] #4 Item titles follow the [SEVERITY] repo — summary format
- [ ] #5 python -m pytest tests/ -v shows all tests passing
- [ ] #6 ruff check . and ruff format --check . show no errors
- [ ] #7 Any fixes found during smoke testing are committed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
