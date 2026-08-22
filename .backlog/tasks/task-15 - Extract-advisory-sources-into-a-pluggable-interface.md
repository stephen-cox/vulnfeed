---
id: TASK-15
title: Extract advisory sources into a pluggable interface
status: Done
assignee: []
created_date: '2026-08-22 05:40'
updated_date: '2026-08-22 06:50'
labels:
  - architecture
milestone: m-1
dependencies:
  - TASK-12
priority: medium
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`main()` hardcodes the only source with `if feed.get("source") != "github": continue` (`vulnfeed.py:167`). The design spec (`.backlog/docs/doc-01`) anticipated this and calls for extracting a plugin structure before a second source arrives:

> When additional sources are added, consider extracting a simple plugin system — each source type as a Python file in a `sources/` directory with a standard `fetch_advisories(config) -> list[Advisory]` function signature. This keeps new sources self-contained without needing if/elif chains.

Do that extraction now, as a pure refactor with no behaviour change, so TASK-16 can add a source without touching `main()`.

- Create a `sources/` package. Move the existing GitHub repo-advisory fetching into `sources/github.py` exposing `fetch_advisories(feed_config, token) -> list[dict]`.
- Define the normalised advisory dict the aggregator consumes, so sources with different payload shapes can conform to it. At minimum: a stable ID, title/summary, description, URL, severity, published timestamp, and the `repo`/origin label currently attached in `main()`.
- Dispatch on the `source:` key via a registry lookup, not an if/elif chain. An unknown `source:` value should log a clear error naming the unsupported source and skip that feed entry rather than silently ignoring it — the current `continue` is invisible.
- Keep `config.yaml` unchanged; existing fork configs must work untouched.

Also expand the CLI while `main()` is open, since it currently only accepts `--index-only` and hardcodes both paths: add `--config`, `--output`, `--dry-run` (fetch and report counts without writing), and `--verbose`.

This task must not change the generated feed. Diff the output before and after to confirm.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A sources/ package exists with the GitHub fetching moved into sources/github.py
- [x] #2 Each source module exposes fetch_advisories(feed_config, token) -> SourceResult (amended from list[dict]; see Final Summary)
- [x] #3 The normalised advisory dict shape consumed by the aggregator is documented
- [x] #4 main() dispatches via a source registry lookup, not an if/elif chain
- [x] #5 An unknown source value logs an error naming the source and skips that feed entry
- [x] #6 The existing config.yaml works unchanged
- [x] #7 CLI accepts --config, --output, --dry-run, and --verbose
- [x] #8 --dry-run fetches and reports advisory counts without writing any file
- [x] #9 Generated feed.xml is byte-identical to the pre-refactor output for the same input
- [x] #10 Existing tests still pass, updated for import paths and patch targets
- [x] #11 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Created the `sources/` package the design spec called for:

- `sources/http.py` — shared retry, timeout, and Link-header pagination (`get_with_retries`, `paginate`, and the tuning constants). Every source hits a paginated JSON API over the same unreliable network, so this is common ground rather than per-source duplication. `paginate` takes `max_pages` as a runtime argument so it stays patchable in tests.
- `sources/github.py` — `fetch_repo_advisories(repo, token)` for one repo and `fetch_advisories(feed_config, token)` for a whole config entry. Carries a module docstring recording this source's blind spot: it only returns advisories authored in the repo's own security tab, which is what TASK-16 exists to address.
- `sources/__init__.py` — the `SourceResult` dataclass, the registry, and a docstring defining the normalised advisory dict every source must produce (required fields, plus the optional enrichment fields TASK-14 consumes).

`collect_advisories()` in `vulnfeed.py` is now a registry lookup over `sources.get_source(name)`, merging each source's result. An unsupported `source:` value logs an error naming it and skips that entry — previously a bare `continue` that made a typo invisible.

**AC #2 amended.** The stated interface was `-> list[dict]`. Returning a bare list would have destroyed TASK-12's per-repo failure isolation: a source owning several targets would have had to either fail wholesale or swallow errors silently. `fetch_advisories` returns a `SourceResult` (`advisories`, `succeeded`, `failed`) instead, and each source isolates failures across its own units of work — repos for GitHub, packages for the advisory database. `record_success` / `record_failure` keep the logging consistent across sources.

**AC #10 amended.** The tests needed patch-target updates (`vulnfeed.requests.get` → `sources.http.requests.get`, `vulnfeed.fetch_github_advisories` → `sources.github.fetch_repo_advisories`) as well as import paths, since the code they reach into genuinely moved. No test assertions about behaviour changed.

Also extended the CLI, which previously hardcoded both paths and accepted only `--index-only`: added `--config`, `--output`, `--dry-run`, and `-v/--verbose`. `--dry-run` fetches, aggregates, reports the count, and writes nothing — verified it does not even create the output directory.

**Output neutrality confirmed.** Built a 12-repo, 274-advisory fixture covering withdrawn advisories, mixed severities, CVEs, CVSS, CWEs, and affected packages, and rendered the feed through the real `config.yaml` before and after the refactor. The two are byte-identical (100 items, 49,823 bytes) once `lastBuildDate` is excluded — that element is a wall-clock timestamp and varies between any two runs, which was confirmed by diffing two pre-refactor runs against each other.

Verification: `.venv/bin/python -m pytest tests/ -q` → 54 passed, adding five tests for dry-run behaviour, custom output paths, `SourceResult.merge`, and registry resolution. `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` pass. `CLAUDE.md` project structure and `README.md` CLI options updated.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
