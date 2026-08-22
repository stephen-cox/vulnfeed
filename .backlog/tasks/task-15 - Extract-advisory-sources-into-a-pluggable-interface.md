---
id: TASK-15
title: Extract advisory sources into a pluggable interface
status: To Do
assignee: []
created_date: '2026-08-22 05:40'
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
- [ ] #1 A sources/ package exists with the GitHub fetching moved into sources/github.py
- [ ] #2 Each source module exposes fetch_advisories(feed_config, token) -> list[dict]
- [ ] #3 The normalised advisory dict shape consumed by the aggregator is documented
- [ ] #4 main() dispatches via a source registry lookup, not an if/elif chain
- [ ] #5 An unknown source value logs an error naming the source and skips that feed entry
- [ ] #6 The existing config.yaml works unchanged
- [ ] #7 CLI accepts --config, --output, --dry-run, and --verbose
- [ ] #8 --dry-run fetches and reports advisory counts without writing any file
- [ ] #9 Generated feed.xml is byte-identical to the pre-refactor output for the same input
- [ ] #10 Existing tests still pass, updated only for import paths
- [ ] #11 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
