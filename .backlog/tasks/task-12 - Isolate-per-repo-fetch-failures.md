---
id: TASK-12
title: Isolate per-repo fetch failures
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
labels:
  - reliability
  - bug
milestone: m-1
dependencies:
  - TASK-11
priority: high
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`main()` fetches each repo inside a bare loop (`vulnfeed.py:166-171`) and `fetch_github_advisories` calls `raise_for_status()`. A single failing repo — renamed, deleted, made private, or returning a transient 403 that outlives the retries from TASK-11 — propagates out of the loop and aborts the entire run. The feed is not regenerated at all, so one bad entry in `config.yaml` silently freezes the published output.

Make the loop fault-tolerant:
- Catch per-repo fetch failures, record them, and continue with the remaining repos.
- Log each failure clearly (repo name, status code or exception) to stderr so it is visible in the Actions log.
- Still generate the feed from the repos that succeeded.
- Exit non-zero only if *every* configured repo failed, or if no advisories were retrieved at all — that indicates a systemic problem (bad token, API outage) rather than one stale config entry.
- Print a summary line at the end: repos succeeded, repos failed, total advisories.

There is currently no logging anywhere in the script; use the `logging` module rather than bare `print`, configured once in `main()`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A failure fetching one repo does not prevent the other repos from being fetched
- [ ] #2 Each failure is logged with the repo name and the underlying error
- [ ] #3 The feed is still generated from the repos that succeeded
- [ ] #4 The script exits non-zero when every repo fails
- [ ] #5 The script exits zero when at least one repo succeeds
- [ ] #6 A summary of succeeded/failed repo counts and total advisories is logged at the end of the run
- [ ] #7 Logging uses the logging module, configured in main()
- [ ] #8 Test covers a mixed run where one repo raises and another succeeds
- [ ] #9 Test covers the all-repos-failed case producing a non-zero exit
- [ ] #10 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
