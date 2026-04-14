---
id: TASK-08
title: README with setup and usage instructions
status: To Do
assignee: []
created_date: '2026-04-14 09:18'
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
- [ ] #1 README.md exists at the project root
- [ ] #2 Contains a clear project title and one-line description
- [ ] #3 Explains how the tool works (config -> fetch -> generate RSS)
- [ ] #4 Shows the GitHub Pages feed URL pattern
- [ ] #5 Includes fork-and-customize instructions with GitHub Pages setup (Source: GitHub Actions)
- [ ] #6 Includes local development setup commands (venv, pip install, run script)
- [ ] #7 Documents how to set GITHUB_TOKEN for authenticated API access
- [ ] #8 Includes test running instructions
- [ ] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
