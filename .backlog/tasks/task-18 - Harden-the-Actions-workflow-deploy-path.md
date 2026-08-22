---
id: TASK-18
title: Harden the Actions workflow deploy path
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
labels:
  - ci
milestone: m-1
dependencies:
  - TASK-10
priority: medium
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Two structural problems in `.github/workflows/update-feed.yml`, plus a documentation error they expose.

**The deploy is racy.** `build-index` and `update-feed` commit generated files to `main`, then `deploy` separately checks out `main` and runs `git pull` to pick them up. Nothing guarantees the pull sees the commit that just landed, and nothing guarantees another push has not landed in between. Deploy can publish a stale or mixed `public/` directory. Pass the built directory between jobs as a workflow artifact instead of round-tripping it through a git branch — the generating job uploads it, `deploy` downloads it, and no checkout-and-pull is needed.

**Concurrent runs can collide.** A manual `workflow_dispatch` overlapping the nightly schedule produces two jobs both committing and pushing to `main`; the second push fails on a non-fast-forward. Add a `concurrency` group with `cancel-in-progress: false` so runs serialise rather than race.

**A doc claim is wrong.** `CLAUDE.md` states `public/feed.xml` is "(gitignored, served by GitHub Pages)". It is not gitignored — `.gitignore` does not mention it, it is tracked in git, and the workflow commits it daily. Correct that line. If this task's artifact-based deploy makes committing the generated feed unnecessary, decide explicitly whether to keep committing it (useful as a change history and as a fallback if a run fails) or to stop, and make the docs match whichever is chosen.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The generated public/ directory is passed to the deploy job as a workflow artifact
- [ ] #2 The deploy job no longer checks out main and runs git pull to obtain the build output
- [ ] #3 A concurrency group prevents overlapping runs from pushing to main simultaneously
- [ ] #4 cancel-in-progress is false so a scheduled run is not cancelled by a manual one
- [ ] #5 The CLAUDE.md claim that public/feed.xml is gitignored is corrected
- [ ] #6 A decision on whether to keep committing the generated feed is made and reflected in both the workflow and the docs
- [ ] #7 Workflow YAML parses without errors
- [ ] #8 A manual workflow_dispatch run completes end to end and deploys the expected content
- [ ] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
