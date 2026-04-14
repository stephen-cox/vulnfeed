---
id: TASK-08
title: README with setup and usage instructions
status: Done
assignee: []
created_date: '2026-04-14 09:18'
updated_date: '2026-04-14 11:21'
labels: []
milestone: m-0
dependencies:
  - TASK-07
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: medium
ordinal: 8000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Create `README.md` at the project root with documentation for users and anyone forking the repo.

The README should include these sections:

1. **Title and tagline** — "VulnFeed" with a one-line description of what it does
2. **How it works** — Brief explanation: Python script reads config.yaml, fetches GitHub Security Advisories, generates RSS feed
3. **Subscribe** — Shows the feed URL pattern: `https://<username>.github.io/vulnfeed/feed.xml`
4. **Fork and customize** — Step-by-step instructions:
   - Fork the repo
   - Edit `config.yaml` to list repos to monitor
   - Enable GitHub Pages (Settings > Pages > Source: GitHub Actions)
   - Workflow runs daily at 4am UTC, or trigger manually from Actions tab
5. **Local development** — Commands to set up venv, install deps, run the script. Note about setting `GITHUB_TOKEN` for authenticated API access
6. **Running tests** — `python -m pytest tests/ -v`
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 README.md exists at the project root
- [x] #2 Contains a clear project title and one-line description
- [x] #3 Explains how the tool works (config -> fetch -> generate RSS)
- [x] #4 Shows the GitHub Pages feed URL pattern
- [x] #5 Includes fork-and-customize instructions with GitHub Pages setup (Source: GitHub Actions)
- [x] #6 Includes local development setup commands (venv, pip install, run script)
- [x] #7 Documents how to set GITHUB_TOKEN for authenticated API access
- [x] #8 Includes test running instructions
- [x] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a new root `README.md` documenting project purpose, workflow (config → fetch advisories → generate RSS), subscription URL pattern, fork/customization with GitHub Pages (Source: GitHub Actions), local setup commands, `GITHUB_TOKEN` usage, and test/lint commands.

Independent verification completed: `.venv/bin/python -m pytest tests/ -v` (7 passed), `.venv/bin/ruff check .` (passed), and `.venv/bin/ruff format --check .` (passed). All acceptance criteria and Definition of Done items are satisfied; no warnings or follow-up actions required.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
