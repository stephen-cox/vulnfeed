import xml.etree.ElementTree as ET
from unittest.mock import Mock, call, patch

import pytest
import requests

from vulnfeed import (
    PER_PAGE,
    REQUEST_TIMEOUT,
    aggregate_advisories,
    fetch_github_advisories,
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


def test_fetch_github_advisories() -> None:
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

    with patch("vulnfeed.requests.get", return_value=mock_response) as mock_get:
        advisories = fetch_github_advisories("owner/repo", token="fake-token")

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


def test_fetch_github_advisories_follows_pagination() -> None:
    """Every page is fetched and concatenated; the Link URL is used verbatim."""
    page_two_url = f"{ADVISORY_URL}?per_page=100&page=2"
    responses = [
        make_response(
            [{"ghsa_id": "GHSA-page1-a"}, {"ghsa_id": "GHSA-page1-b"}], next_url=page_two_url
        ),
        make_response([{"ghsa_id": "GHSA-page2-a"}]),
    ]

    with patch("vulnfeed.requests.get", side_effect=responses) as mock_get:
        advisories = fetch_github_advisories("owner/repo", token="fake-token")

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


def test_fetch_github_advisories_stops_on_empty_page() -> None:
    """A Link header pointing at an empty page ends pagination rather than looping."""
    responses = [
        make_response([{"ghsa_id": "GHSA-only"}], next_url=f"{ADVISORY_URL}?page=2"),
        make_response([]),
    ]

    with patch("vulnfeed.requests.get", side_effect=responses) as mock_get:
        advisories = fetch_github_advisories("owner/repo")

    assert [a["ghsa_id"] for a in advisories] == ["GHSA-only"]
    assert mock_get.call_count == 2


def test_fetch_github_advisories_caps_pagination() -> None:
    """A Link header that never terminates is bounded by MAX_PAGES."""
    endless = make_response([{"ghsa_id": "GHSA-loop"}], next_url=f"{ADVISORY_URL}?page=next")

    with patch("vulnfeed.requests.get", return_value=endless) as mock_get:
        with patch("vulnfeed.MAX_PAGES", 3):
            advisories = fetch_github_advisories("owner/repo")

    assert mock_get.call_count == 3
    assert len(advisories) == 3


def test_fetch_github_advisories_omits_auth_header_without_token() -> None:
    with patch("vulnfeed.requests.get", return_value=make_response([])) as mock_get:
        fetch_github_advisories("owner/repo")

    assert mock_get.call_args.kwargs["headers"] == {"Accept": "application/vnd.github+json"}


def test_fetch_github_advisories_retries_transient_status() -> None:
    """A 502 is retried and the eventual success is returned."""
    responses = [
        make_response([], status_code=502),
        make_response([{"ghsa_id": "GHSA-recovered"}]),
    ]

    with patch("vulnfeed.requests.get", side_effect=responses) as mock_get:
        with patch("vulnfeed.time.sleep") as mock_sleep:
            advisories = fetch_github_advisories("owner/repo")

    assert [a["ghsa_id"] for a in advisories] == ["GHSA-recovered"]
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(1.0)
    responses[0].raise_for_status.assert_not_called()


def test_fetch_github_advisories_honours_retry_after() -> None:
    responses = [
        make_response([], status_code=429, headers={"Retry-After": "7"}),
        make_response([{"ghsa_id": "GHSA-after-wait"}]),
    ]

    with patch("vulnfeed.requests.get", side_effect=responses):
        with patch("vulnfeed.time.sleep") as mock_sleep:
            fetch_github_advisories("owner/repo")

    mock_sleep.assert_called_once_with(7.0)


def test_fetch_github_advisories_retries_connection_errors() -> None:
    side_effect = [
        requests.ConnectionError("connection reset"),
        make_response([{"ghsa_id": "GHSA-reconnected"}]),
    ]

    with patch("vulnfeed.requests.get", side_effect=side_effect):
        with patch("vulnfeed.time.sleep") as mock_sleep:
            advisories = fetch_github_advisories("owner/repo")

    assert [a["ghsa_id"] for a in advisories] == ["GHSA-reconnected"]
    mock_sleep.assert_called_once_with(1.0)


def test_fetch_github_advisories_gives_up_after_max_attempts() -> None:
    """Backoff is bounded: a persistently failing repo raises instead of looping."""
    failing = make_response([], status_code=503)
    failing.raise_for_status.side_effect = requests.HTTPError("503 Server Error")

    with patch("vulnfeed.requests.get", return_value=failing) as mock_get:
        with patch("vulnfeed.time.sleep") as mock_sleep:
            with pytest.raises(requests.HTTPError):
                fetch_github_advisories("owner/repo")

    assert mock_get.call_count == 4
    assert [c.args[0] for c in mock_sleep.call_args_list] == [1.0, 2.0, 4.0]


def test_fetch_github_advisories_does_not_retry_client_errors() -> None:
    """A 404 (renamed or deleted repo) fails immediately rather than backing off."""
    missing = make_response([], status_code=404)
    missing.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

    with patch("vulnfeed.requests.get", return_value=missing) as mock_get:
        with patch("vulnfeed.time.sleep") as mock_sleep:
            with pytest.raises(requests.HTTPError):
                fetch_github_advisories("owner/repo")

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

    with patch("vulnfeed.requests.get", return_value=mock_response):
        main(config_path=str(config_file), output_path=str(output_file), token="fake-token")

    assert output_file.exists()
    output_xml = output_file.read_text()
    assert "GHSA-zzzz-yyyy-xxxx" in output_xml
    assert "CRITICAL" in output_xml
