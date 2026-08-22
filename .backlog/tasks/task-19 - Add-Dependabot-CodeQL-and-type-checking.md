---
id: TASK-19
title: Add Dependabot, CodeQL and type checking
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 07:45'
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
- [x] #1 .github/dependabot.yml exists covering the pip ecosystem on a weekly schedule
- [x] #2 .github/dependabot.yml also covers the github-actions ecosystem
- [x] #3 A CodeQL workflow runs for Python on push to main and on pull requests
- [x] #4 A type checker is added to requirements.txt and configured in pyproject.toml
- [x] #5 Type checking runs in the checks job and passes with no errors
- [x] #6 Ruff lint selection is reviewed, and any added rule sets pass
- [x] #7 All workflow and config YAML parses without errors
- [x] #8 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**Dependabot.** Added `.github/dependabot.yml` covering `pip` and `github-actions`, both weekly with a five-PR limit. `requirements.txt` pins exact versions and the workflow pins action majors, and nothing was bumping either — a vulnerability in `requests` or `feedgen` would have gone unnoticed indefinitely in a project whose entire purpose is noticing vulnerabilities.

**CodeQL.** Added `.github/workflows/codeql.yml` running the Python analysis on push to `main`, on pull requests, and weekly. Scoped to `security-events: write`, `actions: read`, `contents: read` on the job with `contents: read` at the top level.

**Type checking.** Added `mypy==1.15.0` plus `types-requests` and `types-PyYAML` stubs, configured in `pyproject.toml`, and wired into the CI `checks` job between the format check and the tests.

Scoped to `vulnfeed.py` and `sources/`, deliberately excluding `tests/`. Including the tests produced 45 errors, essentially all of them `ElementTree.find()` returning `Element | None` where a test knowingly asserts on a node it just constructed. Silencing those would have meant dozens of noise assertions for no defect-finding value, which is not proportionate for a single-file project.

Against production code mypy found exactly one real problem: `get_source(name: str | None)` passed a possibly-`None` key to `dict.get`, which is typed for `str`. Fixed with an explicit `None` guard and a proper `Callable[..., SourceResult] | None` return annotation — clearer than it was, independent of the type checker. `mypy` now passes clean on 5 source files.

**Ruff ruleset extended** from `["E", "F", "I", "W"]` to add `B` (bugbear) and `UP` (pyupgrade). Both pass with no changes needed, which is a reasonable outcome given the code was written against `py312` targets throughout.

Verification: `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, and `.venv/bin/mypy` all pass; `.venv/bin/python -m pytest tests/ -q` → 103 passed. Both new YAML files parse via `yaml.safe_load`, and the `checks` job step list was inspected programmatically to confirm the type-check step is present and ordered before the tests. `README.md` and `CLAUDE.md` updated for the new command and the new files.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
