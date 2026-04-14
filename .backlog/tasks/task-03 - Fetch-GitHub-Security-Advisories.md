---
id: TASK-03
title: Fetch GitHub Security Advisories
status: Done
assignee: []
created_date: '2026-04-14 09:17'
updated_date: '2026-04-14 11:00'
labels:
  - automation
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
- [x] #1 fetch_github_advisories(repo, token) exists in vulnfeed.py
- [x] #2 Function calls the correct GitHub API URL: https://api.github.com/repos/{owner}/{repo}/security-advisories
- [x] #3 Function sets Accept: application/vnd.github+json header
- [x] #4 Function sets Authorization: Bearer {token} header when token is provided
- [x] #5 Function calls response.raise_for_status() before returning
- [x] #6 Function returns the parsed JSON list of advisories
- [x] #7 Test uses unittest.mock to mock requests.get and verifies the correct URL and headers
- [x] #8 pytest tests/test_vulnfeed.py::test_fetch_github_advisories passes
- [x] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented `fetch_github_advisories(repo, token=None)` in `vulnfeed.py` to call the GitHub security-advisories endpoint with required headers, optional bearer token auth, `raise_for_status()`, and JSON return. Added/verified `test_fetch_github_advisories` using `unittest.mock.patch` on `requests.get` to assert URL, headers, status propagation, and returned advisory data.

Verification evidence: `.venv/bin/python -m pytest tests/test_vulnfeed.py::test_fetch_github_advisories -v` (1 passed), `.venv/bin/python -m pytest tests/ -v` (3 passed), `.venv/bin/ruff check .` (all checks passed), `.venv/bin/ruff format --check .` (3 files already formatted). No warnings; no follow-up required for this task scope.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
