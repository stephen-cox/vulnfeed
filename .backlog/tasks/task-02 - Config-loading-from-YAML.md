---
id: TASK-02
title: Config loading from YAML
status: To Do
assignee: []
created_date: '2026-04-14 09:17'
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
- [ ] #1 vulnfeed.py exists with a load_config() function that accepts an optional config_path parameter
- [ ] #2 load_config() parses a YAML file and returns a dict with a 'feeds' key containing a list of source configs
- [ ] #3 tests/test_vulnfeed.py exists with a test_load_config test that creates a temp config and verifies parsing
- [ ] #4 pytest tests/test_vulnfeed.py::test_load_config passes
- [ ] #5 ruff check . and ruff format --check . pass with no errors
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 All acceptance criteria verified and marked as done
- [ ] #2 All tests pass
- [ ] #3 All linting checks pass
- [ ] #4 Any manual tests pass
<!-- DOD:END -->
