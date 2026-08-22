---
id: m-1
title: "Post-MVP Hardening"
---

## Description

Close the gaps found after the MVP shipped: correct silent data loss in the fetch layer, get tests running in CI, broaden advisory coverage beyond repo-filed advisories, and make the published feed and site more useful.

## Themes

- **Reliability** (TASK-11, TASK-12, TASK-13) — the feed is currently truncated, can hang, and aborts entirely on a single bad repo.
- **CI** (TASK-10, TASK-18, TASK-19) — tests never run in CI and pull requests are unchecked.
- **Coverage** (TASK-15, TASK-16) — repo-level advisories miss anything filed against the project's published packages.
- **Presentation** (TASK-14, TASK-17, TASK-20) — richer feed items, a site that shows advisories, and alerting on criticals.
