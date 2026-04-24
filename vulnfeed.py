import os
import textwrap

import requests
import yaml
from feedgen.feed import FeedGenerator


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)


def fetch_github_advisories(repo: str, token: str | None = None) -> list[dict]:
    url = f"https://api.github.com/repos/{repo}/security-advisories"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


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
    fg.title("VulnFeed – Security Advisories")
    fg.link(href=feed_url or "https://vulnfeed", rel="self")
    fg.description("Aggregated security advisories from GitHub repositories")

    for advisory in advisories:
        severity = (advisory.get("severity") or "unknown").upper()
        repo = advisory.get("repo", "")

        entry = fg.add_entry()
        entry.id(advisory["ghsa_id"])
        entry.title(f"[{severity}] {repo} – {advisory['summary']}")
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
