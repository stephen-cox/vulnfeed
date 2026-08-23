"""Tests for the global GitHub Advisory Database source."""

from unittest.mock import patch

import pytest
import requests

from sources import ghsa
from sources.http import PER_PAGE

GLOBAL_ADVISORY = {
    "ghsa_id": "GHSA-glob-0000-0000",
    "cve_id": "CVE-2026-9999",
    "url": "https://api.github.com/advisories/GHSA-glob-0000-0000",
    "html_url": "https://github.com/advisories/GHSA-glob-0000-0000",
    "summary": "Remote code execution in widget",
    "description": "Full body.",
    "severity": "critical",
    "published_at": "2026-05-01T00:00:00Z",
    "withdrawn_at": None,
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


def make_response(payload):
    from unittest.mock import Mock

    response = Mock()
    response.status_code = 200
    response.json.return_value = payload
    response.headers = {}
    response.links = {}
    return response


def test_package_label_combines_ecosystem_and_name() -> None:
    assert ghsa.package_label({"ecosystem": "composer", "name": "a/b"}) == "composer:a/b"
    assert ghsa.package_label({"name": "bare"}) == "bare"


def test_fetch_package_advisories_sends_affects_and_ecosystem() -> None:
    with patch("sources.http.requests.get", return_value=make_response([])) as mock_get:
        ghsa.fetch_package_advisories({"ecosystem": "pip", "name": "open-webui"})

    assert mock_get.call_args.args[0] == "https://api.github.com/advisories"
    assert mock_get.call_args.kwargs["params"] == {
        "affects": "open-webui",
        "per_page": PER_PAGE,
        "ecosystem": "pip",
    }


def test_fetch_package_advisories_omits_ecosystem_when_absent() -> None:
    with patch("sources.http.requests.get", return_value=make_response([])) as mock_get:
        ghsa.fetch_package_advisories({"name": "solo"})

    assert "ecosystem" not in mock_get.call_args.kwargs["params"]


def test_normalise_sets_the_package_as_the_origin_label() -> None:
    normalised = ghsa.normalise(GLOBAL_ADVISORY, "composer:vendor/widget")

    assert normalised["repo"] == "composer:vendor/widget"
    assert normalised["ghsa_id"] == GLOBAL_ADVISORY["ghsa_id"]
    assert normalised["html_url"] == GLOBAL_ADVISORY["html_url"]
    # The source payload must not be mutated in place.
    assert "repo" not in GLOBAL_ADVISORY


def test_normalise_falls_back_to_the_api_url() -> None:
    without_html_url = {k: v for k, v in GLOBAL_ADVISORY.items() if k != "html_url"}

    normalised = ghsa.normalise(without_html_url, "composer/x")

    assert normalised["html_url"] == GLOBAL_ADVISORY["url"]


def test_fetch_advisories_normalises_every_package() -> None:
    config = {
        "packages": [
            {"ecosystem": "composer", "name": "vendor/widget"},
            {"ecosystem": "pip", "name": "gadget"},
        ]
    }

    with patch(
        "sources.ghsa.fetch_package_advisories", return_value=[dict(GLOBAL_ADVISORY)]
    ) as mock_fetch:
        result = ghsa.fetch_advisories(config, token="fake-token")

    assert mock_fetch.call_count == 2
    assert result.succeeded == ["composer:vendor/widget", "pip:gadget"]
    assert result.failed == []
    assert [a["repo"] for a in result.advisories] == ["composer:vendor/widget", "pip:gadget"]


def test_fetch_advisories_isolates_a_failing_package() -> None:
    config = {"packages": [{"name": "good"}, {"name": "bad"}]}

    def fake(package, token=None):
        if package["name"] == "bad":
            raise requests.HTTPError("500 Server Error")
        return [dict(GLOBAL_ADVISORY)]

    with patch("sources.ghsa.fetch_package_advisories", side_effect=fake):
        result = ghsa.fetch_advisories(config)

    assert result.succeeded == ["good"]
    assert result.failed == ["bad"]
    assert len(result.advisories) == 1


def test_fetch_advisories_warns_when_a_package_matches_nothing(caplog) -> None:
    """A misspelled package returns an empty list, not a 404 — make that visible."""
    config = {"packages": [{"ecosystem": "pip", "name": "no-such-packge"}]}

    with patch("sources.ghsa.fetch_package_advisories", return_value=[]):
        with caplog.at_level("WARNING", logger="vulnfeed"):
            result = ghsa.fetch_advisories(config)

    assert result.succeeded == ["pip:no-such-packge"]
    assert "check the package name" in caplog.text
    assert "pip:no-such-packge" in caplog.text


def test_fetch_advisories_skips_entries_without_a_name(caplog) -> None:
    config = {"packages": [{"ecosystem": "pip"}]}

    with patch("sources.ghsa.fetch_package_advisories") as mock_fetch:
        with caplog.at_level("ERROR", logger="vulnfeed"):
            result = ghsa.fetch_advisories(config)

    mock_fetch.assert_not_called()
    assert result.succeeded == []
    assert "no name" in caplog.text


def test_fetch_advisories_with_no_packages_is_a_noop() -> None:
    result = ghsa.fetch_advisories({})

    assert (result.advisories, result.succeeded, result.failed) == ([], [], [])


@pytest.mark.parametrize("ecosystem", ["npm", "pip", "composer", "rubygems", "go", "maven"])
def test_fetch_package_advisories_passes_ecosystem_through(ecosystem) -> None:
    with patch("sources.http.requests.get", return_value=make_response([])) as mock_get:
        ghsa.fetch_package_advisories({"ecosystem": ecosystem, "name": "pkg"})

    assert mock_get.call_args.kwargs["params"]["ecosystem"] == ecosystem
