---
id: TASK-20
title: Notify on new critical advisories
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
labels:
  - feature
milestone: m-1
dependencies:
  - TASK-13
priority: low
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
VulnFeed publishes a feed and nothing else. Noticing a critical advisory requires the subscriber to open their reader. For the severities that matter most, a push is more appropriate than a pull — 23 of the 233 advisories currently in the feed are CRITICAL.

Add an opt-in notification path for newly seen advisories at or above a configured severity:
- New optional `notifications:` section in `config.yaml` — a minimum severity threshold and one or more destinations. Absent means no notifications, so forks are unaffected.
- Support a generic webhook destination (works for Slack and Discord incoming webhooks), with the URL supplied via an environment variable rather than committed to config. Document the Actions secret setup in `README.md`.
- Optionally support opening a GitHub issue per new critical advisory, which needs no external service and gives a natural triage workflow.

The hard part is **"newly seen"**. The design spec is explicit that there is no database and no state file, and each run regenerates the full feed idempotently. Naively notifying on everything above the threshold would fire on every run for every historic critical advisory.

Resolve this before implementing. The most likely approach is to diff against the previously committed `public/feed.xml` — it is already in git, already the record of what was last published, and requires no new state. Note that TASK-18 may stop committing the feed, so coordinate with whatever it decides. Whichever mechanism is chosen, the first run after enabling notifications must not spam every historic advisory, and a failed or skipped run must not cause an advisory to be silently missed on the next one.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 config.yaml supports an optional notifications section with a minimum severity threshold
- [ ] #2 Notifications are off by default so existing fork configs are unaffected
- [ ] #3 A generic webhook destination is supported, with the URL read from an environment variable
- [ ] #4 The Actions secret setup for the webhook is documented in README.md
- [ ] #5 The mechanism for determining a newly seen advisory is chosen and documented, and does not require a new state file
- [ ] #6 The first run after enabling notifications does not notify for historic advisories
- [ ] #7 A skipped or failed run does not cause an advisory to be missed on the following run
- [ ] #8 Only advisories at or above the configured severity trigger a notification
- [ ] #9 A notification delivery failure is logged and does not abort feed generation
- [ ] #10 Tests cover threshold filtering, new-vs-seen detection, the first-run case, and a webhook delivery failure
- [ ] #11 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
