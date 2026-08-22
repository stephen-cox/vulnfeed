"""Advisories from the global GitHub Advisory Database, matched by package.

This is the coverage gap `sources.github` cannot close. The repository endpoint
returns only advisories authored in a project's own security tab; anything filed
against the project's *published packages* by a third-party reporter, an
ecosystem maintainer, or a CVE assigner lives in the global database instead and
is invisible to that source.

Uses the REST endpoint rather than the GraphQL `securityAdvisories` connection:
GET /advisories accepts `ecosystem` and `affects` filters directly, paginates
with the same Link headers as every other endpoint here, and therefore reuses
`sources.http.paginate` unchanged. GraphQL would need a separate client and
cursor-based paging for no additional filtering power.
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


def package_label(package: dict) -> str:
    """The origin label shown in the feed item title.

    Separated with a colon rather than a slash because package names in several
    ecosystems already contain slashes — `composer/composer/composer` is
    unreadable where `composer:composer/composer` is not.
    """
    ecosystem = package.get("ecosystem")
    name = package.get("name")
    return f"{ecosystem}:{name}" if ecosystem else str(name)


def fetch_package_advisories(package: dict, token: str | None = None) -> list[dict]:
    """Fetch advisories affecting one published package."""
    params = {
        "affects": package["name"],
        "per_page": PER_PAGE,
    }
    if package.get("ecosystem"):
        params["ecosystem"] = package["ecosystem"]

    return paginate(
        f"{GITHUB_API_ROOT}/advisories",
        headers=_headers(token),
        params=params,
        context=package_label(package),
    )


def normalise(advisory: dict, label: str) -> dict:
    """Bring a global-database advisory into the shared advisory shape.

    The payload already matches on ghsa_id, summary, description, severity,
    published_at, withdrawn_at, cvss, cwes, and vulnerabilities. What it lacks is
    the origin label, which for this source is the package rather than a repo.
    """
    normalised = dict(advisory)
    normalised["repo"] = label
    # The database exposes the advisory at /advisories/{ghsa_id}; keep whichever
    # public URL the payload provides rather than constructing one.
    if not normalised.get("html_url") and normalised.get("url"):
        normalised["html_url"] = normalised["url"]
    return normalised


def fetch_advisories(feed_config: dict, token: str | None = None) -> SourceResult:
    """Fetch every package in one `source: ghsa` config entry."""
    result = SourceResult()

    for package in feed_config.get("packages", []):
        if not package.get("name"):
            log.error("Skipping ghsa package entry with no name: %r", package)
            continue

        label = package_label(package)
        try:
            advisories = fetch_package_advisories(package, token=token)
        except Exception as exc:
            result.record_failure(label, exc)
            continue

        if not advisories:
            # A misspelled package name returns an empty list rather than a 404,
            # so without this a typo would silently contribute nothing —
            # exactly the kind of quiet coverage hole this source exists to fix.
            log.warning("No advisories found for %s; check the package name", label)

        result.record_success(label, [normalise(a, label) for a in advisories])

    return result
