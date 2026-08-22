import logging
import os
import textwrap
import time

import requests
import yaml
from feedgen.feed import FeedGenerator

log = logging.getLogger("vulnfeed")

GITHUB_API_ROOT = "https://api.github.com"

# (connect, read) seconds. Without this a stalled connection blocks until the
# Actions six-hour job limit.
REQUEST_TIMEOUT = (5, 30)

# GitHub's security-advisories endpoint defaults to 30 results per page, which
# silently truncated the feed for every busy repo before pagination was added.
PER_PAGE = 100

# Guards against a malformed Link header cycling forever.
MAX_PAGES = 50

MAX_ATTEMPTS = 4
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)


def _backoff_seconds(response: requests.Response | None, attempt: int) -> float:
    """Seconds to wait before the next attempt, honouring Retry-After when given."""
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except (TypeError, ValueError):
            log.warning("Ignoring unparseable Retry-After header: %r", retry_after)
    return float(2**attempt)


def _get_with_retries(url: str, headers: dict, params: dict | None = None) -> requests.Response:
    """GET a URL, retrying transient failures with bounded exponential backoff."""
    for attempt in range(MAX_ATTEMPTS):
        is_last = attempt == MAX_ATTEMPTS - 1
        try:
            response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            if is_last:
                raise
            delay = _backoff_seconds(None, attempt)
            log.warning("GET %s failed (%s); retrying in %.0fs", url, exc, delay)
            time.sleep(delay)
            continue

        if not is_last and response.status_code in RETRY_STATUSES:
            delay = _backoff_seconds(response, attempt)
            log.warning("GET %s returned %s; retrying in %.0fs", url, response.status_code, delay)
            time.sleep(delay)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError("retry loop exhausted without returning")  # pragma: no cover


def fetch_github_advisories(repo: str, token: str | None = None) -> list[dict]:
    """Fetch every security advisory published in a repository's security tab."""
    url = f"{GITHUB_API_ROOT}/repos/{repo}/security-advisories"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    advisories: list[dict] = []
    params: dict | None = {"per_page": PER_PAGE}

    for _ in range(MAX_PAGES):
        response = _get_with_retries(url, headers=headers, params=params)
        batch = response.json()
        if not batch:
            break
        advisories.extend(batch)

        next_url = response.links.get("next", {}).get("url")
        if not next_url:
            break
        # The Link header URL already carries per_page and page.
        url, params = next_url, None
    else:
        log.warning("Stopped paginating %s after %d pages", repo, MAX_PAGES)

    return advisories


def aggregate_advisories(advisories: list[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for advisory in advisories:
        ghsa_id = advisory["ghsa_id"]
        if ghsa_id not in seen:
            seen[ghsa_id] = advisory

    return sorted(seen.values(), key=lambda advisory: advisory["published_at"], reverse=True)


def generate_feed(advisories: list[dict], feed_url: str = "") -> bytes:
    fg = FeedGenerator()
    fg.id(feed_url or "https://github.com/vulnfeed")
    fg.title("VulnFeed — Security Advisories")
    fg.link(href=feed_url or "https://vulnfeed", rel="self")
    fg.description("Aggregated security advisories from GitHub repositories")

    for advisory in advisories:
        severity = (advisory.get("severity") or "unknown").upper()
        repo = advisory.get("repo", "")

        entry = fg.add_entry(order="append")
        entry.id(advisory["ghsa_id"])
        entry.title(f"[{severity}] {repo} — {advisory['summary']}")
        entry.link(href=advisory["html_url"])
        entry.description(advisory["description"])
        entry.published(advisory["published_at"])
        entry.guid(advisory["ghsa_id"], permalink=False)

    return fg.rss_str(pretty=True)


def generate_index(config: dict) -> str:
    site = config.get("site", {})
    site_url = site.get("url", "")
    github_url = site.get("github", "")
    feed_url = f"{site_url}/feed.xml" if site_url else "feed.xml"

    repos = []
    for feed in config.get("feeds", []):
        if feed.get("source") == "github":
            repos.extend(feed.get("repos", []))

    repo_items = "\n".join(f"    <li>{repo}</li>" for repo in repos)

    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>VulnFeed</title>
          <style>
            body {{
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
              max-width: 640px;
              margin: 4rem auto;
              padding: 0 1.5rem;
              color: #1a1a1a;
              line-height: 1.6;
            }}
            h1 {{ margin-bottom: 0.25rem; }}
            .subtitle {{ color: #555; margin-top: 0; }}
            .feed-link {{
              display: inline-block;
              margin: 1.5rem 0;
              padding: 0.6rem 1.2rem;
              background: #f60;
              color: #fff;
              text-decoration: none;
              border-radius: 4px;
              font-weight: 600;
            }}
            .feed-link:hover {{ background: #d55; }}
            code {{
              background: #f4f4f4;
              padding: 0.15em 0.4em;
              border-radius: 3px;
              font-size: 0.9em;
            }}
            ul {{ padding-left: 1.2rem; }}
            footer {{ margin-top: 3rem; font-size: 0.85rem; color: #888; }}
            footer a {{ color: #888; }}
          </style>
        </head>
        <body>
          <h1>VulnFeed</h1>
          <p class="subtitle">Aggregated security advisories from GitHub repositories</p>

          <a class="feed-link" href="feed.xml">Subscribe to RSS Feed</a>

          <p>
            VulnFeed polls GitHub's security advisory API for a curated list of open-source
            projects and publishes a single consolidated RSS feed, updated daily.
          </p>

          <h2>Usage</h2>
          <p>Add the feed URL to your RSS reader:</p>
          <p><code>{feed_url}</code></p>

          <h2>Monitored repositories</h2>
          <ul>
        {repo_items}
          </ul>

          <footer>
            <a href="{github_url}">View source on GitHub</a>
          </footer>
        </body>
        </html>
        """)


def main(
    config_path: str = "config.yaml",
    output_path: str = "public/feed.xml",
    token: str | None = None,
    index_only: bool = False,
) -> None:
    config = load_config(config_path)
    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w") as f:
        f.write(generate_index(config))

    if index_only:
        return

    all_advisories = []
    for feed in config.get("feeds", []):
        if feed.get("source") != "github":
            continue
        for repo in feed.get("repos", []):
            advisories = fetch_github_advisories(repo, token=token)
            for advisory in advisories:
                advisory["repo"] = repo
                all_advisories.append(advisory)

    site_url = config.get("site", {}).get("url", "")
    feed_url = f"{site_url}/feed.xml" if site_url else ""

    aggregated = aggregate_advisories(all_advisories)
    feed_xml = generate_feed(aggregated, feed_url=feed_url)

    with open(output_path, "wb") as output_file:
        output_file.write(feed_xml)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--index-only", action="store_true")
    args = parser.parse_args()

    github_token = os.getenv("GITHUB_TOKEN")
    main(token=github_token, index_only=args.index_only)
