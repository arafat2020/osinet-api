"""Sherlock adapter — username OSINT provider.

Wraps the sherlock-project library behind the OSINTProvider interface.
Distinguishes between confirmed results, possible results, not found,
and errors.  Avoids treating HTTP redirects or generic pages as proof
of account ownership.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.core.logging import logger
from app.osint.base import OSINTProvider
from app.schemas.results import OSINTResult, ResultCategory, ResultStatus


class SherlockProvider(OSINTProvider):
    """Username lookup via Sherlock."""

    name: str = "sherlock"

    async def search(self, target: str) -> list[OSINTResult]:
        """Run sherlock against *target* username and return normalised results."""
        results: list[OSINTResult] = []

        try:
            raw = await self._run_sherlock(target)
            results = self._parse_results(target, raw)
        except FileNotFoundError:
            logger.error("sherlock binary not found — is sherlock-project installed?")
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.USERNAME,
                    status=ResultStatus.ERROR,
                    value=target,
                    metadata={"error": "sherlock binary not found"},
                )
            )
        except Exception as exc:
            logger.exception("Sherlock provider error: %s", exc)
            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.USERNAME,
                    status=ResultStatus.ERROR,
                    value=target,
                    metadata={"error": str(exc)},
                )
            )

        return results

    # ── Internal helpers ─────────────────────────────────────────

    async def _run_sherlock(self, username: str) -> list[dict]:
        """Execute sherlock in a subprocess and return parsed JSON output."""
        sherlock_bin = shutil.which("sherlock")
        if sherlock_bin is None:
            raise FileNotFoundError("sherlock")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"

            cmd = [
                sherlock_bin,
                username,
                "--json", str(output_path),
                "--timeout", "15",
                "--no-color",
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=tmpdir,
            )

            _, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=120,
            )

            if process.returncode not in (0, 1):
                logger.warning(
                    "Sherlock exited with code %s: %s",
                    process.returncode,
                    stderr.decode(errors="replace")[:500],
                )

            # Parse JSON output
            if output_path.exists():
                text = output_path.read_text(encoding="utf-8")
                if text.strip():
                    data = json.loads(text)
                    # Sherlock outputs {username: {site: {...}, ...}}
                    if isinstance(data, dict) and username in data:
                        sites = data[username]
                        return [
                            {"site": site, **info}
                            for site, info in sites.items()
                            if isinstance(info, dict)
                        ]
                    elif isinstance(data, dict):
                        # Flat dict: {site: {...}, ...}
                        return [
                            {"site": site, **info}
                            for site, info in data.items()
                            if isinstance(info, dict)
                        ]
                    elif isinstance(data, list):
                        return data

        return []

    def _parse_results(self, username: str, raw: list[dict]) -> list[OSINTResult]:
        """Convert raw sherlock output to OSINTResult instances."""
        results: list[OSINTResult] = []

        for entry in raw:
            site = entry.get("site", entry.get("name", "unknown"))
            url = entry.get("url_user", entry.get("url", ""))
            status_str = str(entry.get("status", "")).lower()
            http_status = entry.get("http_status", None)

            # Determine status and confidence
            if status_str in ("claimed", "found"):
                status = ResultStatus.FOUND
                confidence = self._calculate_confidence(entry, http_status)
            elif status_str in ("available", "not found"):
                # Skip not-found entries
                continue
            elif status_str in ("illegal", "error"):
                status = ResultStatus.ERROR
                confidence = 0.0
            else:
                # Unknown status — treat as possible
                status = ResultStatus.FOUND
                confidence = 0.3

            results.append(
                OSINTResult(
                    source=self.name,
                    category=ResultCategory.USERNAME,
                    status=status,
                    value=username,
                    url=url if url else None,
                    confidence=confidence,
                    metadata={
                        "platform": site,
                        "http_status": http_status,
                    },
                )
            )

        return results

    @staticmethod
    def _calculate_confidence(entry: dict, http_status: int | None) -> float:
        """Calculate confidence based on response indicators.

        Higher confidence for direct 200 responses with content matching.
        Lower confidence for redirects or status-code-only detection.
        """
        # If HTTP 200, base confidence is good
        if http_status == 200:
            confidence = 0.85
        elif http_status and 300 <= http_status < 400:
            # Redirect — may be a false positive
            confidence = 0.4
        elif http_status is None:
            confidence = 0.6
        else:
            confidence = 0.5

        # Boost if response_time is fast (site responded specifically)
        response_time = entry.get("response_time")
        if response_time and isinstance(response_time, (int, float)) and response_time < 2.0:
            confidence = min(1.0, confidence + 0.05)

        return round(confidence, 2)
