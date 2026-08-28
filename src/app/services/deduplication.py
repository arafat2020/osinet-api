"""Result deduplication logic.

Two providers may discover the same account.  We deduplicate by building
a normalised composite key from each result and keeping only the entry
with the highest confidence score.
"""

from __future__ import annotations

from urllib.parse import urlparse

from app.schemas.results import OSINTResult


def _dedup_key(result: OSINTResult) -> str:
    """Build a composite deduplication key.

    The key is constructed from:
    - category
    - normalised domain (from URL, if present)
    - normalised value

    This avoids false merges from display-name-only matching.
    """
    domain = ""
    if result.url:
        try:
            parsed = urlparse(result.url)
            netloc = (parsed.netloc or "").lower()
            domain = netloc.removeprefix("www.")
        except Exception:
            domain = ""

    value = (result.value or "").strip().lower()
    return f"{result.category.value}::{domain}::{value}"


def deduplicate(results: list[OSINTResult]) -> list[OSINTResult]:
    """Remove duplicate results, keeping the one with the highest confidence.

    Duplicates are identified by a composite key of
    ``category + domain + value``.
    """
    seen: dict[str, OSINTResult] = {}

    for result in results:
        key = _dedup_key(result)
        existing = seen.get(key)
        if existing is None or result.confidence > existing.confidence:
            seen[key] = result

    return list(seen.values())
