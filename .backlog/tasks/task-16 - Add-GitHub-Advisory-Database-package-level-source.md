---
id: TASK-16
title: Add GitHub Advisory Database package-level source
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
labels:
  - coverage
milestone: m-1
dependencies:
  - TASK-15
priority: medium
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
This is the largest functional gap in VulnFeed. The `/repos/{owner}/{repo}/security-advisories` endpoint returns **only advisories authored in that repository's own security tab**. Advisories published to the global GitHub Advisory Database against a project's *packages* — filed by third-party reporters, ecosystem maintainers, or CVE assigners rather than by the project itself — are completely invisible to the current feed.

The effect is measurable in the existing config: `taigaio/taiga-events` contributes zero items, and WordPress core CVEs reported through routes other than the repo security tab never appear, despite `WordPress/wordpress-develop` being monitored.

Add a second source using the plugin interface from TASK-15:

- New `sources/ghsa.py` querying `GET /advisories` with `ecosystem` and `affects` filters (or the GraphQL `securityAdvisories` connection if the REST filtering proves insufficient — evaluate both and record the choice).
- New config shape, e.g. `source: ghsa` with a list of `{ecosystem, package}` entries, so a fork can watch `composer/composer` the repo and `composer/composer` the Packagist package independently.
- Normalise the response into the advisory dict defined in TASK-15. GHSA payloads differ from repo-advisory payloads — field mapping is the substance of this task.
- Extend deduplication: `aggregate_advisories()` keys on `ghsa_id`, which is correct for GHSA-vs-GHSA collisions, but the same vulnerability can now legitimately arrive from both sources. Dedupe on GHSA ID first, then CVE ID, preferring whichever record carries more detail.
- Update `config.yaml` with package entries for the currently monitored projects that publish to a package ecosystem, and document the new source in `README.md`.

Verify the coverage claim: record advisory counts per project before and after, and confirm the new source surfaces advisories the repo source missed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 sources/ghsa.py implements the fetch_advisories interface from TASK-15
- [ ] #2 The choice between the REST /advisories endpoint and the GraphQL securityAdvisories connection is made and recorded with its rationale
- [ ] #3 config.yaml supports source: ghsa with ecosystem and package entries
- [ ] #4 GHSA payloads are normalised into the shared advisory dict shape
- [ ] #5 Deduplication keys on GHSA ID, falling back to CVE ID for cross-source duplicates
- [ ] #6 When the same vulnerability arrives from both sources, the record with more detail is kept
- [ ] #7 config.yaml is updated with package entries for the monitored projects that publish to a package ecosystem
- [ ] #8 The new source is documented in README.md
- [ ] #9 Before/after advisory counts demonstrate the new source surfaces advisories the repo source missed
- [ ] #10 Tests cover GHSA normalisation, cross-source CVE deduplication, and an empty result set
- [ ] #11 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
