"""End-to-end checks against a local HTTP server.

The unit tests mock `requests.get`, which stubs out the one thing pagination
actually depends on: requests' own parsing of the `Link` header into
`response.links`. These tests serve real HTTP with real Link headers so that
parsing is exercised for real.
"""

import json
import threading
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

import sources.ghsa
import sources.github
import vulnfeed
from sources.http import PER_PAGE

TOTAL_ADVISORIES = 250


def make_advisory(index: int) -> dict:
    return {
        "ghsa_id": f"GHSA-{index:04d}",
        "html_url": f"https://example.test/advisories/GHSA-{index:04d}",
        "summary": f"Advisory {index}",
        "severity": "high",
        "published_at": "2026-04-01T12:00:00Z",
        "description": f"Description for advisory {index}.",
    }


class AdvisoryHandler(BaseHTTPRequestHandler):
    """Emulates GET /repos/{owner}/{repo}/security-advisories with Link paging."""

    def do_GET(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        per_page = int(query.get("per_page", ["30"])[0])
        page = int(query.get("page", ["1"])[0])

        self.server.requests.append((parsed.path, per_page, page))

        start = (page - 1) * per_page
        body = [make_advisory(i) for i in range(start, min(start + per_page, TOTAL_ADVISORIES))]
        payload = json.dumps(body).encode()

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        if start + per_page < TOTAL_ADVISORIES:
            next_url = (
                f"http://{self.headers['Host']}{parsed.path}?per_page={per_page}&page={page + 1}"
            )
            self.send_header("Link", f'<{next_url}>; rel="next"')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args) -> None:
        """Silence per-request logging to stderr."""


@pytest.fixture
def advisory_api(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), AdvisoryHandler)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    monkeypatch.setattr(sources.github, "GITHUB_API_ROOT", f"http://{host}:{port}")
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_pagination_against_real_http_server(advisory_api) -> None:
    """All pages are retrieved via real Link headers, well past the old 30 cap."""
    advisories = sources.github.fetch_repo_advisories("owner/repo")

    assert len(advisories) == TOTAL_ADVISORIES
    assert advisories[0]["ghsa_id"] == "GHSA-0000"
    assert advisories[-1]["ghsa_id"] == f"GHSA-{TOTAL_ADVISORIES - 1:04d}"
    assert len({a["ghsa_id"] for a in advisories}) == TOTAL_ADVISORIES

    pages = [page for _, _, page in advisory_api.requests]
    per_pages = {per_page for _, per_page, _ in advisory_api.requests}
    assert pages == [1, 2, 3]
    assert per_pages == {PER_PAGE}


def test_single_request_would_have_truncated(advisory_api) -> None:
    """Documents the bug: one default-paged request returns only 30 of 250."""
    import requests

    url = f"{sources.github.GITHUB_API_ROOT}/repos/owner/repo/security-advisories"
    response = requests.get(url, timeout=(5, 30))

    assert len(response.json()) == 30
    assert response.links["next"]["url"]


class BothSourcesHandler(BaseHTTPRequestHandler):
    """Serves the repository endpoint and the global advisory database.

    The repository has one advisory in its security tab. The package the project
    publishes has that one plus a second, filed by a third party — the coverage
    the repository endpoint cannot see.
    """

    REPO_ONLY = {
        "ghsa_id": "GHSA-in-repo-tab",
        "html_url": "https://github.test/repo-advisory",
        "summary": "Filed by the project",
        "description": "In the security tab.",
        "severity": "high",
        "published_at": "2026-05-01T00:00:00Z",
        "cve_id": "CVE-2026-0001",
    }
    THIRD_PARTY_ONLY = {
        "ghsa_id": "GHSA-third-party",
        "html_url": "https://github.test/database-advisory",
        "summary": "Filed by a third party",
        "description": "Only in the global database.",
        "severity": "critical",
        "published_at": "2026-06-01T00:00:00Z",
        "cve_id": "CVE-2026-0002",
    }

    def do_GET(self) -> None:  # noqa: N802 - name fixed by BaseHTTPRequestHandler
        path = urlparse(self.path).path
        if path.endswith("/security-advisories"):
            body = [self.REPO_ONLY]
        else:
            body = [self.REPO_ONLY, self.THIRD_PARTY_ONLY]

        payload = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args) -> None:
        """Silence per-request logging to stderr."""


@pytest.fixture
def both_sources_api(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), BothSourcesHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address
    root = f"http://{host}:{port}"
    monkeypatch.setattr(sources.github, "GITHUB_API_ROOT", root)
    monkeypatch.setattr(sources.ghsa, "GITHUB_API_ROOT", root)
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


GITHUB_ONLY_CONFIG = """
feeds:
  - source: github
    repos:
      - owner/repo
"""

BOTH_SOURCES_CONFIG = """
feeds:
  - source: github
    repos:
      - owner/repo

  - source: ghsa
    packages:
      - ecosystem: composer
        name: vendor/widget
"""


def guids(feed_path):
    root = ET.fromstring(feed_path.read_bytes())
    return [item.find("guid").text for item in root.find("channel").findall("item")]


def run_with_config(tmp_path, config_text, name):
    config_file = tmp_path / f"{name}.yaml"
    config_file.write_text(config_text)
    output = tmp_path / name / "feed.xml"
    vulnfeed.main(config_path=str(config_file), output_path=str(output))
    return output


def test_ghsa_source_surfaces_advisories_the_repo_source_misses(both_sources_api, tmp_path) -> None:
    """Before/after coverage: adding the package source finds a third-party advisory."""
    before = run_with_config(tmp_path, GITHUB_ONLY_CONFIG, "before")
    after = run_with_config(tmp_path, BOTH_SOURCES_CONFIG, "after")

    assert guids(before) == ["GHSA-in-repo-tab"]
    assert set(guids(after)) == {"GHSA-in-repo-tab", "GHSA-third-party"}
    assert len(guids(after)) > len(guids(before))


def test_advisory_in_both_sources_is_published_once(both_sources_api, tmp_path) -> None:
    """CVE-2026-0001 is returned by both endpoints and must not appear twice."""
    after = run_with_config(tmp_path, BOTH_SOURCES_CONFIG, "dedup")

    published = guids(after)
    assert len(published) == len(set(published))
    assert published.count("GHSA-in-repo-tab") == 1
