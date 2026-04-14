---
id: TASK-05
title: Generate RSS feed from advisories
status: To Do
assignee: []
created_date: '2026-04-14 09:18'
labels: []
milestone: m-0
dependencies:
  - TASK-02
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: high
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the `generate_feed()` function in `vulnfeed.py` that takes a list of aggregated advisory dicts and produces an RSS XML feed using the `feedgen` library.

The function should:
- Accept `advisories` (list of dicts) and an optional `feed_url` string
- Create a `FeedGenerator` instance and set:
  - `id` to feed_url (or fallback `"https://github.com/vulnfeed"`)
  - `title` to `"VulnFeed — Security Advisories"`
  - `link` with href=feed_url, rel="self"
  - `description` to `"Aggregated security advisories from GitHub repositories"`
- For each advisory, add an entry with:
  - `title`: `[SEVERITY] owner/repo — summary` (severity uppercased, e.g. `[HIGH] zammad/zammad — SQL injection`)
  - `link`: the advisory's `html_url`
  - `description`: the advisory's `description` field
  - `published`: the advisory's `published_at` field
  - `guid`: the advisory's `ghsa_id` (not a permalink)
- Return the RSS XML as bytes via `fg.rss_str(pretty=True)`

Use TDD: write a test that passes one advisory dict, calls `generate_feed()`, parses the returned XML with `xml.etree.ElementTree`, and asserts the channel title, item title format, link, description, and guid contain expected values.

Key feedgen API usage:
```python
from feedgen.feed import FeedGenerator
fg = FeedGenerator()
fg.id('...')
fg.title('...')
fg.link(href='...', rel='self')
fg.description('...')
fe = fg.add_entry()
fe.id('...')
fe.title('...')
fe.link(href='...')
fe.description('...')
fe.published('...')
fe.guid('...', permalink=False)
fg.rss_str(pretty=True)  # returns bytes
```
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 generate_feed(advisories, feed_url) exists in vulnfeed.py
- [ ] #2 Feed channel title is 'VulnFeed — Security Advisories'
- [ ] #3 Each RSS item title follows the format '[SEVERITY] owner/repo — Advisory summary' with severity uppercased
- [ ] #4 Each RSS item link points to the GitHub advisory html_url
- [ ] #5 Each RSS item description contains the advisory description text
- [ ] #6 Each RSS item guid is the GHSA ID
- [ ] #7 Function returns valid RSS XML as bytes
- [ ] #8 test_generate_feed passes — parses XML and verifies channel title, item title, link, description, guid
- [ ] #9 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
