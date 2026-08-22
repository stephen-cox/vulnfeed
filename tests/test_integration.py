"""End-to-end checks against a local HTTP server.

The unit tests mock `requests.get`, which stubs out the one thing pagination
actually depends on: requests' own parsing of the `Link` header into
`response.links`. These tests serve real HTTP with real Link headers so that
parsing is exercised for real.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pytest

import vulnfeed

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
    monkeypatch.setattr(vulnfeed, "GITHUB_API_ROOT", f"http://{host}:{port}")
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_pagination_against_real_http_server(advisory_api) -> None:
    """All pages are retrieved via real Link headers, well past the old 30 cap."""
    advisories = vulnfeed.fetch_github_advisories("owner/repo")

    assert len(advisories) == TOTAL_ADVISORIES
    assert advisories[0]["ghsa_id"] == "GHSA-0000"
    assert advisories[-1]["ghsa_id"] == f"GHSA-{TOTAL_ADVISORIES - 1:04d}"
    assert len({a["ghsa_id"] for a in advisories}) == TOTAL_ADVISORIES

    pages = [page for _, _, page in advisory_api.requests]
    per_pages = {per_page for _, per_page, _ in advisory_api.requests}
    assert pages == [1, 2, 3]
    assert per_pages == {vulnfeed.PER_PAGE}


def test_single_request_would_have_truncated(advisory_api) -> None:
    """Documents the bug: one default-paged request returns only 30 of 250."""
    import requests

    url = f"{vulnfeed.GITHUB_API_ROOT}/repos/owner/repo/security-advisories"
    response = requests.get(url, timeout=(5, 30))

    assert len(response.json()) == 30
    assert response.links["next"]["url"]
