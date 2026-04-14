---
id: TASK-09
title: End-to-end smoke test
status: Done
assignee: []
created_date: '2026-04-14 09:18'
updated_date: '2026-04-14 11:26'
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
- [x] #1 python vulnfeed.py completes without errors when run with a valid GITHUB_TOKEN
- [x] #2 public/feed.xml is created and contains valid RSS XML
- [x] #3 Feed contains <channel> and <item> elements
- [x] #4 Item titles follow the [SEVERITY] repo — summary format
- [x] #5 python -m pytest tests/ -v shows all tests passing
- [x] #6 ruff check . and ruff format --check . show no errors
- [x] #7 Any fixes found during smoke testing are committed
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Executed end-to-end smoke validation using authenticated GitHub API access: `GITHUB_TOKEN="$(gh auth token)" .venv/bin/python vulnfeed.py` completed successfully and regenerated `public/feed.xml`. Verified feed integrity by XML parsing and structure checks (`<channel>` present, 13 `<item>` nodes) and confirmed all item titles match `[SEVERITY] repo — summary`.

Automated checks all passed: `.venv/bin/python -m pytest tests/ -v` (7 passed), `.venv/bin/ruff check .` (clean), `.venv/bin/ruff format --check .` (already formatted). No defects were found during smoke testing, so no source-code fixes were required.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
