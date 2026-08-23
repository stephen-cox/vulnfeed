---
id: TASK-16
title: Add GitHub Advisory Database package-level source
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 07:05'
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
- [x] #1 sources/ghsa.py implements the fetch_advisories interface from TASK-15
- [x] #2 The choice between the REST /advisories endpoint and the GraphQL securityAdvisories connection is made and recorded with its rationale
- [x] #3 config.yaml supports source: ghsa with ecosystem and package entries
- [x] #4 GHSA payloads are normalised into the shared advisory dict shape
- [x] #5 Deduplication keys on GHSA ID, falling back to CVE ID for cross-source duplicates
- [x] #6 When the same vulnerability arrives from both sources, the record with more detail is kept
- [x] #7 config.yaml is updated with package entries for the monitored projects that publish to a package ecosystem
- [x] #8 The new source is documented in README.md
- [x] #9 Before/after advisory counts demonstrate the new source surfaces advisories the repo source missed — via local-HTTP integration test, not the live API; see Final Summary
- [x] #10 Tests cover GHSA normalisation, cross-source CVE deduplication, and an empty result set
- [x] #11 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `sources/ghsa.py`, implementing the plugin interface from TASK-15 and registered as `source: ghsa`.

**REST over GraphQL.** `GET /advisories` accepts `ecosystem` and `affects` filters directly and paginates with the same Link headers as every other endpoint here, so it reuses `sources.http.paginate` unchanged. The GraphQL `securityAdvisories` connection would have required a separate client and cursor-based paging for no additional filtering power. Recorded in the module docstring.

**Normalisation** turned out to be light: the global payload already matches the shared shape on `ghsa_id`, `summary`, `description`, `severity`, `published_at`, `withdrawn_at`, `cvss`, `cwes`, and `vulnerabilities`. What it lacks is an origin label, so `normalise()` sets `repo` to `ecosystem/package` and falls back to the API `url` if `html_url` is absent. It copies rather than mutating the source dict. TASK-14's `_affected_packages` already read `first_patched_version` as well as `patched_versions`, so the global shape needed no further work there.

**Cross-source deduplication.** `aggregate_advisories` keyed on `ghsa_id` alone, which is now insufficient: one vulnerability can arrive as both a repository advisory and a database entry under two different GHSA IDs. Added `deduplicate_advisories()`, which collapses by GHSA ID and then by CVE ID, and `detail_score()`, which ranks candidates by populated CVE, CVSS, CWE, affected-package, and description fields so the richer record wins regardless of arrival order. Withdrawn advisories are filtered *before* deduplication, so a retracted richer record cannot win a CVE and then vanish — that case is covered by a test.

**A misspelled package is made visible.** A wrong package name returns an empty list, not a 404, so it would have contributed nothing silently — the exact failure mode this milestone exists to eliminate. The source logs `No advisories found for <package>; check the package name` in that case.

**AC #9 not verified against the live API.** As with TASK-11, this session's GitHub access is scoped to `stephen-cox/vulnfeed` and direct `api.github.com` calls return 403, so real before/after counts were not obtainable. Substituted an integration test in `tests/test_integration.py` that serves both endpoints from a local HTTP server — the repo tab holds one advisory, the package holds that one plus a third-party filing — and runs `main()` end to end with a github-only config and then a both-sources config. It asserts the second run publishes strictly more, and that the advisory present in both is published once.

**Package names in `config.yaml` are unverified.** Added five entries (`composer/composer`, `espocrm/espocrm`, `mautic/core` on Packagist, `open-webui` on PyPI, `github.com/argoproj/argo-cd/v2` on Go) for the monitored projects that publish to an ecosystem GitHub indexes. These could not be confirmed against the live API. The config carries a comment saying so, and any wrong name will announce itself in the first run's log via the warning above. The remaining monitored projects — Icinga, Rocket.Chat, Zammad, Taiga, WordPress core — are not conventionally published to an indexed package ecosystem and were left out.

Verification: `.venv/bin/python -m pytest tests/ -q` → 81 passed, adding twelve tests in `tests/test_ghsa.py` (label building, request parameters, normalisation, per-package isolation, the empty-result warning, nameless entries, six ecosystems) and nine in `tests/test_vulnfeed.py` (detail scoring, CVE collapsing in both orders, distinct CVEs, null CVEs not collapsing, repeated GHSA IDs, end-to-end aggregation, the withdrawn-duplicate case, and both sources merging). `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass. Real `config.yaml` resolves both sources across 12 repos and 5 packages. `README.md` documents both sources, ecosystem values, the typo warning, and the dedup behaviour.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
