from unittest.mock import Mock, patch

from vulnfeed import fetch_github_advisories, load_config


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
