"""Pluggable advisory sources.

Each source module exposes:

    fetch_advisories(feed_config: dict, token: str | None) -> SourceResult

`feed_config` is one entry from the `feeds:` list in config.yaml. The source is
responsible for isolating failures across its own units of work (repos for
GitHub, packages for the advisory database) and reporting them via SourceResult,
so one bad entry never stops the rest of the run.

Every source must return advisories in the shape the aggregator consumes:

    ghsa_id       str    stable unique ID, used for dedup and as the RSS guid
    html_url      str    link to the advisory
    summary       str    one-line title
    description   str    body text (markdown)
    severity      str    low | medium | high | critical (may be None)
    published_at  str    ISO 8601 timestamp (may be None)
    repo          str    origin label shown in the feed item title

Optional enrichment fields, all tolerated as absent: cve_id, cvss,
cvss_severities, cwes, vulnerabilities, withdrawn_at.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import requests

log = logging.getLogger("vulnfeed")


@dataclass
class SourceResult:
    """Advisories from a source, plus which of its targets worked."""

    advisories: list[dict] = field(default_factory=list)
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def record_success(self, target: str, advisories: list[dict]) -> None:
        self.advisories.extend(advisories)
        self.succeeded.append(target)
        log.info("Fetched %d advisories from %s", len(advisories), target)

    def record_failure(self, target: str, error: BaseException) -> None:
        if isinstance(error, requests.RequestException):
            log.error("Failed to fetch advisories for %s: %s", target, error)
        else:
            log.exception("Unexpected error fetching advisories for %s", target, exc_info=error)
        self.failed.append(target)

    def merge(self, other: "SourceResult") -> None:
        self.advisories.extend(other.advisories)
        self.succeeded.extend(other.succeeded)
        self.failed.extend(other.failed)


def get_source(name: str | None) -> Callable[..., SourceResult] | None:
    """Look up a source's entry point by its config `source:` value."""
    if name is None:
        return None

    # Imported here rather than at module scope: source modules import
    # SourceResult from this module, so a top-level import would be circular.
    from sources import ghsa, github

    registry: dict[str, Callable[..., SourceResult]] = {
        "github": github.fetch_advisories,
        "ghsa": ghsa.fetch_advisories,
    }
    return registry.get(name)
