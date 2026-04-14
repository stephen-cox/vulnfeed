---
id: TASK-03
title: Fetch GitHub Security Advisories
status: To Do
assignee: []
created_date: '2026-04-14 09:17'
labels: []
milestone: m-0
dependencies:
  - TASK-02
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: high
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the `fetch_github_advisories()` function in `vulnfeed.py` that fetches security advisories for a given GitHub repository using the GitHub REST API.

The function should:
- Accept `repo` (string like `"owner/repo"`) and an optional `token` parameter
- Call `GET https://api.github.com/repos/{owner}/{repo}/security-advisories`
- Set headers: `Accept: application/vnd.github+json` and `Authorization: Bearer {token}` (if token provided)
- Call `response.raise_for_status()` to propagate HTTP errors
- Return the parsed JSON response (a list of advisory dicts)

Key fields in each advisory from the API: `ghsa_id`, `html_url`, `summary`, `severity`, `published_at`, `description`.

Use TDD: write a test that mocks `requests.get` with a fake response containing two advisories. Assert the function makes the correct API call with correct headers, and returns the expected list.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 fetch_github_advisories(repo, token) exists in vulnfeed.py
- [ ] #2 Function calls the correct GitHub API URL: https://api.github.com/repos/{owner}/{repo}/security-advisories
- [ ] #3 Function sets Accept: application/vnd.github+json header
- [ ] #4 Function sets Authorization: Bearer {token} header when token is provided
- [ ] #5 Function calls response.raise_for_status() before returning
- [ ] #6 Function returns the parsed JSON list of advisories
- [ ] #7 Test uses unittest.mock to mock requests.get and verifies the correct URL and headers
- [ ] #8 pytest tests/test_vulnfeed.py::test_fetch_github_advisories passes
- [ ] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
