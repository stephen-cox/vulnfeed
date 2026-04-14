---
id: TASK-05
title: Generate RSS feed from advisories
status: Done
assignee: []
created_date: '2026-04-14 09:18'
updated_date: '2026-04-14 11:08'
labels:
  - feed
  - rss
milestone: m-0
dependencies:
  - TASK-02
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: high
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement RSS generation from fetched advisory records.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 generate_feed(advisories, feed_url) exists in vulnfeed.py
- [x] #2 Feed channel title is 'VulnFeed — Security Advisories'
- [x] #3 Each RSS item title follows the format '[SEVERITY] owner/repo — Advisory summary' with severity uppercased
- [x] #4 Each RSS item link points to the GitHub advisory html_url
- [x] #5 Each RSS item description contains the advisory description text
- [x] #6 Each RSS item guid is the GHSA ID
- [x] #7 Function returns valid RSS XML as bytes
- [x] #8 test_generate_feed passes — parses XML and verifies channel title, item title, link, description, guid
- [x] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented and verified RSS feed generation for advisory records.

Verification evidence (independent run): `.venv/bin/python -m pytest tests/ -v` passed (6/6), including `test_generate_feed`; `.venv/bin/ruff check .` passed; `.venv/bin/ruff format --check .` passed. Manual runtime check confirmed `generate_feed(...)` returns bytes and XML parses with expected channel title and GUID.

Acceptance criteria #1-#9 validated against source and test behavior. No critical issues found. Follow-up recommendation: consider adding an acceptance criterion for behavior when advisory fields are missing/malformed to formalize error-handling expectations.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
