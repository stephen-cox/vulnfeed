---
id: TASK-06
title: Main entrypoint wiring everything together
status: Done
assignee: []
created_date: '2026-04-14 09:18'
updated_date: '2026-04-14 11:13'
labels: []
milestone: m-0
dependencies:
  - TASK-03
  - TASK-04
  - TASK-05
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: high
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the `main()` function in `vulnfeed.py` that orchestrates the full pipeline: load config, fetch advisories for each repo, aggregate them, generate the RSS feed, and write it to disk. Also add the `if __name__ == "__main__"` block.

The function should:
- Accept optional params: `config_path` (default `"config.yaml"`), `output_path` (default `"public/feed.xml"`), `token` (default `None`)
- Call `load_config(config_path)` to get the config
- Loop through each feed in `config["feeds"]` where `source == "github"`
- For each repo in that feed, call `fetch_github_advisories(repo, token=token)`
- Inject `advisory["repo"] = repo` into each advisory dict (needed for RSS title formatting)
- Collect all advisories into a flat list
- Call `aggregate_advisories()` on the full list
- Call `generate_feed()` on the aggregated list
- Create the output directory if it doesn't exist (`os.makedirs`)
- Write the RSS bytes to the output file

The `if __name__ == "__main__"` block should read `GITHUB_TOKEN` from environment and call `main(token=token)`.

Use TDD: write a test that creates a temp config file pointing to one repo, mocks `requests.get` to return a fake advisory, calls `main()` with the temp paths, and asserts the output XML file exists and contains the expected advisory data.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 main(config_path, output_path, token) exists in vulnfeed.py with correct defaults
- [x] #2 main() loads config, fetches advisories for each github repo, aggregates, generates feed, and writes to output_path
- [x] #3 Each advisory dict gets a 'repo' key injected before aggregation
- [x] #4 Output directory is created if it doesn't exist
- [x] #5 if __name__ == '__main__' block reads GITHUB_TOKEN from env and calls main()
- [x] #6 test_main_writes_feed_xml passes — uses mocked API, verifies output file exists and contains expected GHSA ID and severity
- [x] #7 All existing tests still pass (pytest tests/ -v shows 6 passing)
- [x] #8 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented and verified task-06 end-to-end. `vulnfeed.py` now includes `main(config_path='config.yaml', output_path='public/feed.xml', token=None)` that loads config, fetches GitHub advisories per repo, injects `repo` into each advisory, aggregates advisories, generates RSS XML, ensures output directory creation, and writes the feed to disk; `__main__` reads `GITHUB_TOKEN` and invokes `main(token=github_token)`.

Verification evidence: `.venv/bin/python -m pytest tests/ -v` => 7/7 passing (including new `test_main_writes_feed_xml` that mocks API and asserts output contains GHSA ID + severity), `.venv/bin/ruff check .` passed, `.venv/bin/ruff format --check .` passed. Security/operational review found no hardcoded secrets, no unauthorized scope changes, and acceptable error/logging posture for this CLI batch script.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
