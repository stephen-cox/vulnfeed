
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
├── vulnfeed.py              # Main script — aggregate, generate RSS and index
├── sources/                 # Pluggable advisory sources
│   ├── __init__.py          # SourceResult, source registry
│   ├── http.py              # Shared retry/timeout/pagination plumbing
│   └── github.py            # Repository security advisories
├── templates/index.html     # Landing page template (string.Template)
├── tests/test_vulnfeed.py   # Unit tests
├── tests/test_ghsa.py       # Advisory database source tests
├── tests/test_index.py      # Landing page tests
├── tests/test_integration.py # Local-HTTP end-to-end tests
├── requirements.txt         # Python dependencies
├── pyproject.toml            # ruff and pytest config
├── .github/
│   ├── dependabot.yml       # Weekly pip and github-actions updates
│   └── workflows/
│       ├── update-feed.yml  # Checks, scheduled feed build, Pages deploy
│       └── codeql.yml       # CodeQL analysis
├── public/
│   ├── feed.xml             # Generated RSS feed (committed by CI, served by GitHub Pages)
│   └── index.html           # Generated landing page (committed by CI)
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
- `python vulnfeed.py --dry-run` — fetch and report counts without writing anything
- `python vulnfeed.py --index-only` — rebuild the landing page from the published feed
- `python -m pytest tests/ -v` — run tests
- `ruff check .` — lint
- `ruff format --check .` — check formatting
- `ruff format .` — auto-format
- `mypy` — type check (vulnfeed.py and sources/)

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
