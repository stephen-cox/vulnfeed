---
id: TASK-11
title: Paginate advisory fetching and add timeouts and retries
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
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
- [ ] #1 fetch_github_advisories requests per_page=100 and follows Link rel="next" until there are no more pages
- [ ] #2 All pages are concatenated into a single returned list
- [ ] #3 Every request passes an explicit timeout
- [ ] #4 Transient failures (429, 5xx, connection errors) are retried with bounded exponential backoff
- [ ] #5 Retry-After is honoured when the response provides it
- [ ] #6 A maximum page count prevents an unbounded pagination loop
- [ ] #7 Test covers a multi-page response assembling into one list
- [ ] #8 Test asserts per_page and timeout are sent on the request
- [ ] #9 Test covers a retried transient error that eventually succeeds
- [ ] #10 A real run produces more than 30 advisories for at least one previously capped repo
- [ ] #11 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
