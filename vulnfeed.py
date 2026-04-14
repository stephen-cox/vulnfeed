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
    fg.title("VulnFeed — Security Advisories")
    fg.link(href=feed_url, rel="self")
    fg.description("Aggregated security advisories from GitHub repositories")

    for advisory in advisories:
        severity = (advisory.get("severity") or "unknown").upper()
        repo = advisory.get("repo", "")

        entry = fg.add_entry()
        entry.id(advisory["ghsa_id"])
        entry.title(f"[{severity}] {repo} — {advisory['summary']}")
        entry.link(href=advisory["html_url"])
        entry.description(advisory["description"])
        entry.published(advisory["published_at"])
        entry.guid(advisory["ghsa_id"], permalink=False)

    return fg.rss_str(pretty=True)
