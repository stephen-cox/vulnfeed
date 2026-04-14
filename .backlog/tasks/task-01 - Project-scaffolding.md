---
id: TASK-01
title: Project scaffolding
status: To Do
assignee: []
created_date: '2026-04-14 09:17'
labels: []
milestone: m-0
dependencies: []
documentation:
  - docs/superpowers/specs/2026-04-14-vulnfeed-design.md
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: high
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Set up the project structure for VulnFeed. This is a Python project that aggregates GitHub Security Advisories into an RSS feed.

Create the following files from scratch in the repo root:
- `requirements.txt` — Python dependencies: feedgen 1.0.0, requests 2.32.3, PyYAML 6.0.2, pytest 8.3.5, ruff 0.11.6
- `config.yaml` — YAML config listing GitHub repos to monitor (see spec for format: a `feeds` list with `source: github` and a `repos` list)
- `pyproject.toml` — ruff config (target Python 3.12, line-length 100, lint rules E/F/I/W) and pytest config (testpaths = tests)
- `.gitignore` — ignore `__pycache__/`, `*.pyc`, `.venv/`, `public/feed.xml`
- `public/.gitkeep` — empty file so the `public/` output directory exists in git

After creating files, set up a virtual environment and install dependencies to verify everything works.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 requirements.txt exists with feedgen, requests, PyYAML, pytest, and ruff pinned to specific versions
- [ ] #2 config.yaml exists with the correct YAML structure (feeds list with source and repos keys)
- [ ] #3 pyproject.toml exists with ruff config (target-version py312, line-length 100, lint select E/F/I/W) and pytest config (testpaths = tests)
- [ ] #4 .gitignore exists and excludes __pycache__/, *.pyc, .venv/, public/feed.xml
- [ ] #5 public/.gitkeep exists so the public/ directory is tracked by git
- [ ] #6 pip install -r requirements.txt succeeds without errors in a fresh venv
- [ ] #7 ruff check . runs without errors on an empty project
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
