"""Shared HTTP plumbing for advisory sources.

Every source talks to a paginated JSON API over the same unreliable network, so
retry policy, timeouts, and Link-header pagination live here rather than being
reimplemented per source.
"""

import logging
import time

import requests

log = logging.getLogger("vulnfeed")

# (connect, read) seconds. Without this a stalled connection blocks until the
# Actions six-hour job limit.
REQUEST_TIMEOUT = (5, 30)

# GitHub's endpoints default to 30 results per page, which silently truncated
# the feed for every busy repo before pagination was added.
PER_PAGE = 100

# Guards against a malformed Link header cycling forever.
MAX_PAGES = 50

MAX_ATTEMPTS = 4
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def backoff_seconds(response: requests.Response | None, attempt: int) -> float:
    """Seconds to wait before the next attempt, honouring Retry-After when given."""
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except (TypeError, ValueError):
            log.warning("Ignoring unparseable Retry-After header: %r", retry_after)
    return float(2**attempt)


def get_with_retries(url: str, headers: dict, params: dict | None = None) -> requests.Response:
    """GET a URL, retrying transient failures with bounded exponential backoff."""
    for attempt in range(MAX_ATTEMPTS):
        is_last = attempt == MAX_ATTEMPTS - 1
        try:
            response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            if is_last:
                raise
            delay = backoff_seconds(None, attempt)
            log.warning("GET %s failed (%s); retrying in %.0fs", url, exc, delay)
            time.sleep(delay)
            continue

        if not is_last and response.status_code in RETRY_STATUSES:
            delay = backoff_seconds(response, attempt)
            log.warning("GET %s returned %s; retrying in %.0fs", url, response.status_code, delay)
            time.sleep(delay)
            continue

        response.raise_for_status()
        return response

    raise RuntimeError("retry loop exhausted without returning")  # pragma: no cover


def paginate(
    url: str,
    headers: dict,
    params: dict | None = None,
    max_pages: int | None = None,
    context: str = "",
) -> list[dict]:
    """Collect every page of a JSON list endpoint by following Link rel="next"."""
    limit = max_pages or MAX_PAGES
    items: list[dict] = []

    for _ in range(limit):
        response = get_with_retries(url, headers=headers, params=params)
        batch = response.json()
        if not batch:
            break
        items.extend(batch)

        next_url = response.links.get("next", {}).get("url")
        if not next_url:
            break
        # The Link header URL already carries per_page and page.
        url, params = next_url, None
    else:
        log.warning("Stopped paginating %s after %d pages", context or url, limit)

    return items
