---
id: TASK-04
title: Aggregate and deduplicate advisories
status: Done
assignee: []
created_date: '2026-04-14 09:17'
updated_date: '2026-04-14 11:04'
labels: []
milestone: m-0
dependencies:
  - TASK-02
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: high
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the `aggregate_advisories()` function in `vulnfeed.py` that takes a flat list of advisory dicts (potentially from multiple repos), deduplicates them by GHSA ID, and sorts them by published date (newest first).

The function should:
- Accept a list of advisory dicts, each containing at least: `ghsa_id`, `summary`, `severity`, `published_at`, `html_url`, `description`, `repo`
- Deduplicate by `ghsa_id` — if the same GHSA ID appears multiple times, keep only the first occurrence
- Sort the result by `published_at` in descending order (newest first)
- Return the deduplicated, sorted list

Use TDD: write two tests:
1. `test_aggregate_advisories_deduplicates` — pass in 3 advisories where 2 share the same ghsa_id, assert result has 2 items
2. `test_aggregate_advisories_sorts_newest_first` — pass in an older and newer advisory, assert the newer one comes first
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 aggregate_advisories(advisories) exists in vulnfeed.py
- [x] #2 Duplicate advisories (same ghsa_id) are removed, keeping first occurrence
- [x] #3 Result is sorted by published_at descending (newest first)
- [x] #4 test_aggregate_advisories_deduplicates passes — 3 input advisories with 1 duplicate produces 2 results
- [x] #5 test_aggregate_advisories_sorts_newest_first passes — newer advisory appears before older one
- [x] #6 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented `aggregate_advisories(advisories)` in `vulnfeed.py` and added aggregate-focused tests in `tests/test_vulnfeed.py`. Verification passed: `.venv/bin/python -m pytest tests/ -v` (5 passed), `.venv/bin/ruff check .` (all checks passed), and `.venv/bin/ruff format --check .` (3 files already formatted).

Acceptance criteria and DoD are satisfied: deduplication by `ghsa_id` keeps first occurrence (confirmed via implementation and direct runtime check), output sorting is newest-first by `published_at`, and required tests pass. Minor recommendation: strengthen `test_aggregate_advisories_deduplicates` to assert the retained duplicate is explicitly the first occurrence.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
