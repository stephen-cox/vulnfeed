---
id: TASK-19
title: Add Dependabot, CodeQL and type checking
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
labels:
  - ci
  - security
milestone: m-1
dependencies:
  - TASK-10
priority: low
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A project whose purpose is tracking security advisories should be watching its own dependencies. It currently is not.

`requirements.txt` pins exact versions (`requests==2.32.3`, `feedgen==1.0.0`, `PyYAML==6.0.2`, `pytest==8.3.5`, `ruff==0.11.6`) with nothing to bump them, so a vulnerability in one of these would go unnoticed indefinitely.

Add:
- `.github/dependabot.yml` covering both the `pip` ecosystem and `github-actions` (the workflow pins `actions/checkout@v4`, `setup-python@v5`, `configure-pages@v5`, `upload-pages-artifact@v3`, `deploy-pages@v4`), on a weekly schedule.
- A CodeQL workflow for Python, on push to `main` and on pull requests.
- Type checking in the `checks` job from TASK-10. The codebase already carries full type annotations, so a checker should have little to complain about — pick mypy or ty, add it to `requirements.txt`, configure it in `pyproject.toml`, and fix whatever it surfaces.

Consider also extending the ruff lint selection in `pyproject.toml`, which is currently just `["E", "F", "I", "W"]` — `B` (bugbear) and `UP` (pyupgrade) are cheap additions that catch real problems.

Keep this proportionate: the goal is automated awareness of dependency and code issues, not a heavyweight quality gate on a single-file project.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 .github/dependabot.yml exists covering the pip ecosystem on a weekly schedule
- [ ] #2 .github/dependabot.yml also covers the github-actions ecosystem
- [ ] #3 A CodeQL workflow runs for Python on push to main and on pull requests
- [ ] #4 A type checker is added to requirements.txt and configured in pyproject.toml
- [ ] #5 Type checking runs in the checks job and passes with no errors
- [ ] #6 Ruff lint selection is reviewed, and any added rule sets pass
- [ ] #7 All workflow and config YAML parses without errors
- [ ] #8 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
