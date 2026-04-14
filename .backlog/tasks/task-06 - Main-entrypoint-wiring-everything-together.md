---
id: TASK-06
title: Main entrypoint wiring everything together
status: To Do
assignee: []
created_date: '2026-04-14 09:18'
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
- [ ] #1 main(config_path, output_path, token) exists in vulnfeed.py with correct defaults
- [ ] #2 main() loads config, fetches advisories for each github repo, aggregates, generates feed, and writes to output_path
- [ ] #3 Each advisory dict gets a 'repo' key injected before aggregation
- [ ] #4 Output directory is created if it doesn't exist
- [ ] #5 if __name__ == '__main__' block reads GITHUB_TOKEN from env and calls main()
- [ ] #6 test_main_writes_feed_xml passes — uses mocked API, verifies output file exists and contains expected GHSA ID and severity
- [ ] #7 All existing tests still pass (pytest tests/ -v shows 6 passing)
- [ ] #8 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
