---
id: doc-01
title: VulnFeed Design Spec
type: other
created_date: '2026-04-14 08:51'
updated_date: '2026-04-14 09:01'
---
# VulnFeed Design Spec

**Date:** 2026-04-14
**Status:** Approved

## Overview

VulnFeed is a simple app that uses GitHub Actions to scan a configurable list of GitHub repositories for security advisories and publishes them as an aggregated RSS feed. It runs daily, generates a static XML file, and serves it via GitHub Pages.

The tool is primarily for personal use. Others can fork the repo, update the configuration for the software they care about, and publish their own feed.

## Approach

Python script + GitHub Actions + GitHub Pages. Python was chosen for its clean syntax, good libraries (`feedgen`, `requests`), and ease of modification for anyone forking the repo.

## Project Structure

```
vulnfeed/
├── config.yaml              # List of GitHub repos to monitor
├── vulnfeed.py              # Main script — fetch, aggregate, generate RSS
├── requirements.txt         # feedgen, requests
├── .github/workflows/
│   └── update-feed.yml      # Scheduled Action (daily 4am UTC)
├── public/
│   └── feed.xml             # Generated RSS feed (served by GitHub Pages)
└── README.md
```

- `config.yaml` is the single file a fork needs to edit
- `public/` is used for GitHub Pages output (GitHub Pages can be configured to serve from a custom directory via a workflow, or use the `gh-pages` branch approach — see GitHub Pages Setup below)
- One Python file. No packages, no `src/`, no unnecessary abstractions

## Configuration Format

```yaml
# config.yaml
feeds:
  - source: github
    repos:
      - zammad/zammad
      - django/django
      - pallets/flask
```

The `source: github` key is present so the config format extends naturally if other source types are added later (e.g., `source: nvd`). For now, only `github` is supported.

**Note for future:** When additional sources are added, consider extracting a simple plugin system — each source type as a Python file in a `sources/` directory with a standard `fetch_advisories(config) -> list[Advisory]` function signature. This keeps new sources self-contained without needing if/elif chains.

## Data Flow

1. **GitHub Action triggers** daily at 4am UTC
2. **Script reads** `config.yaml` to get the list of repos
3. **For each repo**, hits the GitHub Security Advisories API (`GET /repos/{owner}/{repo}/security-advisories`) using the `GITHUB_TOKEN` available in Actions
4. **Collects advisories** into a flat list, deduplicates by advisory ID, sorts by published date (newest first)
5. **Generates RSS feed** using `feedgen` — title, link, description, published date, severity
6. **Writes `public/feed.xml`**
7. **Commits and pushes** the updated feed.xml (only if it changed)

No database, no state file. Each run fetches current advisories and regenerates the full feed. Simple and idempotent.

## RSS Feed Content

Each RSS item includes:

- **Title:** `[SEVERITY] repo/name — Advisory summary` (e.g., `[HIGH] zammad/zammad — SQL injection in ticket search`)
- **Link:** URL to the GitHub advisory page
- **Description:** The advisory summary text from GitHub
- **Published date:** When the advisory was published
- **GUID:** The GHSA ID (globally unique, stable)

The feed itself is titled "VulnFeed — Security Advisories" with a link back to the GitHub Pages URL.

## GitHub Action

```yaml
# .github/workflows/update-feed.yml
name: Update Feed
on:
  schedule:
    - cron: '0 4 * * *'    # Daily at 4am UTC
  workflow_dispatch:         # Manual trigger for testing

permissions:
  contents: write           # To commit feed.xml
  security-events: read     # To read advisories

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python vulnfeed.py
      - name: Commit and push if changed
        run: |
          git diff --quiet public/feed.xml && exit 0
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"
          git add public/feed.xml
          git commit -m "Update feed"
          git push
```

Key points:
- `workflow_dispatch` allows manual triggering for testing
- Only commits if `feed.xml` actually changed
- Uses the built-in `GITHUB_TOKEN` — no secrets to configure

## GitHub Pages Setup

GitHub Pages natively supports serving from `/` or `/docs`, but not `/public`. To serve from `public/`, add a deployment step to the GitHub Action that uses `actions/upload-pages-artifact` and `actions/deploy-pages` to publish the `public/` directory. This is handled within the same workflow — no separate config needed.

One-time repo setting: enable GitHub Pages with "Source: GitHub Actions" (not "Deploy from a branch"). The feed URL will be:

```
https://<username>.github.io/vulnfeed/feed.xml
```

The README should document this setup step for anyone forking the repo.
