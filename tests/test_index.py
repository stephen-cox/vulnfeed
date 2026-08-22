"""Tests for the published landing page."""

from html.parser import HTMLParser

from vulnfeed import generate_index, main, read_published_advisories

VOID_ELEMENTS = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track"}
)

CONFIG = {
    "site": {
        "url": "https://example.github.io/vulnfeed",
        "github": "https://github.com/example/vulnfeed",
    },
    "feeds": [
        {"source": "github", "repos": ["owner/repo", "other/project"]},
        {"source": "ghsa", "packages": [{"ecosystem": "composer", "name": "vendor/widget"}]},
    ],
}

ADVISORIES = [
    {
        "ghsa_id": "GHSA-1",
        "html_url": "https://github.com/owner/repo/security/advisories/GHSA-1",
        "summary": "SQL injection in query parser",
        "severity": "critical",
        "published_at": "2026-04-01T12:00:00Z",
        "repo": "owner/repo",
        "cve_id": "CVE-2026-1234",
        "cvss": {"score": 9.8, "vector_string": "CVSS:3.1/AV:N"},
    },
    {
        "ghsa_id": "GHSA-2",
        "html_url": "https://github.com/owner/repo/security/advisories/GHSA-2",
        "summary": "Open redirect",
        "severity": "low",
        "published_at": "2026-03-01T00:00:00Z",
        "repo": "owner/repo",
    },
]


class TagBalanceChecker(HTMLParser):
    """Confirms every non-void element is closed, in order."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_endtag(self, tag) -> None:
        if tag in VOID_ELEMENTS:
            return
        if not self.stack:
            self.errors.append(f"closing </{tag}> with nothing open")
        elif self.stack[-1] != tag:
            self.errors.append(f"closing </{tag}> while <{self.stack[-1]}> is open")
        else:
            self.stack.pop()


def assert_well_formed(html: str) -> None:
    checker = TagBalanceChecker()
    checker.feed(html)
    checker.close()
    assert checker.errors == [], checker.errors
    assert checker.stack == [], f"unclosed tags: {checker.stack}"


def test_index_with_advisories_is_well_formed() -> None:
    assert_well_formed(generate_index(CONFIG, ADVISORIES))


def test_index_without_advisories_is_well_formed() -> None:
    assert_well_formed(generate_index(CONFIG, []))
    assert_well_formed(generate_index(CONFIG))


def test_index_renders_each_advisory() -> None:
    html = generate_index(CONFIG, ADVISORIES)

    assert "SQL injection in query parser" in html
    assert "https://github.com/owner/repo/security/advisories/GHSA-1" in html
    assert "CVE-2026-1234" in html
    assert "CVSS 9.8 (CVSS:3.1/AV:N)" in html
    assert "1 Apr 2026" in html
    assert "owner/repo" in html


def test_index_distinguishes_severities() -> None:
    html = generate_index(CONFIG, ADVISORIES)

    assert '<span class="badge critical">CRITICAL</span>' in html
    assert '<span class="badge low">LOW</span>' in html


def test_index_falls_back_to_the_unknown_badge() -> None:
    html = generate_index(CONFIG, [{**ADVISORIES[1], "severity": None}])

    assert '<span class="badge unknown">UNKNOWN</span>' in html


def test_index_shows_a_last_updated_timestamp() -> None:
    html = generate_index(CONFIG, ADVISORIES)

    assert "2 advisories, last updated" in html
    assert "UTC" in html


def test_index_declares_feed_autodiscovery() -> None:
    """Without this, browsers and reader extensions cannot find the feed."""
    html = generate_index(CONFIG, ADVISORIES)

    assert (
        '<link rel="alternate" type="application/rss+xml" '
        'title="VulnFeed — Security Advisories" '
        'href="https://example.github.io/vulnfeed/feed.xml">'
    ) in html


def test_index_without_a_fetch_shows_a_placeholder_not_an_empty_claim() -> None:
    """--index-only renders before any fetch; it must not claim zero advisories."""
    html = generate_index(CONFIG)

    assert "has not been generated yet" in html
    assert "No advisories are currently published" not in html


def test_index_with_an_empty_feed_says_so() -> None:
    html = generate_index(CONFIG, [])

    assert "No advisories are currently published" in html
    assert "0 advisories, last updated" in html


def test_index_lists_both_source_types() -> None:
    html = generate_index(CONFIG, ADVISORIES)

    assert "Repository security advisories" in html
    assert "<li>owner/repo</li>" in html
    assert "Advisory database, by package" in html
    assert "<li>composer:vendor/widget</li>" in html


def test_index_handles_a_config_with_no_feeds() -> None:
    html = generate_index({"site": {}}, [])

    assert "Nothing is configured." in html
    assert_well_formed(html)


def test_index_escapes_advisory_text() -> None:
    """Advisory summaries are third-party text and must not inject markup."""
    hostile = {
        **ADVISORIES[1],
        "summary": '<script>alert("xss")</script>',
        "html_url": 'https://example.com/"><script>alert(1)</script>',
        "repo": "owner/<b>repo</b>",
    }

    html = generate_index(CONFIG, [hostile])

    assert "<script>" not in html
    assert "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;" in html
    assert "&lt;b&gt;repo&lt;/b&gt;" in html
    assert_well_formed(html)


def test_index_handles_advisories_missing_optional_fields() -> None:
    bare = {"ghsa_id": "GHSA-bare", "repo": "owner/repo"}

    html = generate_index(CONFIG, [bare])

    assert "Untitled advisory" in html
    assert "date unknown" in html
    assert_well_formed(html)


def test_index_declares_a_dark_mode_palette() -> None:
    assert "@media (prefers-color-scheme: dark)" in generate_index(CONFIG, ADVISORIES)


def test_index_declares_a_mobile_breakpoint() -> None:
    html = generate_index(CONFIG, ADVISORIES)

    assert 'name="viewport"' in html
    assert "@media (max-width: 32rem)" in html


def test_read_published_advisories_returns_none_without_a_feed(tmp_path) -> None:
    assert read_published_advisories(str(tmp_path / "missing.xml")) is None


def test_read_published_advisories_survives_a_corrupt_feed(tmp_path, caplog) -> None:
    corrupt = tmp_path / "feed.xml"
    corrupt.write_text("<rss><channel>truncated")

    with caplog.at_level("WARNING", logger="vulnfeed"):
        assert read_published_advisories(str(corrupt)) is None

    assert "Could not parse" in caplog.text


def test_index_only_reuses_the_published_feed(tmp_path) -> None:
    """A push rebuilds the page without fetching; it must not wipe the advisories."""
    from vulnfeed import generate_feed

    config_file = tmp_path / "config.yaml"
    config_file.write_text("feeds:\n  - source: github\n    repos: [owner/repo]\n")
    feed_path = tmp_path / "public" / "feed.xml"
    feed_path.parent.mkdir()
    feed_path.write_bytes(generate_feed(ADVISORIES))

    main(config_path=str(config_file), output_path=str(feed_path), index_only=True)

    html = (feed_path.parent / "index.html").read_text()
    assert "SQL injection in query parser" in html
    assert "Open redirect" in html
    assert "has not been generated yet" not in html


def test_index_only_round_trips_severity_repo_and_cve(tmp_path) -> None:
    from vulnfeed import generate_feed

    feed_path = tmp_path / "feed.xml"
    feed_path.write_bytes(generate_feed(ADVISORIES))

    recovered = read_published_advisories(str(feed_path))

    assert [a["summary"] for a in recovered] == [
        "SQL injection in query parser",
        "Open redirect",
    ]
    assert [a["severity"] for a in recovered] == ["critical", "low"]
    assert [a["repo"] for a in recovered] == ["owner/repo", "owner/repo"]
    assert [a["cve_id"] for a in recovered] == ["CVE-2026-1234", None]
    assert [a["ghsa_id"] for a in recovered] == ["GHSA-1", "GHSA-2"]


def test_index_only_before_any_feed_exists_shows_the_placeholder(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("feeds:\n  - source: github\n    repos: [owner/repo]\n")
    feed_path = tmp_path / "public" / "feed.xml"

    main(config_path=str(config_file), output_path=str(feed_path), index_only=True)

    html = (feed_path.parent / "index.html").read_text()
    assert "has not been generated yet" in html


def test_index_only_round_trips_dates() -> None:
    """RSS pubDate is RFC 2822, not the API's ISO 8601 — both must parse."""
    from vulnfeed import _published_at

    assert _published_at({"published_at": "Wed, 14 Jun 2023 04:00:00 +0000"}).year == 2023
    assert _published_at({"published_at": "2026-04-01T12:00:00Z"}).year == 2026


def test_index_only_renders_real_dates_from_a_published_feed(tmp_path) -> None:
    from vulnfeed import generate_feed

    config_file = tmp_path / "config.yaml"
    config_file.write_text("feeds:\n  - source: github\n    repos: [owner/repo]\n")
    feed_path = tmp_path / "public" / "feed.xml"
    feed_path.parent.mkdir()
    feed_path.write_bytes(generate_feed(ADVISORIES))

    main(config_path=str(config_file), output_path=str(feed_path), index_only=True)

    html = (feed_path.parent / "index.html").read_text()
    assert "1 Apr 2026" in html
    assert "date unknown" not in html
