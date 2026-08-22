---
id: TASK-10
title: Run tests in CI and gate pull requests
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 05:52'
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
- [x] #1 A `checks` job runs `ruff check .`, `ruff format --check .`, and `python -m pytest tests/ -v`
- [x] #2 `build-index` and `update-feed` declare `needs: [checks]` and no longer duplicate the lint steps
- [x] #3 The workflow triggers on `pull_request`
- [x] #4 On a pull request, only `checks` runs — `build-index`, `update-feed`, and `deploy` are all skipped
- [x] #5 Scheduled and manual runs still generate the feed and deploy as before
- [x] #6 Workflow YAML parses without errors
- [x] #7 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Restructured `.github/workflows/update-feed.yml` around a shared `checks` job running `ruff check .`, `ruff format --check .`, and `python -m pytest tests/ -v`. `build-index` and `update-feed` now declare `needs: [checks]` and no longer duplicate the lint steps, so a failing test blocks both the feed commit and the Pages deploy.

Added a `pull_request` trigger. Gating verified for each event: on `pull_request` only `checks` runs — `build-index` (`event_name == 'push'`) and `update-feed` (`schedule || workflow_dispatch`) are both false, and `deploy` skips because its condition requires one of them to have result `'success'` while both report `'skipped'`. Push, schedule, and dispatch runs are unchanged. When `checks` fails, the dependent jobs skip and `deploy` skips with them.

Tightened permissions alongside the new trigger: top-level dropped to `contents: read`, with `contents: write` granted only to the two jobs that push and `pages: write` / `id-token: write` only to `deploy`. Without this, a same-repo pull request branch would have run with a repo-write token.

**Pre-existing bug found and fixed.** Enabling the suite exposed a failing test that had never run in CI: `generate_feed` emitted en dashes (`VulnFeed – Security Advisories`, `[HIGH] repo – summary`) while both `tests/test_vulnfeed.py` and the design spec (`doc-01`) specify em dashes. Corrected `vulnfeed.py:38` and `vulnfeed.py:48` to match the spec. Item GUIDs are GHSA IDs and are unaffected, so subscribers will not see re-notified items — only retitled ones.

Verification: `.venv/bin/python -m pytest tests/ -q` → 8 passed (was 1 failed, 7 passed at baseline). `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass. Workflow YAML parses via `yaml.safe_load`. `python vulnfeed.py --index-only` produces a byte-identical `public/index.html`.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
