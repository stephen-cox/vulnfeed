import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from unittest.mock import Mock, call, patch

import pytest
import requests

import sources
from sources.github import fetch_repo_advisories
from sources.http import PER_PAGE, REQUEST_TIMEOUT
from vulnfeed import (
    DEFAULT_MAX_ITEMS,
    advisory_title,
    aggregate_advisories,
    collect_advisories,
    deduplicate_advisories,
    describe_advisory,
    detail_score,
    feed_limits,
    generate_feed,
    load_config,
    main,
)

ADVISORY_URL = "https://api.github.com/repos/owner/repo/security-advisories"
AUTH_HEADERS = {
    "Accept": "application/vnd.github+json",
    "Authorization": "Bearer fake-token",
}


def make_response(payload, *, next_url=None, status_code=200, headers=None):
    """A stand-in for requests.Response covering only what the fetcher touches."""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.headers = headers or {}
    response.links = {"next": {"url": next_url}} if next_url else {}
    return response


def test_load_config(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - zammad/zammad
      - django/django
"""
    )

    config = load_config(str(config_file))

    assert len(config["feeds"]) == 1
    assert config["feeds"][0]["source"] == "github"
    assert config["feeds"][0]["repos"] == ["zammad/zammad", "django/django"]


def test_fetch_repo_advisories() -> None:
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "ghsa_id": "GHSA-1234-5678-9abc",
            "html_url": "https://github.com/owner/repo/security/advisories/GHSA-1234-5678-9abc",
            "summary": "SQL injection in query parser",
            "severity": "high",
            "published_at": "2026-04-01T12:00:00Z",
            "description": "A SQL injection vulnerability was found.",
        },
        {
            "ghsa_id": "GHSA-aaaa-bbbb-cccc",
            "html_url": "https://github.com/owner/repo/security/advisories/GHSA-aaaa-bbbb-cccc",
            "summary": "XSS in admin panel",
            "severity": "medium",
            "published_at": "2026-03-15T08:00:00Z",
            "description": "A stored XSS vulnerability exists in the admin panel.",
        },
    ]

    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.links = {}

    with patch("sources.http.requests.get", return_value=mock_response) as mock_get:
        advisories = fetch_repo_advisories("owner/repo", token="fake-token")

    mock_get.assert_called_once_with(
        ADVISORY_URL,
        headers=AUTH_HEADERS,
        params={"per_page": PER_PAGE},
        timeout=REQUEST_TIMEOUT,
    )
    mock_response.raise_for_status.assert_called_once_with()
    assert len(advisories) == 2
    assert advisories[0]["ghsa_id"] == "GHSA-1234-5678-9abc"
    assert advisories[1]["severity"] == "medium"


def test_fetch_repo_advisories_follows_pagination() -> None:
    """Every page is fetched and concatenated; the Link URL is used verbatim."""
    page_two_url = f"{ADVISORY_URL}?per_page=100&page=2"
    responses = [
        make_response(
            [{"ghsa_id": "GHSA-page1-a"}, {"ghsa_id": "GHSA-page1-b"}], next_url=page_two_url
        ),
        make_response([{"ghsa_id": "GHSA-page2-a"}]),
    ]

    with patch("sources.http.requests.get", side_effect=responses) as mock_get:
        advisories = fetch_repo_advisories("owner/repo", token="fake-token")

    assert [a["ghsa_id"] for a in advisories] == ["GHSA-page1-a", "GHSA-page1-b", "GHSA-page2-a"]
    assert mock_get.call_args_list == [
        call(
            ADVISORY_URL,
            headers=AUTH_HEADERS,
            params={"per_page": PER_PAGE},
            timeout=REQUEST_TIMEOUT,
        ),
        call(page_two_url, headers=AUTH_HEADERS, params=None, timeout=REQUEST_TIMEOUT),
    ]


def test_fetch_repo_advisories_stops_on_empty_page() -> None:
    """A Link header pointing at an empty page ends pagination rather than looping."""
    responses = [
        make_response([{"ghsa_id": "GHSA-only"}], next_url=f"{ADVISORY_URL}?page=2"),
        make_response([]),
    ]

    with patch("sources.http.requests.get", side_effect=responses) as mock_get:
        advisories = fetch_repo_advisories("owner/repo")

    assert [a["ghsa_id"] for a in advisories] == ["GHSA-only"]
    assert mock_get.call_count == 2


def test_fetch_repo_advisories_caps_pagination() -> None:
    """A Link header that never terminates is bounded by MAX_PAGES."""
    endless = make_response([{"ghsa_id": "GHSA-loop"}], next_url=f"{ADVISORY_URL}?page=next")

    with patch("sources.http.requests.get", return_value=endless) as mock_get:
        with patch("sources.http.MAX_PAGES", 3):
            advisories = fetch_repo_advisories("owner/repo")

    assert mock_get.call_count == 3
    assert len(advisories) == 3


def test_fetch_repo_advisories_omits_auth_header_without_token() -> None:
    with patch("sources.http.requests.get", return_value=make_response([])) as mock_get:
        fetch_repo_advisories("owner/repo")

    assert mock_get.call_args.kwargs["headers"] == {"Accept": "application/vnd.github+json"}


def test_fetch_repo_advisories_retries_transient_status() -> None:
    """A 502 is retried and the eventual success is returned."""
    responses = [
        make_response([], status_code=502),
        make_response([{"ghsa_id": "GHSA-recovered"}]),
    ]

    with patch("sources.http.requests.get", side_effect=responses) as mock_get:
        with patch("sources.http.time.sleep") as mock_sleep:
            advisories = fetch_repo_advisories("owner/repo")

    assert [a["ghsa_id"] for a in advisories] == ["GHSA-recovered"]
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(1.0)
    responses[0].raise_for_status.assert_not_called()


def test_fetch_repo_advisories_honours_retry_after() -> None:
    responses = [
        make_response([], status_code=429, headers={"Retry-After": "7"}),
        make_response([{"ghsa_id": "GHSA-after-wait"}]),
    ]

    with patch("sources.http.requests.get", side_effect=responses):
        with patch("sources.http.time.sleep") as mock_sleep:
            fetch_repo_advisories("owner/repo")

    mock_sleep.assert_called_once_with(7.0)


def test_fetch_repo_advisories_retries_connection_errors() -> None:
    side_effect = [
        requests.ConnectionError("connection reset"),
        make_response([{"ghsa_id": "GHSA-reconnected"}]),
    ]

    with patch("sources.http.requests.get", side_effect=side_effect):
        with patch("sources.http.time.sleep") as mock_sleep:
            advisories = fetch_repo_advisories("owner/repo")

    assert [a["ghsa_id"] for a in advisories] == ["GHSA-reconnected"]
    mock_sleep.assert_called_once_with(1.0)


def test_fetch_repo_advisories_gives_up_after_max_attempts() -> None:
    """Backoff is bounded: a persistently failing repo raises instead of looping."""
    failing = make_response([], status_code=503)
    failing.raise_for_status.side_effect = requests.HTTPError("503 Server Error")

    with patch("sources.http.requests.get", return_value=failing) as mock_get:
        with patch("sources.http.time.sleep") as mock_sleep:
            with pytest.raises(requests.HTTPError):
                fetch_repo_advisories("owner/repo")

    assert mock_get.call_count == 4
    assert [c.args[0] for c in mock_sleep.call_args_list] == [1.0, 2.0, 4.0]


def test_fetch_repo_advisories_does_not_retry_client_errors() -> None:
    """A 404 (renamed or deleted repo) fails immediately rather than backing off."""
    missing = make_response([], status_code=404)
    missing.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

    with patch("sources.http.requests.get", return_value=missing) as mock_get:
        with patch("sources.http.time.sleep") as mock_sleep:
            with pytest.raises(requests.HTTPError):
                fetch_repo_advisories("owner/repo")

    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


def test_aggregate_advisories_deduplicates() -> None:
    advisory_a = {
        "ghsa_id": "GHSA-1111-2222-3333",
        "summary": "Bug A",
        "severity": "high",
        "published_at": "2026-04-01T12:00:00Z",
        "html_url": "https://github.com/owner/repo1/security/advisories/GHSA-1111-2222-3333",
        "description": "Description A",
        "repo": "owner/repo1",
    }
    advisory_b = {
        "ghsa_id": "GHSA-4444-5555-6666",
        "summary": "Bug B",
        "severity": "medium",
        "published_at": "2026-03-15T08:00:00Z",
        "html_url": "https://github.com/owner/repo2/security/advisories/GHSA-4444-5555-6666",
        "description": "Description B",
        "repo": "owner/repo2",
    }
    advisory_a_dup = dict(advisory_a)

    result = aggregate_advisories([advisory_a, advisory_b, advisory_a_dup])

    assert len(result) == 2


def test_aggregate_advisories_sorts_newest_first() -> None:
    older = {
        "ghsa_id": "GHSA-old",
        "summary": "Old",
        "severity": "low",
        "published_at": "2026-01-01T00:00:00Z",
        "html_url": "https://example.com/old",
        "description": "Old one",
        "repo": "owner/repo",
    }
    newer = {
        "ghsa_id": "GHSA-new",
        "summary": "New",
        "severity": "high",
        "published_at": "2026-04-01T00:00:00Z",
        "html_url": "https://example.com/new",
        "description": "New one",
        "repo": "owner/repo",
    }

    result = aggregate_advisories([older, newer])

    assert result[0]["ghsa_id"] == "GHSA-new"
    assert result[1]["ghsa_id"] == "GHSA-old"


def test_generate_feed() -> None:
    advisories = [
        {
            "ghsa_id": "GHSA-1234-5678-9abc",
            "html_url": "https://github.com/owner/repo/security/advisories/GHSA-1234-5678-9abc",
            "summary": "SQL injection in query parser",
            "severity": "high",
            "published_at": "2026-04-01T12:00:00Z",
            "description": "A SQL injection vulnerability was found.",
            "repo": "owner/repo",
        },
    ]

    xml_bytes = generate_feed(advisories, feed_url="https://example.github.io/vulnfeed/feed.xml")

    root = ET.fromstring(xml_bytes)
    channel = root.find("channel")
    assert channel is not None
    assert channel.find("title").text == "VulnFeed — Security Advisories"

    items = channel.findall("item")
    assert len(items) == 1
    assert items[0].find("title").text == "[HIGH] owner/repo — SQL injection in query parser"
    assert (
        items[0].find("link").text
        == "https://github.com/owner/repo/security/advisories/GHSA-1234-5678-9abc"
    )
    assert items[0].find("description").text == "A SQL injection vulnerability was found."
    assert items[0].find("guid").text == "GHSA-1234-5678-9abc"


def test_generate_feed_preserves_order() -> None:
    advisories = [
        {
            "ghsa_id": "GHSA-new",
            "html_url": "https://example.com/new",
            "summary": "Newer",
            "severity": "high",
            "published_at": "2026-04-01T00:00:00Z",
            "description": "Newer one",
            "repo": "owner/repo",
        },
        {
            "ghsa_id": "GHSA-old",
            "html_url": "https://example.com/old",
            "summary": "Older",
            "severity": "low",
            "published_at": "2026-01-01T00:00:00Z",
            "description": "Older one",
            "repo": "owner/repo",
        },
    ]

    xml_bytes = generate_feed(advisories)

    root = ET.fromstring(xml_bytes)
    items = root.find("channel").findall("item")
    assert [item.find("guid").text for item in items] == ["GHSA-new", "GHSA-old"]


def test_main_writes_feed_xml(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    output_file = tmp_path / "output" / "feed.xml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - owner/repo
"""
    )

    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "ghsa_id": "GHSA-zzzz-yyyy-xxxx",
            "html_url": "https://github.com/owner/repo/security/advisories/GHSA-zzzz-yyyy-xxxx",
            "summary": "Privilege escalation in widget parser",
            "severity": "critical",
            "published_at": "2026-04-10T10:00:00Z",
            "description": "A privilege escalation vulnerability was found.",
        }
    ]

    with patch("sources.http.requests.get", return_value=mock_response):
        main(config_path=str(config_file), output_path=str(output_file), token="fake-token")

    assert output_file.exists()
    output_xml = output_file.read_text()
    assert "GHSA-zzzz-yyyy-xxxx" in output_xml
    assert "CRITICAL" in output_xml


CONFIG_TWO_REPOS = {
    "feeds": [{"source": "github", "repos": ["owner/good", "owner/bad"]}],
}


def test_collect_advisories_isolates_a_failing_repo(caplog) -> None:
    """One repo failing must not stop the others being fetched."""

    def fake_fetch(repo, token=None):
        if repo == "owner/bad":
            raise requests.HTTPError("404 Client Error: Not Found for url: ...")
        return [{"ghsa_id": "GHSA-good"}]

    with patch("sources.github.fetch_repo_advisories", side_effect=fake_fetch):
        with caplog.at_level("ERROR"):
            result = collect_advisories(CONFIG_TWO_REPOS)

    assert [a["ghsa_id"] for a in result.advisories] == ["GHSA-good"]
    assert result.advisories[0]["repo"] == "owner/good"
    assert result.succeeded == ["owner/good"]
    assert result.failed == ["owner/bad"]
    assert "owner/bad" in caplog.text
    assert "404" in caplog.text


def test_collect_advisories_isolates_unexpected_errors() -> None:
    """A non-network error is contained too, rather than aborting the run."""

    def fake_fetch(repo, token=None):
        if repo == "owner/bad":
            raise KeyError("ghsa_id")
        return [{"ghsa_id": "GHSA-good"}]

    with patch("sources.github.fetch_repo_advisories", side_effect=fake_fetch):
        result = collect_advisories(CONFIG_TWO_REPOS)

    assert result.succeeded == ["owner/good"]
    assert result.failed == ["owner/bad"]
    assert len(result.advisories) == 1


def test_collect_advisories_skips_unknown_sources(caplog) -> None:
    """An unsupported source must be reported, not silently ignored."""
    config = {"feeds": [{"source": "nvd", "repos": ["ignored"]}]}

    with patch("sources.github.fetch_repo_advisories") as mock_fetch:
        with caplog.at_level("ERROR", logger="vulnfeed"):
            result = collect_advisories(config)

    mock_fetch.assert_not_called()
    assert (result.advisories, result.succeeded, result.failed) == ([], [], [])
    assert "nvd" in caplog.text


def test_main_exits_non_zero_when_every_repo_fails(tmp_path) -> None:
    """A systemic failure must not overwrite the published feed with an empty one."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - owner/one
      - owner/two
"""
    )
    output_file = tmp_path / "output" / "feed.xml"
    output_file.parent.mkdir()
    output_file.write_bytes(b"<rss>previously published</rss>")

    with patch(
        "sources.github.fetch_repo_advisories", side_effect=requests.ConnectionError("down")
    ):
        exit_code = main(config_path=str(config_file), output_path=str(output_file))

    assert exit_code == 1
    assert output_file.read_bytes() == b"<rss>previously published</rss>"


def test_main_exits_zero_when_one_repo_succeeds(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - owner/good
      - owner/bad
"""
    )
    output_file = tmp_path / "output" / "feed.xml"

    def fake_fetch(repo, token=None):
        if repo == "owner/bad":
            raise requests.HTTPError("500 Server Error")
        return [
            {
                "ghsa_id": "GHSA-survivor",
                "html_url": "https://example.com/a",
                "summary": "Still published",
                "severity": "high",
                "published_at": "2026-04-01T12:00:00Z",
                "description": "Body",
            }
        ]

    with patch("sources.github.fetch_repo_advisories", side_effect=fake_fetch):
        exit_code = main(config_path=str(config_file), output_path=str(output_file))

    assert exit_code == 0
    assert b"Still published" in output_file.read_bytes()


def test_main_exits_zero_when_repos_have_no_advisories(tmp_path) -> None:
    """Watching quiet repos is legitimate and must not fail the run."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - owner/quiet
"""
    )
    output_file = tmp_path / "output" / "feed.xml"

    with patch("sources.github.fetch_repo_advisories", return_value=[]):
        exit_code = main(config_path=str(config_file), output_path=str(output_file))

    assert exit_code == 0
    assert output_file.exists()


def test_main_logs_a_run_summary(tmp_path, caplog) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - owner/good
      - owner/bad
"""
    )
    output_file = tmp_path / "output" / "feed.xml"

    def fake_fetch(repo, token=None):
        if repo == "owner/bad":
            raise requests.HTTPError("500 Server Error")
        return []

    with patch("sources.github.fetch_repo_advisories", side_effect=fake_fetch):
        with caplog.at_level("INFO", logger="vulnfeed"):
            main(config_path=str(config_file), output_path=str(output_file))

    assert "0 advisories from 2 repos (1 succeeded, 1 failed)" in caplog.text
    assert "Repos that failed: owner/bad" in caplog.text


def advisory(ghsa_id: str, published_at: str = "2026-04-01T12:00:00Z", **extra) -> dict:
    base = {
        "ghsa_id": ghsa_id,
        "html_url": f"https://example.com/{ghsa_id}",
        "summary": f"Summary for {ghsa_id}",
        "severity": "high",
        "published_at": published_at,
        "description": f"Description for {ghsa_id}",
        "repo": "owner/repo",
    }
    base.update(extra)
    return base


def test_aggregate_advisories_drops_withdrawn() -> None:
    """A retracted advisory used to stay in the feed forever."""
    advisories = [
        advisory("GHSA-live"),
        advisory("GHSA-retracted", withdrawn_at="2026-05-01T00:00:00Z"),
    ]

    result = aggregate_advisories(advisories)

    assert [a["ghsa_id"] for a in result] == ["GHSA-live"]


def test_aggregate_advisories_keeps_null_withdrawn_at() -> None:
    """The API sends withdrawn_at: null on live advisories — that is not withdrawn."""
    result = aggregate_advisories([advisory("GHSA-live", withdrawn_at=None)])

    assert [a["ghsa_id"] for a in result] == ["GHSA-live"]


def test_aggregate_advisories_applies_max_items_after_sorting() -> None:
    """The cap keeps the newest, not the first seen."""
    advisories = [
        advisory("GHSA-old", "2020-01-01T00:00:00Z"),
        advisory("GHSA-newest", "2026-08-01T00:00:00Z"),
        advisory("GHSA-middle", "2024-01-01T00:00:00Z"),
    ]

    result = aggregate_advisories(advisories, max_items=2)

    assert [a["ghsa_id"] for a in result] == ["GHSA-newest", "GHSA-middle"]


def test_aggregate_advisories_max_items_none_keeps_everything() -> None:
    advisories = [advisory(f"GHSA-{i}") for i in range(150)]

    assert len(aggregate_advisories(advisories, max_items=None)) == 150


def test_aggregate_advisories_applies_max_age_days() -> None:
    now = datetime(2026, 8, 22, tzinfo=UTC)
    advisories = [
        advisory("GHSA-recent", "2026-08-01T00:00:00Z"),
        advisory("GHSA-ancient", "2019-12-20T23:12:22Z"),
    ]

    result = aggregate_advisories(advisories, max_age_days=365, now=now)

    assert [a["ghsa_id"] for a in result] == ["GHSA-recent"]


def test_aggregate_advisories_handles_null_published_at() -> None:
    """A null published_at used to raise TypeError and take down the whole run."""
    advisories = [
        advisory("GHSA-dated", "2026-04-01T12:00:00Z"),
        advisory("GHSA-undated", published_at=None),
    ]

    result = aggregate_advisories(advisories)

    assert [a["ghsa_id"] for a in result] == ["GHSA-dated", "GHSA-undated"]


def test_aggregate_advisories_handles_unparseable_published_at(caplog) -> None:
    advisories = [advisory("GHSA-dated"), advisory("GHSA-garbled", published_at="not a date")]

    with caplog.at_level("WARNING", logger="vulnfeed"):
        result = aggregate_advisories(advisories)

    assert [a["ghsa_id"] for a in result] == ["GHSA-dated", "GHSA-garbled"]
    assert "GHSA-garbled" in caplog.text


def test_aggregate_advisories_missing_published_at_does_not_break_max_age() -> None:
    now = datetime(2026, 8, 22, tzinfo=UTC)
    advisories = [advisory("GHSA-recent", "2026-08-01T00:00:00Z"), advisory("GHSA-undated", None)]

    result = aggregate_advisories(advisories, max_age_days=30, now=now)

    assert [a["ghsa_id"] for a in result] == ["GHSA-recent"]


def test_feed_limits_defaults_when_section_absent() -> None:
    """An unmodified fork config must keep working."""
    assert feed_limits({"feeds": []}) == (DEFAULT_MAX_ITEMS, None)


def test_feed_limits_reads_configured_values() -> None:
    config = {"feed": {"max_items": 25, "max_age_days": 90}}

    assert feed_limits(config) == (25, 90)


def test_feed_limits_allows_disabling_the_cap() -> None:
    assert feed_limits({"feed": {"max_items": None}}) == (None, None)


def test_main_applies_configured_feed_limits(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feed:
  max_items: 2

feeds:
  - source: github
    repos:
      - owner/repo
"""
    )
    output_file = tmp_path / "output" / "feed.xml"
    fetched = [
        advisory("GHSA-a", "2026-08-01T00:00:00Z"),
        advisory("GHSA-b", "2026-07-01T00:00:00Z"),
        advisory("GHSA-c", "2026-06-01T00:00:00Z"),
    ]

    with patch("sources.github.fetch_repo_advisories", return_value=fetched):
        main(config_path=str(config_file), output_path=str(output_file))

    root = ET.fromstring(output_file.read_bytes())
    guids = [item.find("guid").text for item in root.find("channel").findall("item")]
    assert guids == ["GHSA-a", "GHSA-b"]


FULL_ADVISORY = {
    "ghsa_id": "GHSA-full-0000-0000",
    "html_url": "https://github.com/owner/repo/security/advisories/GHSA-full-0000-0000",
    "summary": "SQL injection in ticket search",
    "severity": "critical",
    "published_at": "2026-04-01T12:00:00Z",
    "description": "## Summary\nA SQL injection vulnerability.",
    "repo": "owner/repo",
    "cve_id": "CVE-2026-1234",
    "cvss": {"score": 9.8, "vector_string": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"},
    "cwes": [{"cwe_id": "CWE-89", "name": "SQL Injection"}, {"cwe_id": "CWE-20", "name": "Input"}],
    "vulnerabilities": [
        {
            "package": {"ecosystem": "rubygems", "name": "zammad"},
            "vulnerable_version_range": "< 6.4.1",
            "patched_versions": "6.4.1",
        }
    ],
}

MINIMAL_ADVISORY = {
    "ghsa_id": "GHSA-min-0000-0000",
    "html_url": "https://example.com/min",
    "summary": "Bare advisory",
    "severity": None,
    "published_at": "2026-03-01T00:00:00Z",
    "description": "Body only.",
    "repo": "owner/repo",
    "cve_id": None,
    "cvss": {"score": None, "vector_string": None},
    "cwes": [],
    "vulnerabilities": [],
}


def test_describe_advisory_includes_all_metadata() -> None:
    described = describe_advisory(FULL_ADVISORY)

    assert "CVE-2026-1234" in described
    assert "CVSS 9.8 (CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)" in described
    assert "CWE-89, CWE-20" in described
    assert "- rubygems/zammad < 6.4.1 (patched: 6.4.1)" in described
    assert described.endswith("## Summary\nA SQL injection vulnerability.")


def test_describe_advisory_omits_absent_metadata() -> None:
    """Every enriched field is optional; absent ones must not leave empty lines."""
    described = describe_advisory(MINIMAL_ADVISORY)

    assert described == "Body only."


def test_describe_advisory_survives_missing_keys_entirely() -> None:
    described = describe_advisory({"summary": "No body", "ghsa_id": "GHSA-x"})

    assert described == "No body"


def test_describe_advisory_reads_cvss_severities_fallback() -> None:
    advisory_with_v4 = {
        **MINIMAL_ADVISORY,
        "cvss_severities": {"cvss_v4": {"score": 8.7, "vector_string": "CVSS:4.0/AV:N"}},
    }

    assert "CVSS 8.7 (CVSS:4.0/AV:N)" in describe_advisory(advisory_with_v4)


def test_describe_advisory_handles_score_without_vector() -> None:
    assert "CVSS 7.5" in describe_advisory({**MINIMAL_ADVISORY, "cvss": {"score": 7.5}})


def test_describe_advisory_handles_first_patched_version_object() -> None:
    """The global advisory database nests the patched version in an object."""
    advisory_ghsa_shape = {
        **MINIMAL_ADVISORY,
        "vulnerabilities": [
            {
                "package": {"ecosystem": "npm", "name": "widget"},
                "vulnerable_version_range": ">= 2.0, < 2.1.4",
                "first_patched_version": {"identifier": "2.1.4"},
            }
        ],
    }

    assert "- npm/widget >= 2.0, < 2.1.4 (patched: 2.1.4)" in describe_advisory(advisory_ghsa_shape)


def test_describe_advisory_skips_packages_without_a_name() -> None:
    advisory_no_name = {**MINIMAL_ADVISORY, "vulnerabilities": [{"package": {"ecosystem": "npm"}}]}

    assert describe_advisory(advisory_no_name) == "Body only."


def test_advisory_title_appends_cve_when_present() -> None:
    assert advisory_title(FULL_ADVISORY) == (
        "[CRITICAL] owner/repo — SQL injection in ticket search (CVE-2026-1234)"
    )


def test_advisory_title_without_cve_is_unchanged() -> None:
    assert advisory_title(MINIMAL_ADVISORY) == "[UNKNOWN] owner/repo — Bare advisory"


def test_generate_feed_adds_severity_and_repo_categories() -> None:
    root = ET.fromstring(generate_feed([FULL_ADVISORY]))
    item = root.find("channel").find("item")

    assert [c.text for c in item.findall("category")] == ["CRITICAL", "owner/repo"]


def test_generate_feed_with_minimal_advisory_is_valid_rss() -> None:
    root = ET.fromstring(generate_feed([MINIMAL_ADVISORY]))

    assert root.tag == "rss"
    assert root.get("version") == "2.0"
    item = root.find("channel").find("item")
    assert item.find("description").text == "Body only."
    assert item.find("guid").text == "GHSA-min-0000-0000"


def test_main_dry_run_writes_nothing(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
feeds:
  - source: github
    repos:
      - owner/repo
"""
    )
    output_file = tmp_path / "output" / "feed.xml"

    with patch("sources.github.fetch_repo_advisories", return_value=[advisory("GHSA-a")]):
        exit_code = main(config_path=str(config_file), output_path=str(output_file), dry_run=True)

    assert exit_code == 0
    assert not output_file.exists()
    assert not output_file.parent.exists()


def test_main_dry_run_reports_the_count(tmp_path, caplog) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("feeds:\n  - source: github\n    repos: [owner/repo]\n")
    fetched = [advisory("GHSA-a"), advisory("GHSA-b")]

    with patch("sources.github.fetch_repo_advisories", return_value=fetched):
        with caplog.at_level("INFO", logger="vulnfeed"):
            main(
                config_path=str(config_file),
                output_path=str(tmp_path / "out" / "feed.xml"),
                dry_run=True,
            )

    assert "Dry run: would write 2 advisories" in caplog.text


def test_main_honours_custom_output_path(tmp_path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text("feeds:\n  - source: github\n    repos: [owner/repo]\n")
    output_file = tmp_path / "custom" / "somewhere" / "rss.xml"

    with patch("sources.github.fetch_repo_advisories", return_value=[advisory("GHSA-a")]):
        main(config_path=str(config_file), output_path=str(output_file))

    assert output_file.exists()
    assert (output_file.parent / "index.html").exists()


def test_source_result_merge_combines_targets() -> None:
    first = sources.SourceResult(advisories=[{"ghsa_id": "A"}], succeeded=["one"], failed=[])
    second = sources.SourceResult(advisories=[{"ghsa_id": "B"}], succeeded=[], failed=["two"])

    first.merge(second)

    assert [a["ghsa_id"] for a in first.advisories] == ["A", "B"]
    assert first.succeeded == ["one"]
    assert first.failed == ["two"]


def test_get_source_resolves_github_and_rejects_unknown() -> None:
    assert sources.get_source("github") is not None
    assert sources.get_source("nvd") is None
    assert sources.get_source(None) is None


REPO_RECORD = {
    "ghsa_id": "GHSA-from-repo",
    "html_url": "https://github.com/owner/repo/security/advisories/GHSA-from-repo",
    "summary": "RCE in widget",
    "description": "Short body.",
    "severity": "critical",
    "published_at": "2026-05-01T00:00:00Z",
    "repo": "owner/repo",
    "cve_id": "CVE-2026-9999",
}

GLOBAL_RECORD = {
    "ghsa_id": "GHSA-from-database",
    "html_url": "https://github.com/advisories/GHSA-from-database",
    "summary": "RCE in widget",
    "description": "Fuller body.",
    "severity": "critical",
    "published_at": "2026-05-01T00:00:00Z",
    "repo": "composer/vendor/widget",
    "cve_id": "CVE-2026-9999",
    "cvss": {"score": 9.9, "vector_string": "CVSS:3.1/AV:N"},
    "cwes": [{"cwe_id": "CWE-94", "name": "Code Injection"}],
    "vulnerabilities": [
        {
            "package": {"ecosystem": "composer", "name": "vendor/widget"},
            "vulnerable_version_range": "< 3.0.1",
            "first_patched_version": "3.0.1",
        }
    ],
}


def test_detail_score_ranks_the_richer_record_higher() -> None:
    assert detail_score(GLOBAL_RECORD) > detail_score(REPO_RECORD)


def test_deduplicate_collapses_the_same_cve_from_two_sources() -> None:
    """One vulnerability, two GHSA IDs — the old GHSA-only dedup published both."""
    result = deduplicate_advisories([REPO_RECORD, GLOBAL_RECORD])

    assert len(result) == 1
    assert result[0]["ghsa_id"] == "GHSA-from-database"


def test_deduplicate_prefers_the_richer_record_regardless_of_order() -> None:
    assert deduplicate_advisories([GLOBAL_RECORD, REPO_RECORD])[0]["ghsa_id"] == (
        "GHSA-from-database"
    )
    assert deduplicate_advisories([REPO_RECORD, GLOBAL_RECORD])[0]["ghsa_id"] == (
        "GHSA-from-database"
    )


def test_deduplicate_keeps_distinct_cves() -> None:
    other = {**GLOBAL_RECORD, "ghsa_id": "GHSA-other", "cve_id": "CVE-2026-1111"}

    result = deduplicate_advisories([REPO_RECORD, other])

    assert {a["ghsa_id"] for a in result} == {"GHSA-from-repo", "GHSA-other"}


def test_deduplicate_keeps_advisories_without_a_cve() -> None:
    """A null cve_id must not collapse every uncredited advisory into one."""
    first = {**REPO_RECORD, "ghsa_id": "GHSA-a", "cve_id": None}
    second = {**REPO_RECORD, "ghsa_id": "GHSA-b", "cve_id": None}

    result = deduplicate_advisories([first, second])

    assert {a["ghsa_id"] for a in result} == {"GHSA-a", "GHSA-b"}


def test_deduplicate_collapses_repeated_ghsa_ids() -> None:
    result = deduplicate_advisories([REPO_RECORD, dict(REPO_RECORD)])

    assert len(result) == 1


def test_aggregate_deduplicates_across_sources_end_to_end() -> None:
    result = aggregate_advisories([REPO_RECORD, GLOBAL_RECORD])

    assert [a["ghsa_id"] for a in result] == ["GHSA-from-database"]


def test_aggregate_drops_a_withdrawn_duplicate_before_dedup() -> None:
    """A withdrawn richer record must not win the CVE and then vanish."""
    withdrawn_global = {**GLOBAL_RECORD, "withdrawn_at": "2026-06-01T00:00:00Z"}

    result = aggregate_advisories([REPO_RECORD, withdrawn_global])

    assert [a["ghsa_id"] for a in result] == ["GHSA-from-repo"]


def test_collect_advisories_merges_both_sources() -> None:
    config = {
        "feeds": [
            {"source": "github", "repos": ["owner/repo"]},
            {"source": "ghsa", "packages": [{"ecosystem": "composer", "name": "vendor/widget"}]},
        ]
    }

    with patch("sources.github.fetch_repo_advisories", return_value=[dict(REPO_RECORD)]):
        with patch("sources.ghsa.fetch_package_advisories", return_value=[dict(GLOBAL_RECORD)]):
            result = collect_advisories(config)

    assert result.succeeded == ["owner/repo", "composer/vendor/widget"]
    assert len(result.advisories) == 2
