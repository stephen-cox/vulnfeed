---
id: TASK-12
title: Isolate per-repo fetch failures
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 06:15'
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
- [x] #1 A failure fetching one repo does not prevent the other repos from being fetched
- [x] #2 Each failure is logged with the repo name and the underlying error
- [x] #3 The feed is still generated from the repos that succeeded
- [x] #4 The script exits non-zero when every repo fails
- [x] #5 The script exits zero when at least one repo succeeds
- [x] #6 A summary of succeeded/failed repo counts and total advisories is logged at the end of the run
- [x] #7 Logging uses the logging module, configured in main()
- [x] #8 Test covers a mixed run where one repo raises and another succeeds
- [x] #9 Test covers the all-repos-failed case producing a non-zero exit
- [x] #10 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Extracted the fetch loop out of `main()` into `collect_advisories(config, token)`, which returns `(advisories, succeeded, failed)`. Each repo is fetched inside a `try`, so a renamed, deleted, private, or transiently unavailable repo is recorded and skipped instead of aborting the run. `requests.RequestException` is logged at ERROR with the repo name and the underlying error; anything unexpected is caught separately and logged with a traceback via `log.exception`, so a malformed payload cannot freeze the feed either.

Introduced `logging` throughout (module logger `vulnfeed`, `basicConfig` in `main()`), replacing the script's previous silence. A run now logs per-repo counts, per-repo failures, and a closing summary: `2 advisories from 4 repos (2 succeeded, 2 failed)` followed by `Repos that failed: owner/gone, owner/broken`.

`main()` now returns an exit code and the `__main__` block passes it to `sys.exit`. It returns 1 only when every configured repo failed — a systemic signal (bad token, API outage, no network) — and in that case returns *before* writing, so the previously published `feed.xml` is left intact rather than replaced with an empty one.

**Deviation from the task description.** The description also called for exiting non-zero when no advisories were retrieved at all. Implemented as a WARNING with exit 0 instead: a config watching quiet repos is legitimate, and `taigaio/taiga-events` in the current `config.yaml` already returns zero advisories, so failing on that would break the real configuration. Exit 1 is reserved for all-repos-failed, which is what AC #4 and #5 specify.

Verification: `.venv/bin/python -m pytest tests/ -q` → 26 passed, adding seven tests covering mixed success/failure, unexpected non-network errors, unknown sources being skipped, the all-failed non-zero exit leaving an existing feed untouched, the one-succeeded zero exit, the quiet-repos case, and the summary log text. A manual run with two of four repos failing exits 0 and writes both surviving advisories. `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
