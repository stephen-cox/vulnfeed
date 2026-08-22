---
id: TASK-10
title: Run tests in CI and gate pull requests
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
labels:
  - ci
  - testing
milestone: m-1
dependencies: []
priority: high
ordinal: 10000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`.github/workflows/update-feed.yml` runs `ruff check .` and `ruff format --check .` in both the `build-index` and `update-feed` jobs, but never runs `pytest`. The test suite (`tests/test_vulnfeed.py`, 7 tests) has never executed in CI.

The workflow also only triggers on `schedule`, `workflow_dispatch`, and `push` to `main`, so pull requests get no checks at all — a broken change is only caught after it lands.

Restructure the workflow so checks are shared rather than duplicated:

- Add a `checks` job that installs dependencies, runs `ruff check .`, `ruff format --check .`, and `python -m pytest tests/ -v`.
- Make `build-index` and `update-feed` depend on `checks` and drop their inline lint steps.
- Add a `pull_request` trigger. On a pull request, only the `checks` job should run — `build-index`, `update-feed`, and `deploy` must stay skipped so a PR never commits to `main` or deploys to Pages.

Keep the existing `if:` guards on `build-index` / `update-feed` working. Note that `deploy` uses `always() && !cancelled()` with an `||` over both job results, so verify it still skips cleanly on a pull request run.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A `checks` job runs `ruff check .`, `ruff format --check .`, and `python -m pytest tests/ -v`
- [ ] #2 `build-index` and `update-feed` declare `needs: [checks]` and no longer duplicate the lint steps
- [ ] #3 The workflow triggers on `pull_request`
- [ ] #4 On a pull request, only `checks` runs — `build-index`, `update-feed`, and `deploy` are all skipped
- [ ] #5 Scheduled and manual runs still generate the feed and deploy as before
- [ ] #6 Workflow YAML parses without errors
- [ ] #7 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
