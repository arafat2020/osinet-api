"""PhoneInfoga adapter — phone OSINT provider.

Calls the PhoneInfoga REST API (a Go service running separately)
to gather publicly available information about a phone number such as:
  country, carrier, line type, formats, timezone.

Does NOT attempt to retrieve:
  - private subscriber records
  - private addresses
  - live location
  - private messages
  - authentication information
"""

from __future__ import annotations

import httpx
import phonenumbers

from app.core.config import settings
from app.core.logging import logger
from app.osint.base import OSINTProvider
from app.schemas.results import OSINTResult, ResultCategory, ResultStatus


class PhoneInfogaProvider(OSINTProvider):
    """Phone number lookup via PhoneInfoga REST API."""

    name: str = "phoneinfoga"

    async def search(self, target: str) -> list[OSINTResult]:
        """Query PhoneInfoga for *target* phone number."""
        results: list[OSINTResult] = []

        try:
            raw = await self._query_phoneinfoga(target)
            results = self._parse_results(target, raw)
        except httpx.ConnectError:
            logger.warning(
                "PhoneInfoga service not reachable at %s",
                settings.phoneinfoga_url,
            )
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.PHONE,
                    status=ResultStatus.ERROR,
                    value=target,
                    metadata={
                        "error": "PhoneInfoga service not reachable",
                        "url": settings.phoneinfoga_url,
                    },
                )
            )
        except Exception as exc:
            logger.exception("PhoneInfoga provider error: %s", exc)
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.PHONE,
                    status=ResultStatus.ERROR,
                    value=target,
                    metadata={"error": str(exc)},
                )
            )

        return results

    # ── Internal helpers ─────────────────────────────────────────

    async def _query_phoneinfoga(self, phone: str) -> dict:
        """Call the PhoneInfoga local/scan endpoint."""
        base = settings.phoneinfoga_url.rstrip("/")
        # Prefer sending a clean digits-only representation using phonenumbers:
        # country code + national number (e.g. 8801614545931) since PhoneInfoga
        # commonly expects no '+' or formatting characters.
        api_phone = phone.lstrip("+")
        try:
            parsed = phonenumbers.parse(phone, None)
            if phonenumbers.is_valid_number(parsed):
                api_phone = f"{parsed.country_code}{parsed.national_number}"
        except phonenumbers.NumberParseException:
            # Fall back to stripping '+' if parsing fails
            api_phone = phone.lstrip("+")

        url = f"{base}/api/numbers/{api_phone}/scan/local"
        logger.debug("PhoneInfoga query url: %s (from %s)", url, phone)

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)

            if resp.status_code == 200:
                return resp.json()  # type: ignore[no-any-return]
            elif resp.status_code == 400:
                return {"error": "Invalid phone number format"}
            elif resp.status_code == 429:
                return {"_rate_limited": True}
            else:
                return {"error": f"PhoneInfoga returned status {resp.status_code}"}

    def _parse_results(self, phone: str, raw: dict) -> list[OSINTResult]:
        """Convert PhoneInfoga scan response to OSINTResult instances."""
        results: list[OSINTResult] = []

        # Handle errors
        if raw.get("_rate_limited"):
            return [
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.PHONE,
                    status=ResultStatus.RATE_LIMITED,
                    value=phone,
                    metadata={"error": "Rate limited"},
                )
            ]

        if "error" in raw:
            return [
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.PHONE,
                    status=ResultStatus.ERROR,
                    value=phone,
                    metadata={"error": raw["error"]},
                )
            ]

        # Parse successful scan — extract public info
        country = raw.get("country", "")
        country_code = raw.get("countryCode", raw.get("country_code", ""))
        carrier = raw.get("carrier", "")
        line_type = raw.get("lineType", raw.get("line_type", ""))
        international = raw.get("internationalFormat", raw.get("international_format", ""))
        local_fmt = raw.get("localFormat", raw.get("local_format", ""))
        timezone_str = raw.get("timezone", "")
        raw_local = raw.get("rawLocal", raw.get("raw_local", ""))

        meta: dict = {}
        if country:
            meta["country"] = country
        if country_code:
            meta["country_code"] = country_code
        if carrier:
            meta["carrier"] = carrier
        if line_type:
            meta["line_type"] = line_type
        if international:
            meta["international_format"] = international
        if local_fmt:
            meta["local_format"] = local_fmt
        if timezone_str:
            meta["timezone"] = timezone_str
        if raw_local:
            meta["raw_local"] = raw_local

        # If we have meaningful data, it's a found result
        if meta:
            confidence = 0.7 if carrier else 0.5
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.PHONE,
                    status=ResultStatus.FOUND,
                    value=phone,
                    confidence=confidence,
                    metadata=meta,
                )
            )
        else:
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.PHONE,
                    status=ResultStatus.NOT_FOUND,
                    value=phone,
                    confidence=0.0,
                    metadata={"raw": raw},
                )
            )

        return results
