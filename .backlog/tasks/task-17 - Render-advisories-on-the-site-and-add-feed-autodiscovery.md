---
id: TASK-17
title: Render advisories on the site and add feed autodiscovery
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 07:25'
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
- [x] #1 The index page renders the most recent advisories with severity, repo, summary, CVE ID, published date, and a link
- [x] #2 The page shows a last-updated timestamp
- [x] #3 Advisories are visually distinguishable by severity
- [x] #4 The head contains a link rel="alternate" type="application/rss+xml" pointing at the feed
- [x] #5 Page markup lives in a template file rather than an inline f-string
- [x] #6 generate_index accepts advisories and renders correctly when given none
- [x] #7 --index-only still produces a valid page without fetching
- [x] #8 The page includes a dark-mode media query
- [x] #9 The layout is usable at mobile widths
- [x] #10 Generated HTML is well-formed and advisory content is correctly escaped
- [x] #11 Tests cover rendering with advisories, rendering with none, and escaping of advisory text
- [x] #12 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Moved the page out of the 70-line f-string and into `templates/index.html`, rendered with `string.Template`. Chose that over Jinja2 to avoid a new dependency — the page needs seven substitutions and no logic, and the real win was escaping every CSS brace, which `string.Template` removes entirely.

The page now renders the published advisories: severity badge, origin, linked summary, date, CVE, and CVSS per item, with a `2 advisories, last updated 22 Aug 2026 at 06:17 UTC` line above. Severity is distinguished by a coloured badge with a distinct `unknown` fallback. The `What is monitored` section lists both source types separately, so the packages added in TASK-16 are visible alongside the repos.

Added `<link rel="alternate" type="application/rss+xml">` to the head — without it, browsers and reader extensions could not detect the feed from the page. Added a `prefers-color-scheme: dark` palette (all colours are CSS custom properties, redefined once in the dark block) and a `max-width: 32rem` breakpoint, with `word-break` on the long package identifiers that would otherwise overflow on a phone.

All advisory text goes through `html.escape`, including URLs and the origin label. A test feeds a hostile summary, link, and repo through and asserts no raw `<script>` survives and the page stays well-formed.

**Two problems found and fixed along the way.**

*`--index-only` would have wiped the advisory list.* It runs on every push to `main` and does not fetch, so once the page carried advisories it would have rebuilt an empty one and left it that way until the next scheduled run. Added `read_published_advisories()`, which reads the committed `feed.xml` — the record of what is actually published — and recovers severity and repo from the `<category>` elements TASK-14 added, with the summary and CVE parsed back out of the title. That parse is reliable because this module writes the title format it reads. Missing or corrupt feed returns None and the page falls back to a placeholder rather than claiming zero advisories.

*RSS `pubDate` is RFC 2822, not ISO 8601.* Caught by running the round-trip against a real generated feed: every recovered date rendered as "date unknown". `_published_at` now falls back to `parsedate_to_datetime`, so both formats parse.

`generate_index(config, advisories=None)` distinguishes three states: `None` renders "The feed has not been generated yet", an empty list renders "No advisories are currently published", and a populated list renders the items. `main()` writes the index after the fetch in the normal path so it can include them.

Verification: `.venv/bin/python -m pytest tests/ -q` → 103 passed, adding 20 tests in `tests/test_index.py` covering tag-balance well-formedness in all three states (via an `HTMLParser` subclass that understands void elements), rendering, severity badges and the unknown fallback, the timestamp, autodiscovery, both source types, an empty config, escaping of hostile input, advisories missing every optional field, dark mode, the mobile breakpoint, the feed round-trip, corrupt and missing feeds, and date parsing in both formats. Rendered the real page from a 274-advisory fixture and inspected both modes directly. `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
