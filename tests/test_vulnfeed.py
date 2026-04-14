import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch

from vulnfeed import aggregate_advisories, fetch_github_advisories, generate_feed, load_config


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

    with patch("vulnfeed.requests.get", return_value=mock_response) as mock_get:
        advisories = fetch_github_advisories("owner/repo", token="fake-token")

    mock_get.assert_called_once_with(
        "https://api.github.com/repos/owner/repo/security-advisories",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer fake-token",
        },
    )
    mock_response.raise_for_status.assert_called_once_with()
    assert len(advisories) == 2
    assert advisories[0]["ghsa_id"] == "GHSA-1234-5678-9abc"
    assert advisories[1]["severity"] == "medium"


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
