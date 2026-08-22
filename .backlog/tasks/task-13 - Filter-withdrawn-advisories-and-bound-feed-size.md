---
id: TASK-13
title: Filter withdrawn advisories and bound feed size
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 06:25'
labels:
  - feed
  - bug
milestone: m-1
dependencies:
  - TASK-12
priority: medium
ordinal: 13000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The generated feed keeps everything forever and never drops retracted advisories.

**Withdrawn advisories persist.** The API returns a `withdrawn_at` field on retracted advisories. `aggregate_advisories()` (`vulnfeed.py:25`) ignores it, so an advisory GitHub has withdrawn stays in the feed indefinitely.

**The feed is unbounded.** `public/feed.xml` is currently 588 KB with 233 items reaching back to December 2019, and it will only grow — worse once TASK-11 removes the accidental 30-per-repo cap. Every subscriber re-downloads the whole thing on each poll.

**The sort key is unguarded.** `sorted(..., key=lambda advisory: advisory["published_at"])` raises `TypeError` if any advisory has a null `published_at`, which is possible for draft or unpublished advisories when authenticated with write access.

Changes:
- Drop advisories with a non-null `withdrawn_at` during aggregation.
- Add retention limits to `config.yaml` under a new `feed:` key — a `max_items` cap and an optional `max_age_days` window — with sensible defaults applied when the key is absent so existing forks keep working.
- Apply the cap after sorting, so the newest advisories are kept.
- Treat a missing or null `published_at` as the epoch when sorting rather than raising, and log it.

Document the new `feed:` config keys in `README.md`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Advisories with a non-null withdrawn_at are excluded from the feed
- [x] #2 config.yaml supports a feed.max_items setting
- [x] #3 config.yaml supports an optional feed.max_age_days setting
- [x] #4 Defaults apply when the feed key is absent, so an unmodified fork config still works
- [x] #5 The cap is applied after sorting so the newest advisories are retained
- [x] #6 A missing or null published_at sorts as oldest instead of raising TypeError, and is logged
- [x] #7 The new feed config keys are documented in README.md
- [x] #8 Tests cover withdrawn filtering, max_items truncation, max_age_days filtering, and the null published_at guard
- [x] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`aggregate_advisories()` now takes `max_items`, `max_age_days`, and an injectable `now`, and does three things it did not before.

**Withdrawn advisories are dropped.** Any advisory with a truthy `withdrawn_at` is skipped and logged. Checked with a truthy test rather than key presence, because the API sends `withdrawn_at: null` on live advisories — treating that as withdrawn would have emptied the feed.

**Retention is bounded.** New optional `feed:` section in `config.yaml` with `max_items` and `max_age_days`. `feed_limits(config)` reads them, defaulting to `max_items: 100` and no age limit when the section is absent, so an unmodified fork config keeps working. Both limits apply after sorting, so the newest advisories are what survive. `max_items: null` disables the cap. The current feed of 233 items and 588 KB will trim to 100 on the next run.

**The sort key is guarded.** Added `_published_at()`, which parses the timestamp and falls back to `datetime.min` (UTC) with a warning for null, missing, or unparseable values, instead of letting `sorted()` raise `TypeError` on a null and take the run down. Naive timestamps are coerced to UTC so comparisons against the age cutoff cannot raise on mixed awareness.

Documented the new section in `README.md` under a new Configuration heading, including that withdrawn advisories are excluded automatically, and added it to `config.yaml` with `max_age_days` present but commented out.

Verification: `.venv/bin/python -m pytest tests/ -q` → 38 passed, adding twelve tests covering withdrawn filtering, the `withdrawn_at: null` case, `max_items` applied after sorting, `max_items=None`, `max_age_days`, null and unparseable `published_at`, undated advisories interacting with the age cutoff, the three `feed_limits` cases, and an end-to-end `main()` run honouring a configured cap. Confirmed the real `config.yaml` parses to `(100, None)` across 12 repos. `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
