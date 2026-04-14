---
id: TASK-02
title: Config loading from YAML
status: Done
assignee:
  - '@codex'
created_date: '2026-04-14 09:17'
updated_date: '2026-04-14 10:56'
labels: []
milestone: m-0
dependencies:
  - TASK-01
documentation:
  - docs/superpowers/plans/2026-04-14-vulnfeed-implementation.md
priority: high
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Implement the `load_config()` function in `vulnfeed.py` that reads `config.yaml` and returns the parsed configuration as a Python dictionary.

The function should:
- Accept an optional `config_path` parameter (default: `"config.yaml"`)
- Open the file and parse it with `yaml.safe_load()`
- Return the parsed dictionary

The config format is:
```yaml
feeds:
  - source: github
    repos:
      - owner/repo
```

Use TDD: write the test first in `tests/test_vulnfeed.py`, verify it fails, then implement. The test should use `tmp_path` to create a temporary config file and assert the parsed structure matches expectations.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 vulnfeed.py exists with a load_config() function that accepts an optional config_path parameter
- [x] #2 load_config() parses a YAML file and returns a dict with a 'feeds' key containing a list of source configs
- [x] #3 tests/test_vulnfeed.py exists with a test_load_config test that creates a temp config and verifies parsing
- [x] #4 pytest tests/test_vulnfeed.py::test_load_config passes
- [x] #5 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented YAML config loading by adding `load_config(config_path="config.yaml")` in `vulnfeed.py` using `yaml.safe_load`, and added `tests/test_vulnfeed.py::test_load_config` to verify temporary YAML parsing via `tmp_path`.

Verification results: `.venv/bin/python -m pytest tests/test_vulnfeed.py::test_load_config -v` PASS, `.venv/bin/python -m pytest tests/ -v` PASS (2/2), `.venv/bin/ruff check .` PASS, `.venv/bin/ruff format --check .` PASS, plus manual runtime check of default-path loading from `config.yaml` PASS. No blocking issues found; recommend adding explicit negative-path tests (missing file / invalid YAML) in a future task.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 All acceptance criteria verified and marked as done
- [x] #2 All tests pass
- [x] #3 All linting checks pass
- [x] #4 Any manual tests pass
<!-- DOD:END -->
