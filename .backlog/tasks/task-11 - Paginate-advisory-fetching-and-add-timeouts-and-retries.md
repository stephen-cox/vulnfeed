---
id: TASK-11
title: Paginate advisory fetching and add timeouts and retries
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 06:05'
labels:
  - reliability
  - bug
milestone: m-1
dependencies: []
priority: high
ordinal: 11000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`fetch_github_advisories()` (`vulnfeed.py:14`) makes a single unpaginated request with no timeout and no retry handling. Three defects follow from that:

**1. The feed is silently truncated.** GitHub's `/repos/{owner}/{repo}/security-advisories` endpoint defaults to `per_page=30`. Six of the twelve configured repos currently return exactly 30 advisories — `zammad/zammad`, `open-webui/open-webui`, `mautic/mautic`, `espocrm/espocrm`, `argoproj/argo-cd`, and `WordPress/wordpress-develop`. Everything past the newest 30 per repo is being dropped with no warning.

**2. A hung request stalls the job.** `requests.get(url, headers=headers)` has no `timeout`, so a stalled connection blocks until the Actions six-hour job limit.

**3. Rate limits and transient errors are unhandled.** A 429, a secondary rate-limit 403, or a transient 5xx fails immediately.

Changes:
- Request `per_page=100` and follow the `Link: rel="next"` header until exhausted, accumulating all pages.
- Pass an explicit `timeout` (connect and read) to every request.
- Retry transient failures (429, 5xx, connection errors) with bounded exponential backoff, honouring `Retry-After` when present. Cap the attempts so a persistently failing repo terminates rather than looping.
- Guard against a runaway pagination loop (a sane maximum page count).

Tests should mock `requests.get` and cover: a two-page response assembling into one list, `per_page=100` being sent, a timeout being passed, and a retried 5xx eventually succeeding.

Out of scope: ETag / `If-None-Match` conditional requests to conserve rate limit. Worth doing later, but it needs cross-run state, which the design spec deliberately avoids.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 fetch_github_advisories requests per_page=100 and follows Link rel="next" until there are no more pages
- [x] #2 All pages are concatenated into a single returned list
- [x] #3 Every request passes an explicit timeout
- [x] #4 Transient failures (429, 5xx, connection errors) are retried with bounded exponential backoff
- [x] #5 Retry-After is honoured when the response provides it
- [x] #6 A maximum page count prevents an unbounded pagination loop
- [x] #7 Test covers a multi-page response assembling into one list
- [x] #8 Test asserts per_page and timeout are sent on the request
- [x] #9 Test covers a retried transient error that eventually succeeds
- [ ] #10 A real run produces more than 30 advisories for at least one previously capped repo — BLOCKED, see Final Summary; substituted a real-HTTP integration test. Confirm on the first scheduled run.
- [x] #11 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Rewrote `fetch_github_advisories` and added two helpers in `vulnfeed.py`.

**Pagination.** The first request now sends `per_page=100` and each subsequent page follows the `next` URL from the `Link` header verbatim (it already carries `per_page` and `page`). Pages accumulate into one list. Termination is on an absent `next` link or an empty page body, with a `MAX_PAGES = 50` ceiling so a malformed Link header logs a warning and stops rather than cycling forever.

**Timeouts.** `REQUEST_TIMEOUT = (5, 30)` (connect, read) is passed on every request.

**Retries.** `_get_with_retries` retries 429 and 5xx responses plus `requests.RequestException` with exponential backoff (1s, 2s, 4s) over `MAX_ATTEMPTS = 4`, honouring `Retry-After` when present and falling back to the exponential delay when the header is missing or unparseable. Client errors other than 429 — notably the 404 of a renamed or deleted repo — fail immediately rather than burning 7 seconds of backoff first.

**Testing.** Twelve tests now cover the fetcher, including multi-page assembly, the `per_page`/`timeout` arguments, empty-page termination, the MAX_PAGES ceiling, retried 5xx and connection errors, `Retry-After` handling, exhaustion after four attempts, and no-retry on 404.

Added `tests/test_integration.py`, which serves the endpoint from a local `ThreadingHTTPServer` with genuine `Link` headers. The unit tests mock `requests.get`, which stubs out the one thing pagination depends on — requests' own parsing of `Link` into `response.links` — so this exercises it for real: 250 advisories retrieved across 3 pages at `per_page=100`. A companion test documents the original bug by showing a single default-paged request returning only 30 of the 250.

**AC #10 not verified.** The intent was to prove the fix against the live API. This session's GitHub access is scoped to `stephen-cox/vulnfeed`, and direct `api.github.com` calls return 403 ("GitHub access to this repository is not enabled for this session") for third-party repos and for the in-scope repo alike; the GitHub MCP server exposes no security-advisories endpoint. The local-HTTP integration test above is the substitute and covers the same mechanism, but it cannot confirm GitHub's live response shape. Confirm on the first scheduled run — the six repos previously pinned at exactly 30 (`zammad/zammad`, `open-webui/open-webui`, `mautic/mautic`, `espocrm/espocrm`, `argoproj/argo-cd`, `WordPress/wordpress-develop`) should exceed it.

Verification: `.venv/bin/python -m pytest tests/ -q` → 19 passed. `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done — #10 blocked by session GitHub scope
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
