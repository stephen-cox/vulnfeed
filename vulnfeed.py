import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from html import escape
from string import Template
from xml.etree import ElementTree

import yaml
from feedgen.feed import FeedGenerator

import sources
import sources.ghsa

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

    parsed = None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        # Advisories read back out of a published feed carry RFC 2822 pubDate
        # values rather than the API's ISO 8601 timestamps.
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            parsed = None

    if parsed is None:
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


TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

SEVERITY_CLASSES = frozenset({"critical", "high", "medium", "low"})


def _load_template(name: str) -> Template:
    with open(os.path.join(TEMPLATE_PATH, name)) as template_file:
        return Template(template_file.read())


def _format_date(advisory: dict) -> str:
    published = _published_at(advisory)
    if published == datetime.min.replace(tzinfo=UTC):
        return "date unknown"
    return published.strftime("%-d %b %Y")


def _render_advisory(advisory: dict) -> str:
    severity = (advisory.get("severity") or "unknown").lower()
    badge_class = severity if severity in SEVERITY_CLASSES else "unknown"

    meta = [_format_date(advisory)]
    if advisory.get("cve_id"):
        meta.append(escape(advisory["cve_id"]))
    cvss = _cvss_summary(advisory)
    if cvss:
        meta.append(escape(cvss))

    meta_spans = "".join(f"<span>{part}</span>" for part in meta)

    return (
        '    <li class="advisory">\n'
        '      <div class="advisory-head">\n'
        f'        <span class="badge {badge_class}">{escape(severity.upper())}</span>\n'
        f'        <span class="origin">{escape(advisory.get("repo", ""))}</span>\n'
        "      </div>\n"
        f'      <a class="summary" href="{escape(advisory.get("html_url", ""))}">'
        f"{escape(advisory.get('summary', 'Untitled advisory'))}</a>\n"
        f'      <div class="advisory-meta">{meta_spans}</div>\n'
        "    </li>"
    )


def _render_advisories(advisories: list[dict] | None) -> str:
    if advisories is None:
        return (
            '  <p class="empty">The feed has not been generated yet. '
            "It is rebuilt daily by GitHub Actions.</p>"
        )
    if not advisories:
        return '  <p class="empty">No advisories are currently published.</p>'

    items = "\n".join(_render_advisory(advisory) for advisory in advisories)
    return f'  <ul class="advisories">\n{items}\n  </ul>'


def _render_targets(config: dict) -> str:
    """List what each configured source watches, whichever sources are in use."""
    groups = []
    for feed in config.get("feeds", []):
        source = feed.get("source")
        if source == "github":
            targets = list(feed.get("repos", []))
            heading = "Repository security advisories"
        elif source == "ghsa":
            targets = [sources.ghsa.package_label(package) for package in feed.get("packages", [])]
            heading = "Advisory database, by package"
        else:
            continue

        if not targets:
            continue

        listed = "\n".join(f"    <li>{escape(target)}</li>" for target in targets)
        groups.append(f'  <p>{escape(heading)}</p>\n  <ul class="targets">\n{listed}\n  </ul>')

    return "\n".join(groups) if groups else "  <p>Nothing is configured.</p>"


def read_published_advisories(feed_path: str) -> list[dict] | None:
    """Recover the page's advisory list from an already-published feed.

    `--index-only` runs on every push and does not fetch. Without this it would
    rebuild the page with an empty list and wipe the advisories until the next
    scheduled run. The committed feed is the record of what is published, and
    since this module also writes it, its title format can be parsed back
    reliably.

    Returns None when there is no feed to read.
    """
    if not os.path.exists(feed_path):
        return None

    try:
        root = ElementTree.parse(feed_path).getroot()
    except ElementTree.ParseError as exc:
        log.warning(
            "Could not parse %s (%s); rendering the page without advisories", feed_path, exc
        )
        return None

    channel = root.find("channel")
    if channel is None:
        return None

    advisories = []
    for item in channel.findall("item"):
        categories = [category.text or "" for category in item.findall("category")]
        severity = categories[0] if categories else "UNKNOWN"
        repo = categories[1] if len(categories) > 1 else ""

        title = (item.findtext("title") or "").strip()
        summary = title
        prefix = f"[{severity}] {repo} — "
        if summary.startswith(prefix):
            summary = summary[len(prefix) :]

        cve_id = None
        if summary.endswith(")") and " (CVE-" in summary:
            summary, _, trailing = summary.rpartition(" (")
            cve_id = trailing[:-1]

        advisories.append(
            {
                "ghsa_id": item.findtext("guid") or "",
                "html_url": item.findtext("link") or "",
                "summary": summary,
                "severity": severity.lower(),
                "published_at": item.findtext("pubDate"),
                "repo": repo,
                "cve_id": cve_id,
            }
        )

    return advisories


def generate_index(config: dict, advisories: list[dict] | None = None) -> str:
    """Render the published landing page.

    `advisories` is None when the page is rebuilt without fetching (--index-only),
    which renders a placeholder rather than claiming there are no advisories.
    """
    site = config.get("site", {})
    site_url = site.get("url", "")
    feed_url = f"{site_url}/feed.xml" if site_url else "feed.xml"

    if advisories is None:
        status_line = "Rebuilt daily by GitHub Actions."
        heading = "Latest advisories"
    else:
        generated = datetime.now(UTC).strftime("%-d %b %Y at %H:%M UTC")
        status_line = f"{len(advisories)} advisories, last updated {generated}."
        heading = f"Latest advisories ({len(advisories)})"

    return _load_template("index.html").substitute(
        feed_href=escape(feed_url),
        feed_url=escape(feed_url),
        github_url=escape(site.get("github", "")),
        status_line=escape(status_line),
        advisories_heading=escape(heading),
        advisory_items=_render_advisories(advisories),
        target_items=_render_targets(config),
    )


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
    index_path = os.path.join(output_dir, "index.html")

    if index_only:
        if not dry_run:
            os.makedirs(output_dir, exist_ok=True)
            # No fetch happens here, so reuse whatever the last run published
            # rather than rebuilding the page with an empty advisory list.
            published = read_published_advisories(output_path)
            with open(index_path, "w") as f:
                f.write(generate_index(config, published))
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

    os.makedirs(output_dir, exist_ok=True)

    feed_xml = generate_feed(aggregated, feed_url=feed_url)
    with open(output_path, "wb") as output_file:
        output_file.write(feed_xml)

    with open(index_path, "w") as index_file:
        index_file.write(generate_index(config, aggregated))

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
