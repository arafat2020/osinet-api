"""Breach check adapter — email OSINT provider.

Checks public breach aggregation APIs to determine whether an email
has appeared in known data breaches.  Uses the public "Have I Been
Pwned" v3 API (or compatible endpoint).

This module only checks publicly available breach metadata — it does
NOT retrieve passwords, hashes, or private data.
"""

from __future__ import annotations

import httpx

from app.core.logging import logger
from app.osint.base import OSINTProvider
from app.schemas.results import OSINTResult, ResultCategory, ResultStatus

_HIBP_API = "https://haveibeenpwned.com/api/v3"


class BreachCheckProvider(OSINTProvider):
    """Email breach-exposure check via public APIs."""

    name: str = "breach_check"

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key

    async def search(self, target: str) -> list[OSINTResult]:
        """Check *target* email against breach databases."""
        results: list[OSINTResult] = []

        try:
            breaches = await self._check_hibp(target)
            results = self._parse_results(target, breaches)
        except Exception as exc:
            logger.exception("Breach check provider error: %s", exc)
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.BREACH,
                    status=ResultStatus.ERROR,
                    value=target,
                    metadata={"error": str(exc)},
                )
            )

        return results

    async def _check_hibp(self, email: str) -> list[dict]:
        """Query the Have I Been Pwned breached-account endpoint."""
        headers: dict[str, str] = {
            "User-Agent": "OSINT-Intelligence-API",
        }
        if self._api_key:
            headers["hibp-api-key"] = self._api_key

        url = f"{_HIBP_API}/breachedaccount/{email}"
        params = {"truncateResponse": "false"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, params=params)

            if resp.status_code == 200:
                return resp.json()  # type: ignore[no-any-return]
            elif resp.status_code == 404:
                # No breaches found — this is a good thing
                return []
            elif resp.status_code == 401:
                logger.warning("HIBP API key required or invalid")
                return []
            elif resp.status_code == 429:
                logger.warning("HIBP rate limited")
                return [{"_rate_limited": True}]
            else:
                logger.warning("HIBP returned status %s", resp.status_code)
                return []

    def _parse_results(self, email: str, breaches: list[dict]) -> list[OSINTResult]:
        """Convert HIBP breach data to OSINTResult instances."""
        results: list[OSINTResult] = []

        for breach in breaches:
            # Handle rate-limiting marker
            if breach.get("_rate_limited"):
                results.append(
                    OSINTResult(
                        source=self.name,
                        category=ResultCategory.BREACH,
                        status=ResultStatus.RATE_LIMITED,
                        value=email,
                        metadata={"error": "Rate limited by HIBP API"},
                    )
                )
                continue

            name = breach.get("Name", "Unknown")
            domain = breach.get("Domain", "")
            breach_date = breach.get("BreachDate", "")
            data_classes = breach.get("DataClasses", [])
            is_verified = breach.get("IsVerified", False)

            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.BREACH,
                    status=ResultStatus.FOUND,
                    value=email,
                    url=f"https://{domain}" if domain else None,
                    confidence=0.95 if is_verified else 0.7,
                    metadata={
                        "breach_name": name,
                        "breach_date": breach_date,
                        "data_classes": data_classes,
                        "is_verified": is_verified,
                        "domain": domain,
                    },
                )
            )

        return results
