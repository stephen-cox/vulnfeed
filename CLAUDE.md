
# VulnFeed

Aggregated security advisory RSS feed from GitHub repositories. Runs daily via GitHub Actions and publishes to GitHub Pages.

## Tech Stack

- Python 3.12
- feedgen, requests, PyYAML
- pytest for testing
- ruff for linting and formatting

## Project Structure

```
vulnfeed/
├── config.yaml              # List of GitHub repos to monitor (edit this to customize)
├── vulnfeed.py              # Main script — fetch, aggregate, generate RSS
├── tests/test_vulnfeed.py   # Tests
├── requirements.txt         # Python dependencies
├── pyproject.toml            # ruff and pytest config
├── .github/workflows/
│   └── update-feed.yml      # Scheduled Action (daily 4am UTC)
├── public/
│   └── feed.xml             # Generated RSS feed (gitignored, served by GitHub Pages)
└── docs/                    # Specs and plans (not published)
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Commands

- `python vulnfeed.py` — run the feed generator (set GITHUB_TOKEN env var for API access)
- `python -m pytest tests/ -v` — run tests
- `ruff check .` — lint
- `ruff format --check .` — check formatting
- `ruff format .` — auto-format

---

<!-- BACKLOG.MD MCP GUIDELINES START -->

<CRITICAL_INSTRUCTION>

## BACKLOG WORKFLOW INSTRUCTIONS

This project uses Backlog.md MCP for all task and project management activities.

**CRITICAL GUIDANCE**

- If your client supports MCP resources, read `backlog://workflow/overview` to understand when and how to use Backlog for this project.
- If your client only supports tools or the above request fails, call `backlog.get_backlog_instructions()` to load the tool-oriented overview. Use the `instruction` selector when you need `task-creation`, `task-execution`, or `task-finalization`.

- **First time working here?** Read the overview resource IMMEDIATELY to learn the workflow
- **Already familiar?** You should have the overview cached ("## Backlog.md Overview (MCP)")
- **When to read it**: BEFORE creating tasks, or when you're unsure whether to track work

These guides cover:
- Decision framework for when to create tasks
- Search-first workflow to avoid duplicates
- Links to detailed guides for task creation, execution, and finalization
- MCP tools reference

You MUST read the overview resource to understand the complete workflow. The information is NOT summarized here.

</CRITICAL_INSTRUCTION>

<!-- BACKLOG.MD MCP GUIDELINES END -->
