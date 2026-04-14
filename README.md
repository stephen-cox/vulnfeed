# VulnFeed

Aggregated security advisory RSS feed from GitHub repositories.

## How it works

1. `vulnfeed.py` reads `config.yaml` to get the list of GitHub repositories to monitor.
2. For each configured repo, it fetches GitHub Security Advisories from the GitHub API.
3. It deduplicates/sorts advisories and generates an RSS feed at `public/feed.xml`.

## Subscribe

After GitHub Pages is enabled for your fork, your feed URL will follow this pattern:

`https://<username>.github.io/vulnfeed/feed.xml`

## Fork and customize

1. Fork this repository.
2. Edit `config.yaml` and list the repositories you want to monitor.
3. In your fork, go to **Settings → Pages** and set **Source** to **GitHub Actions**.
4. The workflow runs daily at **4:00 UTC**. You can also run it manually from the **Actions** tab.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python vulnfeed.py
```

### GitHub API authentication

For higher API limits and authenticated advisory access, set `GITHUB_TOKEN` before running:

```bash
export GITHUB_TOKEN="<your_github_token>"
python vulnfeed.py
```

## Running tests

```bash
python -m pytest tests/ -v
```

## Lint and format checks

```bash
ruff check .
ruff format --check .
```
