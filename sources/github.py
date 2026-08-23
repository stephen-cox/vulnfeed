"""Advisories filed in a repository's own GitHub security tab.

Note the limit of this source: it returns only advisories authored in the
repository itself. Advisories published against the project's packages by third
parties live in the global advisory database and need a different source.
"""

import logging

from sources import SourceResult
from sources.http import PER_PAGE, paginate

log = logging.getLogger("vulnfeed")

GITHUB_API_ROOT = "https://api.github.com"


def _headers(token: str | None) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_repo_advisories(repo: str, token: str | None = None) -> list[dict]:
    """Fetch every security advisory published in one repository's security tab."""
    return paginate(
        f"{GITHUB_API_ROOT}/repos/{repo}/security-advisories",
        headers=_headers(token),
        params={"per_page": PER_PAGE},
        context=repo,
    )


def fetch_advisories(feed_config: dict, token: str | None = None) -> SourceResult:
    """Fetch every repo in one `source: github` config entry.

    Failures are isolated per repo: a renamed, deleted, private, or transiently
    unavailable repo is recorded and skipped so the others still publish.
    """
    result = SourceResult()

    for repo in feed_config.get("repos", []):
        try:
            advisories = fetch_repo_advisories(repo, token=token)
        except Exception as exc:
            result.record_failure(repo, exc)
            continue

        for advisory in advisories:
            advisory["repo"] = repo
        result.record_success(repo, advisories)

    return result
