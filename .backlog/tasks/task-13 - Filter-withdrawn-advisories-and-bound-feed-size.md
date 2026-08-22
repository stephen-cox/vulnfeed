---
id: TASK-13
title: Filter withdrawn advisories and bound feed size
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
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
- [ ] #1 Advisories with a non-null withdrawn_at are excluded from the feed
- [ ] #2 config.yaml supports a feed.max_items setting
- [ ] #3 config.yaml supports an optional feed.max_age_days setting
- [ ] #4 Defaults apply when the feed key is absent, so an unmodified fork config still works
- [ ] #5 The cap is applied after sorting so the newest advisories are retained
- [ ] #6 A missing or null published_at sorts as oldest instead of raising TypeError, and is logged
- [ ] #7 The new feed config keys are documented in README.md
- [ ] #8 Tests cover withdrawn filtering, max_items truncation, max_age_days filtering, and the null published_at guard
- [ ] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
