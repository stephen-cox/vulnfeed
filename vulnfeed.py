import logging
import os
import sys
import textwrap
import time
from datetime import UTC, datetime, timedelta

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

# Retention defaults, applied when config.yaml has no `feed:` section so
# existing forks keep working untouched.
DEFAULT_MAX_ITEMS = 100
DEFAULT_MAX_AGE_DAYS: int | None = None


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


def _published_at(advisory: dict) -> datetime:
    """Parse an advisory's publication time, treating unusable values as oldest.

    Draft and unpublished advisories can carry a null `published_at`, which used
    to raise TypeError while sorting and take the whole run down with it.
    """
    raw = advisory.get("published_at")
    if not raw:
        log.warning("Advisory %s has no published_at; sorting it last", advisory.get("ghsa_id"))
        return datetime.min.replace(tzinfo=UTC)

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        log.warning(
            "Advisory %s has an unparseable published_at (%r); sorting it last",
            advisory.get("ghsa_id"),
            raw,
        )
        return datetime.min.replace(tzinfo=UTC)

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def aggregate_advisories(
    advisories: list[dict],
    max_items: int | None = None,
    max_age_days: int | None = None,
    now: datetime | None = None,
) -> list[dict]:
    """Deduplicate, drop withdrawn advisories, sort newest first, and trim."""
    seen: dict[str, dict] = {}
    for advisory in advisories:
        if advisory.get("withdrawn_at"):
            # GitHub retracted it; without this it stayed in the feed forever.
            log.info("Skipping withdrawn advisory %s", advisory.get("ghsa_id"))
            continue

        ghsa_id = advisory["ghsa_id"]
        if ghsa_id not in seen:
            seen[ghsa_id] = advisory

    ordered = sorted(seen.values(), key=_published_at, reverse=True)

    if max_age_days:
        cutoff = (now or datetime.now(UTC)) - timedelta(days=max_age_days)
        kept = [advisory for advisory in ordered if _published_at(advisory) >= cutoff]
        if len(kept) < len(ordered):
            log.info(
                "Dropped %d advisories older than %d days", len(ordered) - len(kept), max_age_days
            )
        ordered = kept

    # Applied after sorting, so the newest advisories are the ones retained.
    if max_items is not None and len(ordered) > max_items:
        log.info("Trimming feed from %d to %d items", len(ordered), max_items)
        ordered = ordered[:max_items]

    return ordered


def feed_limits(config: dict) -> tuple[int | None, int | None]:
    """Read retention limits from the optional `feed:` config section."""
    feed_config = config.get("feed") or {}
    return (
        feed_config.get("max_items", DEFAULT_MAX_ITEMS),
        feed_config.get("max_age_days", DEFAULT_MAX_AGE_DAYS),
    )


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


def collect_advisories(config: dict, token: str | None = None) -> tuple[list[dict], list, list]:
    """Fetch advisories from every configured repo, isolating per-repo failures.

    A repo that is renamed, deleted, made private, or transiently unavailable
    must not stop the others from being fetched — before this was isolated, one
    bad entry in config.yaml froze the published feed entirely.

    Returns (advisories, succeeded_repos, failed_repos).
    """
    advisories: list[dict] = []
    succeeded: list[str] = []
    failed: list[str] = []

    for feed in config.get("feeds", []):
        if feed.get("source") != "github":
            continue

        for repo in feed.get("repos", []):
            try:
                fetched = fetch_github_advisories(repo, token=token)
            except requests.RequestException as exc:
                log.error("Failed to fetch advisories for %s: %s", repo, exc)
                failed.append(repo)
                continue
            except Exception:
                log.exception("Unexpected error fetching advisories for %s", repo)
                failed.append(repo)
                continue

            for advisory in fetched:
                advisory["repo"] = repo
            advisories.extend(fetched)
            succeeded.append(repo)
            log.info("Fetched %d advisories from %s", len(fetched), repo)

    return advisories, succeeded, failed


def main(
    config_path: str = "config.yaml",
    output_path: str = "public/feed.xml",
    token: str | None = None,
    index_only: bool = False,
) -> int:
    """Generate the feed and index. Returns a process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    config = load_config(config_path)
    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w") as f:
        f.write(generate_index(config))

    if index_only:
        return 0

    all_advisories, succeeded, failed = collect_advisories(config, token=token)

    log.info(
        "%d advisories from %d repos (%d succeeded, %d failed)",
        len(all_advisories),
        len(succeeded) + len(failed),
        len(succeeded),
        len(failed),
    )
    if failed:
        log.warning("Repos that failed: %s", ", ".join(failed))

    if failed and not succeeded:
        # Every repo failing points at a systemic problem — a bad token, an API
        # outage, no network. Leave the published feed alone rather than
        # replacing it with an empty one.
        log.error("Every configured repo failed; leaving %s unchanged", output_path)
        return 1

    if not all_advisories:
        # Legitimate for a config watching quiet repos, so not an error.
        log.warning("No advisories found across %d repos", len(succeeded))

    site_url = config.get("site", {}).get("url", "")
    feed_url = f"{site_url}/feed.xml" if site_url else ""

    max_items, max_age_days = feed_limits(config)
    aggregated = aggregate_advisories(
        all_advisories, max_items=max_items, max_age_days=max_age_days
    )
    feed_xml = generate_feed(aggregated, feed_url=feed_url)

    with open(output_path, "wb") as output_file:
        output_file.write(feed_xml)

    log.info("Wrote %d advisories to %s", len(aggregated), output_path)
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--index-only", action="store_true")
    args = parser.parse_args()

    github_token = os.getenv("GITHUB_TOKEN")
    sys.exit(main(token=github_token, index_only=args.index_only))
