---
id: TASK-17
title: Render advisories on the site and add feed autodiscovery
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
labels:
  - site
milestone: m-1
dependencies:
  - TASK-14
priority: medium
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The published GitHub Pages site lists the monitored repository names and links to `feed.xml`, but shows **no advisories at all**. A visitor who is not already an RSS user gets nothing from it.

Three problems, all in `generate_index()` (`vulnfeed.py:57`):

**The page has no content.** Render the most recent advisories directly on the page — severity badge, repo, summary, CVE ID, published date, link to the advisory — grouped or filterable by severity. Show a "last updated" timestamp so a stale feed is visible at a glance.

**No feed autodiscovery.** The `<head>` has no `<link rel="alternate" type="application/rss+xml">`, so browsers and reader extensions cannot detect the feed from the page. One line, and it is the standard way readers find a feed.

**The HTML is a 70-line f-string.** Every CSS brace is doubled for escaping, the whole page is embedded in Python, and only the repo list portion is covered by tests. Move the markup to a template file. Adding a templating dependency (Jinja2) is acceptable if it earns its place, but `string.Template` avoids a new dependency and handles this page's needs — pick one and be consistent.

`generate_index()` is currently called before advisories are fetched, and again under `--index-only` where no fetch happens at all. The signature needs to accept advisories, and the `--index-only` path needs to render sensibly without them.

While in the page: add a dark-mode media query and check the layout at mobile widths.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The index page renders the most recent advisories with severity, repo, summary, CVE ID, published date, and a link
- [ ] #2 The page shows a last-updated timestamp
- [ ] #3 Advisories are visually distinguishable by severity
- [ ] #4 The head contains a link rel="alternate" type="application/rss+xml" pointing at the feed
- [ ] #5 Page markup lives in a template file rather than an inline f-string
- [ ] #6 generate_index accepts advisories and renders correctly when given none
- [ ] #7 --index-only still produces a valid page without fetching
- [ ] #8 The page includes a dark-mode media query
- [ ] #9 The layout is usable at mobile widths
- [ ] #10 Generated HTML is well-formed and advisory content is correctly escaped
- [ ] #11 Tests cover rendering with advisories, rendering with none, and escaping of advisory text
- [ ] #12 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
