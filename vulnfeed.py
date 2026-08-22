import logging
import os
import sys
import textwrap
from datetime import UTC, datetime, timedelta

import yaml
from feedgen.feed import FeedGenerator

import sources

log = logging.getLogger("vulnfeed")

# Retention defaults, applied when config.yaml has no `feed:` section so
# existing forks keep working untouched.
DEFAULT_MAX_ITEMS = 100
DEFAULT_MAX_AGE_DAYS: int | None = None


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)


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


def detail_score(advisory: dict) -> int:
    """How much usable detail an advisory record carries.

    Used to pick a winner when the same vulnerability arrives from more than one
    source: the repository advisory and the global database entry for one CVE
    are rarely equally complete.
    """
    score = 0
    if advisory.get("cve_id"):
        score += 1
    if _cvss_summary(advisory):
        score += 1
    score += len(advisory.get("cwes") or [])
    score += len(_affected_packages(advisory))
    if advisory.get("description"):
        score += 1
    return score


def deduplicate_advisories(advisories: list[dict]) -> list[dict]:
    """Collapse duplicates by GHSA ID, then by CVE ID across sources.

    GHSA ID alone was enough while GitHub repositories were the only source. Now
    that the same vulnerability can arrive as both a repository advisory and a
    global-database entry, a CVE-level pass is needed too — the two records
    carry different GHSA IDs but describe one vulnerability.
    """
    by_ghsa: dict[str, dict] = {}
    for advisory in advisories:
        ghsa_id = advisory["ghsa_id"]
        incumbent = by_ghsa.get(ghsa_id)
        if incumbent is None or detail_score(advisory) > detail_score(incumbent):
            by_ghsa[ghsa_id] = advisory

    by_cve: dict[str, dict] = {}
    unique: list[dict] = []
    for advisory in by_ghsa.values():
        cve_id = advisory.get("cve_id")
        if not cve_id:
            unique.append(advisory)
            continue

        incumbent = by_cve.get(cve_id)
        if incumbent is None:
            by_cve[cve_id] = advisory
        elif detail_score(advisory) > detail_score(incumbent):
            log.info(
                "Preferring %s over %s for %s (more detail)",
                advisory["ghsa_id"],
                incumbent["ghsa_id"],
                cve_id,
            )
            by_cve[cve_id] = advisory
        else:
            log.info(
                "Dropping duplicate %s; %s already covers %s",
                advisory["ghsa_id"],
                incumbent["ghsa_id"],
                cve_id,
            )

    return unique + list(by_cve.values())


def aggregate_advisories(
    advisories: list[dict],
    max_items: int | None = None,
    max_age_days: int | None = None,
    now: datetime | None = None,
) -> list[dict]:
    """Deduplicate, drop withdrawn advisories, sort newest first, and trim."""
    live = []
    for advisory in advisories:
        if advisory.get("withdrawn_at"):
            # GitHub retracted it; without this it stayed in the feed forever.
            log.info("Skipping withdrawn advisory %s", advisory.get("ghsa_id"))
            continue
        live.append(advisory)

    ordered = sorted(deduplicate_advisories(live), key=_published_at, reverse=True)

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


def _cvss_summary(advisory: dict) -> str | None:
    """Human-readable CVSS score and vector, from either shape the API uses."""
    cvss = advisory.get("cvss") or {}
    score = cvss.get("score")
    vector = cvss.get("vector_string")

    if score is None and not vector:
        severities = advisory.get("cvss_severities") or {}
        for key in ("cvss_v4", "cvss_v3"):
            candidate = severities.get(key) or {}
            if candidate.get("score") is not None or candidate.get("vector_string"):
                score, vector = candidate.get("score"), candidate.get("vector_string")
                break

    if score is not None and vector:
        return f"CVSS {score} ({vector})"
    if score is not None:
        return f"CVSS {score}"
    if vector:
        return f"CVSS {vector}"
    return None


def _affected_packages(advisory: dict) -> list[str]:
    """One line per affected package: ecosystem/name, range, and patched version."""
    lines = []
    for vulnerability in advisory.get("vulnerabilities") or []:
        package = vulnerability.get("package") or {}
        name = package.get("name")
        if not name:
            continue

        ecosystem = package.get("ecosystem")
        line = f"{ecosystem}/{name}" if ecosystem else name

        version_range = vulnerability.get("vulnerable_version_range")
        if version_range:
            line = f"{line} {version_range}"

        # Repository advisories use patched_versions (a string); the global
        # advisory database uses first_patched_version (sometimes an object).
        patched = vulnerability.get("patched_versions") or vulnerability.get(
            "first_patched_version"
        )
        if isinstance(patched, dict):
            patched = patched.get("identifier")
        if patched:
            line = f"{line} (patched: {patched})"

        lines.append(line)
    return lines


def describe_advisory(advisory: dict) -> str:
    """Advisory body prefixed with a metadata block.

    Kept as plain text/markdown rather than HTML: the body GitHub returns is
    already markdown, and converting it would mean a new dependency and a risk
    of mangling it. Every field here is optional and absent ones are omitted.
    """
    facts = []
    if advisory.get("cve_id"):
        facts.append(advisory["cve_id"])

    cvss = _cvss_summary(advisory)
    if cvss:
        facts.append(cvss)

    cwes = [cwe.get("cwe_id") for cwe in advisory.get("cwes") or [] if cwe.get("cwe_id")]
    if cwes:
        facts.append(", ".join(cwes))

    blocks = []
    if facts:
        blocks.append(" · ".join(facts))

    affected = _affected_packages(advisory)
    if affected:
        blocks.append("Affected:\n" + "\n".join(f"- {line}" for line in affected))

    body = advisory.get("description") or advisory.get("summary") or ""
    if not blocks:
        return body
    return "\n\n".join(blocks) + "\n\n---\n\n" + body


def advisory_title(advisory: dict) -> str:
    severity = (advisory.get("severity") or "unknown").upper()
    repo = advisory.get("repo", "")
    title = f"[{severity}] {repo} — {advisory['summary']}"
    if advisory.get("cve_id"):
        title = f"{title} ({advisory['cve_id']})"
    return title


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
        entry.title(advisory_title(advisory))
        entry.link(href=advisory["html_url"])
        entry.description(describe_advisory(advisory))
        entry.published(advisory["published_at"])
        entry.guid(advisory["ghsa_id"], permalink=False)

        categories = [{"term": severity}]
        if repo:
            categories.append({"term": repo})
        entry.category(categories)

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


def collect_advisories(config: dict, token: str | None = None) -> sources.SourceResult:
    """Fetch advisories from every configured source.

    Dispatch is a registry lookup rather than an if/elif chain, so a new source
    is a new module plus a registry entry. Each source isolates failures across
    its own targets.
    """
    combined = sources.SourceResult()

    for feed in config.get("feeds", []):
        name = feed.get("source")
        fetch = sources.get_source(name)
        if fetch is None:
            # Previously a bare `continue`, which silently ignored typos.
            log.error("Unsupported source %r in config; skipping this feed entry", name)
            continue

        combined.merge(fetch(feed, token=token))

    return combined


def main(
    config_path: str = "config.yaml",
    output_path: str = "public/feed.xml",
    token: str | None = None,
    index_only: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
) -> int:
    """Generate the feed and index. Returns a process exit code."""
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO, format="%(levelname)s %(message)s"
    )

    config = load_config(config_path)
    output_dir = os.path.dirname(output_path) or "."

    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)
        index_path = os.path.join(output_dir, "index.html")
        with open(index_path, "w") as f:
            f.write(generate_index(config))

    if index_only:
        return 0

    result = collect_advisories(config, token=token)
    repo_count = len(result.succeeded) + len(result.failed)

    log.info(
        "%d advisories from %d repos (%d succeeded, %d failed)",
        len(result.advisories),
        repo_count,
        len(result.succeeded),
        len(result.failed),
    )
    if result.failed:
        log.warning("Repos that failed: %s", ", ".join(result.failed))

    if result.failed and not result.succeeded:
        # Every repo failing points at a systemic problem — a bad token, an API
        # outage, no network. Leave the published feed alone rather than
        # replacing it with an empty one.
        log.error("Every configured repo failed; leaving %s unchanged", output_path)
        return 1

    if not result.advisories:
        # Legitimate for a config watching quiet repos, so not an error.
        log.warning("No advisories found across %d repos", len(result.succeeded))

    site_url = config.get("site", {}).get("url", "")
    feed_url = f"{site_url}/feed.xml" if site_url else ""

    max_items, max_age_days = feed_limits(config)
    aggregated = aggregate_advisories(
        result.advisories, max_items=max_items, max_age_days=max_age_days
    )

    if dry_run:
        log.info("Dry run: would write %d advisories to %s", len(aggregated), output_path)
        return 0

    feed_xml = generate_feed(aggregated, feed_url=feed_url)
    with open(output_path, "wb") as output_file:
        output_file.write(feed_xml)

    log.info("Wrote %d advisories to %s", len(aggregated), output_path)
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate the aggregated security advisory feed.")
    parser.add_argument("--config", default="config.yaml", help="path to the config file")
    parser.add_argument("--output", default="public/feed.xml", help="path to write the RSS feed to")
    parser.add_argument(
        "--index-only", action="store_true", help="regenerate index.html without fetching"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="fetch and report counts without writing any file"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="enable debug logging")
    args = parser.parse_args()

    sys.exit(
        main(
            config_path=args.config,
            output_path=args.output,
            token=os.getenv("GITHUB_TOKEN"),
            index_only=args.index_only,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    )
