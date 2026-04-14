# VulnFeed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python script that fetches GitHub Security Advisories for configured repos and publishes an aggregated RSS feed via GitHub Pages.

**Architecture:** A single Python script (`vulnfeed.py`) reads a YAML config file listing GitHub repos, fetches their security advisories via the GitHub REST API, deduplicates and sorts them, and generates an RSS XML file using `feedgen`. A GitHub Actions workflow runs this daily and deploys the output to GitHub Pages.

**Tech Stack:** Python 3.12, feedgen, requests, PyYAML, pytest, ruff, GitHub Actions, GitHub Pages

---

## File Structure

| File | Responsibility |
|------|---------------|
| `config.yaml` | User-editable list of GitHub repos to monitor |
| `vulnfeed.py` | Main script: load config, fetch advisories, generate RSS |
| `tests/test_vulnfeed.py` | Tests for config loading, advisory processing, and feed generation |
| `requirements.txt` | Python dependencies |
| `.github/workflows/update-feed.yml` | Scheduled workflow: run script, deploy to GitHub Pages |
| `public/feed.xml` | Generated RSS feed (gitignored, produced by script) |
| `pyproject.toml` | Ruff configuration |
| `README.md` | Setup instructions for users and forkers |

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `public/.gitkeep`

- [ ] **Step 1: Create `requirements.txt`**

```
feedgen==1.0.0
requests==2.32.3
PyYAML==6.0.2
pytest==8.3.5
ruff==0.11.6
```

- [ ] **Step 2: Create `config.yaml`**

```yaml
feeds:
  - source: github
    repos:
      - zammad/zammad
      - django/django
      - pallets/flask
```

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 4: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
public/feed.xml
```

- [ ] **Step 5: Create `public/.gitkeep`**

Empty file so the `public/` directory exists in git.

- [ ] **Step 6: Set up virtual environment and install dependencies**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt config.yaml pyproject.toml .gitignore public/.gitkeep
git commit -m "chore: project scaffolding with config and dependencies"
```

---

### Task 2: Config loading

**Files:**
- Create: `tests/test_vulnfeed.py`
- Create: `vulnfeed.py`

- [ ] **Step 1: Write the failing test for config loading**

Create `tests/test_vulnfeed.py`:

```python
import yaml
from vulnfeed import load_config


def test_load_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - zammad/zammad
      - django/django
"""
    )
    config = load_config(str(config_file))
    assert len(config["feeds"]) == 1
    assert config["feeds"][0]["source"] == "github"
    assert config["feeds"][0]["repos"] == ["zammad/zammad", "django/django"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vulnfeed.py::test_load_config -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'vulnfeed'`

- [ ] **Step 3: Write minimal implementation**

Create `vulnfeed.py`:

```python
import yaml


def load_config(config_path="config.yaml"):
    with open(config_path) as f:
        return yaml.safe_load(f)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vulnfeed.py::test_load_config -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vulnfeed.py tests/test_vulnfeed.py
git commit -m "feat: add config loading from YAML"
```

---

### Task 3: Fetch GitHub Security Advisories

**Files:**
- Modify: `tests/test_vulnfeed.py`
- Modify: `vulnfeed.py`

- [ ] **Step 1: Write the failing test for fetching advisories**

Append to `tests/test_vulnfeed.py`:

```python
from unittest.mock import patch, Mock
from vulnfeed import fetch_github_advisories


def test_fetch_github_advisories():
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "ghsa_id": "GHSA-1234-5678-9abc",
            "html_url": "https://github.com/owner/repo/security/advisories/GHSA-1234-5678-9abc",
            "summary": "SQL injection in query parser",
            "severity": "high",
            "published_at": "2026-04-01T12:00:00Z",
            "description": "A SQL injection vulnerability was found.",
        },
        {
            "ghsa_id": "GHSA-aaaa-bbbb-cccc",
            "html_url": "https://github.com/owner/repo/security/advisories/GHSA-aaaa-bbbb-cccc",
            "summary": "XSS in admin panel",
            "severity": "medium",
            "published_at": "2026-03-15T08:00:00Z",
            "description": "A stored XSS vulnerability exists in the admin panel.",
        },
    ]
    mock_response.raise_for_status = Mock()

    with patch("vulnfeed.requests.get", return_value=mock_response) as mock_get:
        advisories = fetch_github_advisories("owner/repo", token="fake-token")

    mock_get.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/security-advisories",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer fake-token",
        },
    )
    assert len(advisories) == 2
    assert advisories[0]["ghsa_id"] == "GHSA-1234-5678-9abc"
    assert advisories[1]["severity"] == "medium"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vulnfeed.py::test_fetch_github_advisories -v`
Expected: FAIL with `ImportError: cannot import name 'fetch_github_advisories'`

- [ ] **Step 3: Write minimal implementation**

Add to `vulnfeed.py`:

```python
import requests


def fetch_github_advisories(repo, token=None):
    url = f"https://api.github.com/repos/{repo}/security-advisories"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vulnfeed.py::test_fetch_github_advisories -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vulnfeed.py tests/test_vulnfeed.py
git commit -m "feat: add GitHub Security Advisories fetching"
```

---

### Task 4: Aggregate and deduplicate advisories

**Files:**
- Modify: `tests/test_vulnfeed.py`
- Modify: `vulnfeed.py`

- [ ] **Step 1: Write the failing test for aggregation**

Append to `tests/test_vulnfeed.py`:

```python
from vulnfeed import aggregate_advisories


def test_aggregate_advisories_deduplicates():
    advisory_a = {
        "ghsa_id": "GHSA-1111-2222-3333",
        "summary": "Bug A",
        "severity": "high",
        "published_at": "2026-04-01T12:00:00Z",
        "html_url": "https://github.com/owner/repo1/security/advisories/GHSA-1111-2222-3333",
        "description": "Description A",
        "repo": "owner/repo1",
    }
    advisory_b = {
        "ghsa_id": "GHSA-4444-5555-6666",
        "summary": "Bug B",
        "severity": "medium",
        "published_at": "2026-03-15T08:00:00Z",
        "html_url": "https://github.com/owner/repo2/security/advisories/GHSA-4444-5555-6666",
        "description": "Description B",
        "repo": "owner/repo2",
    }
    # Duplicate of advisory_a
    advisory_a_dup = dict(advisory_a)

    result = aggregate_advisories([advisory_a, advisory_b, advisory_a_dup])
    assert len(result) == 2


def test_aggregate_advisories_sorts_newest_first():
    older = {
        "ghsa_id": "GHSA-old",
        "summary": "Old",
        "severity": "low",
        "published_at": "2026-01-01T00:00:00Z",
        "html_url": "https://example.com/old",
        "description": "Old one",
        "repo": "owner/repo",
    }
    newer = {
        "ghsa_id": "GHSA-new",
        "summary": "New",
        "severity": "high",
        "published_at": "2026-04-01T00:00:00Z",
        "html_url": "https://example.com/new",
        "description": "New one",
        "repo": "owner/repo",
    }
    result = aggregate_advisories([older, newer])
    assert result[0]["ghsa_id"] == "GHSA-new"
    assert result[1]["ghsa_id"] == "GHSA-old"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_vulnfeed.py -k "aggregate" -v`
Expected: FAIL with `ImportError: cannot import name 'aggregate_advisories'`

- [ ] **Step 3: Write minimal implementation**

Add to `vulnfeed.py`:

```python
def aggregate_advisories(advisories):
    seen = {}
    for advisory in advisories:
        ghsa_id = advisory["ghsa_id"]
        if ghsa_id not in seen:
            seen[ghsa_id] = advisory
    return sorted(seen.values(), key=lambda a: a["published_at"], reverse=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_vulnfeed.py -k "aggregate" -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add vulnfeed.py tests/test_vulnfeed.py
git commit -m "feat: add advisory aggregation with dedup and sorting"
```

---

### Task 5: Generate RSS feed

**Files:**
- Modify: `tests/test_vulnfeed.py`
- Modify: `vulnfeed.py`

- [ ] **Step 1: Write the failing test for RSS generation**

Append to `tests/test_vulnfeed.py`:

```python
import xml.etree.ElementTree as ET
from vulnfeed import generate_feed


def test_generate_feed():
    advisories = [
        {
            "ghsa_id": "GHSA-1234-5678-9abc",
            "html_url": "https://github.com/owner/repo/security/advisories/GHSA-1234-5678-9abc",
            "summary": "SQL injection in query parser",
            "severity": "high",
            "published_at": "2026-04-01T12:00:00Z",
            "description": "A SQL injection vulnerability was found.",
            "repo": "owner/repo",
        },
    ]
    xml_bytes = generate_feed(advisories, feed_url="https://example.github.io/vulnfeed/feed.xml")

    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    assert channel.find("title").text == "VulnFeed \u2014 Security Advisories"

    items = channel.findall("item")
    assert len(items) == 1
    assert items[0].find("title").text == "[HIGH] owner/repo \u2014 SQL injection in query parser"
    assert items[0].find("link").text == "https://github.com/owner/repo/security/advisories/GHSA-1234-5678-9abc"
    assert items[0].find("description").text == "A SQL injection vulnerability was found."
    assert "GHSA-1234-5678-9abc" in items[0].find("guid").text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vulnfeed.py::test_generate_feed -v`
Expected: FAIL with `ImportError: cannot import name 'generate_feed'`

- [ ] **Step 3: Write minimal implementation**

Add to `vulnfeed.py`:

```python
from feedgen.feed import FeedGenerator


def generate_feed(advisories, feed_url=""):
    fg = FeedGenerator()
    fg.id(feed_url or "https://github.com/vulnfeed")
    fg.title("VulnFeed \u2014 Security Advisories")
    fg.link(href=feed_url, rel="self")
    fg.description("Aggregated security advisories from GitHub repositories")

    for advisory in advisories:
        fe = fg.add_entry()
        fe.id(advisory["ghsa_id"])
        severity = (advisory.get("severity") or "unknown").upper()
        repo = advisory.get("repo", "")
        fe.title(f"[{severity}] {repo} \u2014 {advisory['summary']}")
        fe.link(href=advisory["html_url"])
        fe.description(advisory["description"])
        fe.published(advisory["published_at"])
        fe.guid(advisory["ghsa_id"], permalink=False)

    return fg.rss_str(pretty=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vulnfeed.py::test_generate_feed -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add vulnfeed.py tests/test_vulnfeed.py
git commit -m "feat: add RSS feed generation with feedgen"
```

---

### Task 6: Main entrypoint

**Files:**
- Modify: `tests/test_vulnfeed.py`
- Modify: `vulnfeed.py`

- [ ] **Step 1: Write the failing test for the main function**

Append to `tests/test_vulnfeed.py`:

```python
import os
from unittest.mock import patch, Mock
from vulnfeed import main


def test_main_writes_feed_xml(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - owner/repo
"""
    )
    output_file = tmp_path / "public" / "feed.xml"
    os.makedirs(tmp_path / "public")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "ghsa_id": "GHSA-test-1234-abcd",
            "html_url": "https://github.com/owner/repo/security/advisories/GHSA-test-1234-abcd",
            "summary": "Test vulnerability",
            "severity": "critical",
            "published_at": "2026-04-01T00:00:00Z",
            "description": "Test description.",
        },
    ]
    mock_response.raise_for_status = Mock()

    with patch("vulnfeed.requests.get", return_value=mock_response):
        main(
            config_path=str(config_file),
            output_path=str(output_file),
            token="fake-token",
        )

    assert output_file.exists()
    content = output_file.read_text()
    assert "GHSA-test-1234-abcd" in content
    assert "[CRITICAL] owner/repo" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_vulnfeed.py::test_main_writes_feed_xml -v`
Expected: FAIL with `ImportError: cannot import name 'main'`

- [ ] **Step 3: Write minimal implementation**

Add to `vulnfeed.py`:

```python
import os


def main(config_path="config.yaml", output_path="public/feed.xml", token=None):
    config = load_config(config_path)

    all_advisories = []
    for feed in config["feeds"]:
        if feed["source"] != "github":
            continue
        for repo in feed["repos"]:
            advisories = fetch_github_advisories(repo, token=token)
            for advisory in advisories:
                advisory["repo"] = repo
            all_advisories.extend(advisories)

    aggregated = aggregate_advisories(all_advisories)
    feed_xml = generate_feed(aggregated)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(feed_xml)


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN")
    main(token=token)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_vulnfeed.py::test_main_writes_feed_xml -v`
Expected: PASS

- [ ] **Step 5: Run all tests**

Run: `python -m pytest tests/ -v`
Expected: All 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add vulnfeed.py tests/test_vulnfeed.py
git commit -m "feat: add main entrypoint that wires everything together"
```

---

### Task 7: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/update-feed.yml`

- [ ] **Step 1: Create the workflow file**

Create `.github/workflows/update-feed.yml`:

```yaml
name: Update Feed

on:
  schedule:
    - cron: '0 4 * * *'
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - run: pip install -r requirements.txt

      - name: Lint and format check
        run: |
          ruff check .
          ruff format --check .

      - run: python vulnfeed.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Commit feed.xml if changed
        run: |
          git add public/feed.xml
          git diff --cached --quiet public/feed.xml && exit 0
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git commit -m "Update feed"
          git push

  deploy:
    needs: update
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main

      - name: Pull latest (includes any feed.xml commit)
        run: git pull origin main

      - uses: actions/configure-pages@v5

      - uses: actions/upload-pages-artifact@v3
        with:
          path: public

      - id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Commit**

```bash
mkdir -p .github/workflows
git add .github/workflows/update-feed.yml
git commit -m "ci: add GitHub Actions workflow for daily feed updates and Pages deploy"
```

---

### Task 8: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

Create `README.md`:

```markdown
# VulnFeed

Aggregated security advisory RSS feed from GitHub repositories. Runs daily via GitHub Actions and publishes to GitHub Pages.

## How it works

A Python script reads `config.yaml` for a list of GitHub repos, fetches their security advisories via the GitHub API, and generates an RSS feed at `public/feed.xml`.

## Subscribe

Once deployed, your feed URL is:

```
https://<username>.github.io/vulnfeed/feed.xml
```

Add this URL to any RSS reader.

## Fork and customize

1. Fork this repo
2. Edit `config.yaml` to list the repos you want to monitor
3. Enable GitHub Pages in your repo settings:
   - Go to Settings > Pages
   - Set Source to **GitHub Actions**
4. The workflow runs daily at 4am UTC, or trigger it manually from the Actions tab

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python vulnfeed.py
```

The generated feed will be written to `public/feed.xml`.

Set `GITHUB_TOKEN` for authenticated API access (higher rate limits):

```bash
export GITHUB_TOKEN=ghp_your_token_here
python vulnfeed.py
```

## Running tests

```bash
python -m pytest tests/ -v
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```

---

### Task 9: End-to-end smoke test

**Files:** None (manual verification)

- [ ] **Step 1: Run the script locally against real GitHub API**

Run:
```bash
source .venv/bin/activate
export GITHUB_TOKEN=$(gh auth token)
python vulnfeed.py
```

Expected: `public/feed.xml` is created with advisory entries.

- [ ] **Step 2: Verify the generated feed**

Run:
```bash
head -50 public/feed.xml
```

Expected: Valid RSS XML with `<channel>`, `<item>` elements, titles in `[SEVERITY] repo — summary` format.

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 4: Final commit if any adjustments were needed**

Only if changes were made during smoke testing.
