# VulnFeed

Aggregated security advisory RSS feed from GitHub repositories.

## How it works

1. `vulnfeed.py` reads `config.yaml` to get the list of GitHub repositories to monitor.
2. For each configured repo, it fetches GitHub Security Advisories from the GitHub API.
3. It deduplicates/sorts advisories and generates an RSS feed at `public/feed.xml`.

## Configuration

`config.yaml` controls which repositories are monitored and how much history the feed keeps.

```yaml
site:
  url: https://<username>.github.io/vulnfeed
  github: https://github.com/<username>/vulnfeed

feed:
  max_items: 100        # most recent advisories to publish
  # max_age_days: 365   # optional: also drop anything older than this

feeds:
  - source: github
    repos:
      - owner/repo
```

The `feed:` section is optional. Omit it and the defaults apply: `max_items: 100` and no
age limit. Both limits are applied after advisories are sorted newest-first, so it is
always the most recent ones that are kept.

Advisories that GitHub has withdrawn are excluded automatically.

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

### Command-line options

```
--config CONFIG   path to the config file (default: config.yaml)
--output OUTPUT   path to write the RSS feed to (default: public/feed.xml)
--index-only      regenerate index.html without fetching
--dry-run         fetch and report counts without writing any file
-v, --verbose     enable debug logging
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
