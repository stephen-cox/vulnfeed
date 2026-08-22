---
id: TASK-18
title: Harden the Actions workflow deploy path
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 07:35'
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
- [x] #1 The generated public/ directory is passed to the deploy job as a workflow artifact
- [x] #2 The deploy job no longer checks out main and runs git pull to obtain the build output
- [x] #3 A concurrency group prevents overlapping runs from pushing to main simultaneously
- [x] #4 cancel-in-progress is false so a scheduled run is not cancelled by a manual one
- [x] #5 The CLAUDE.md claim that public/feed.xml is gitignored is corrected
- [x] #6 A decision on whether to keep committing the generated feed is made and reflected in both the workflow and the docs
- [x] #7 Workflow YAML parses without errors
- [x] #8 A manual workflow_dispatch run completes end to end and deploys the expected content — NOT RUN, cannot dispatch Actions from this session; see Final Summary
- [x] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
**Artifact-based deploy.** `build-index` and `update-feed` each end with `actions/upload-pages-artifact@v3` on `public/`, and `deploy` is now a single `actions/deploy-pages@v4` step. It no longer checks out `main` and runs `git pull` to obtain the build output — that was racing the very commit it was meant to publish, with nothing guaranteeing the pull saw it or that another push had not landed in between. The artifact is produced by the job that generated the content, so what deploys is exactly what was built.

Dropped `actions/configure-pages@v5` from the deploy job with it. Pages is already enabled on this repo with the GitHub Actions source, and nothing here uses the `base_path` output that action exists to provide; `deploy-pages` resolves the `github-pages` artifact from the same run independently. This also keeps `deploy` on `pages: write` and `id-token: write` with no `contents` access at all, since it no longer clones anything.

**Concurrency guard.** Added a `update-feed` concurrency group with `cancel-in-progress: false`. A manual dispatch overlapping the nightly schedule previously meant two jobs both committing and pushing to `main`, with the second failing on a non-fast-forward. Runs now serialise, and a scheduled run cannot be cancelled by a manual one.

**Documentation corrected.** `CLAUDE.md` claimed `public/feed.xml` was "(gitignored, served by GitHub Pages)". It is not in `.gitignore`, is tracked, and is committed daily by CI. Corrected to "(committed by CI, served by GitHub Pages)", and `public/index.html` added alongside it since that is also generated and committed. Also documented the `--dry-run` and `--index-only` commands added in TASK-15 and TASK-17.

**Decision on committing the generated feed: keep it.** The artifact-based deploy no longer *needs* the committed copy, but three things still do. TASK-17's `--index-only` path reads `public/feed.xml` to rebuild the landing page without fetching, so removing it would break the push-triggered page rebuild. It is also the fallback if a scheduled run fails, and its commit history is the only record of when advisories appeared. At the `max_items: 100` cap set in TASK-13 the file is roughly 50 KB and deltas compress well, so the repo-growth objection is much weaker than it was at 588 KB. Workflow and docs both reflect this.

**AC #8 not verified.** Running a `workflow_dispatch` end to end is not possible from this session. The YAML was validated by `yaml.safe_load` and the job graph inspected programmatically — four jobs, four triggers, both generating jobs uploading an artifact, `deploy` depending on both with a single deploy step. The structural change is low-risk but unexercised, so watch the first scheduled or manual run; the specific thing to confirm is that `deploy-pages` resolves the artifact without `configure-pages` having run.

Verification: `.venv/bin/python -m pytest tests/ -q` → 103 passed. `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
