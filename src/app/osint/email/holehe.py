"""Holehe adapter — email OSINT provider.

Wraps the Holehe library behind the OSINTProvider interface.
Holehe checks whether an email address is registered on various
online services using password-reset and sign-up enumeration
(all publicly accessible endpoints).

Important: does NOT claim an account exists solely because of an
ambiguous response.
"""

from __future__ import annotations

import asyncio

import httpx

from app.core.logging import logger
from app.osint.base import OSINTProvider
from app.schemas.results import OSINTResult, ResultCategory, ResultStatus


class HoleheProvider(OSINTProvider):
    """Email account enumeration via Holehe."""

    name: str = "holehe"

    async def search(self, target: str) -> list[OSINTResult]:
        """Run holehe modules against *target* email and return normalised results."""
        results: list[OSINTResult] = []

        try:
            raw = await self._run_holehe(target)
            results = self._parse_results(target, raw)
        except ImportError:
            logger.error("holehe package not installed")
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.EMAIL,
                    status=ResultStatus.ERROR,
                    value=target,
                    metadata={"error": "holehe package not installed"},
                )
            )
        except Exception as exc:
            logger.exception("Holehe provider error: %s", exc)
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.EMAIL,
                    status=ResultStatus.ERROR,
                    value=target,
                    metadata={"error": str(exc)},
                )
            )

        return results

    # ── Internal helpers ─────────────────────────────────────────

    async def _run_holehe(self, email: str) -> list[dict]:
        """Execute holehe's modules and collect results."""
        from holehe import core as holehe_core

        out: list[dict] = []

        # Holehe uses httpx internally. We create a shared client.
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Get all available modules from the 'holehe.modules' package
            modules = holehe_core.import_submodules("holehe.modules")

            tasks = []
            for full_name, module in modules.items():
                # The module function is named after the last path segment
                site = full_name.split(".")[-1]
                func = getattr(module, site, None)
                if func is None:
                    continue
                tasks.append(self._run_module(func, email, client, out))

            # Run all modules concurrently with a reasonable concurrency limit
            semaphore = asyncio.Semaphore(10)

            async def _limited(coro):
                async with semaphore:
                    return await coro

            await asyncio.gather(
                *[_limited(t) for t in tasks],
                return_exceptions=True,
            )

        return out

    @staticmethod
    async def _run_module(func, email: str, client: httpx.AsyncClient, out: list[dict]) -> None:
        """Run a single holehe module safely."""
        try:
            await func(email, client, out)
        except Exception as exc:
            logger.debug("Holehe module %s failed: %s", func.__name__, exc)

    def _parse_results(self, email: str, raw: list[dict]) -> list[OSINTResult]:
        """Convert raw holehe output to OSINTResult instances."""
        results: list[OSINTResult] = []

        for entry in raw:
            name = entry.get("name", "unknown")
            exists = entry.get("exists", False)
            rate_limited = entry.get("rateLimit", False)
            email_recovery = entry.get("emailrecovery", None)
            phone_recovery = entry.get("phoneNumber", None)
            others = entry.get("others", None)

            # Determine status
            if rate_limited:
                status = ResultStatus.RATE_LIMITED
                confidence = 0.0
            elif exists is True:
                status = ResultStatus.FOUND
                confidence = 0.8
            elif exists is False:
                # Skip services where the email is not registered
                continue
            else:
                # Ambiguous — do NOT claim it exists
                continue

            # Build metadata
            meta: dict = {"service": name}
            if email_recovery:
                meta["email_recovery"] = email_recovery
            if phone_recovery:
                meta["phone_recovery"] = phone_recovery
            if others:
                meta["others"] = others

            # Try to build a service URL
            domain = entry.get("domain", "")
            url = f"https://{domain}" if domain else None

            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.EMAIL,
                    status=status,
                    value=email,
                    url=url,
                    confidence=confidence,
                    metadata=meta,
                )
            )

        return results
