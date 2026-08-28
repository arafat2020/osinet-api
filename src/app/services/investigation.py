"""Investigation orchestration service.

Coordinates the full pipeline:
  input validation → normalization → provider dispatch →
  result collection → result normalization → deduplication →
  confidence scoring → report assembly.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from app.core.config import settings
from app.core.logging import audit_log, logger
from app.osint.base import ProviderRegistry
from app.schemas.investigation import (
    InvestigationResponse,
    InvestigationSummary,
    InvestigationTarget,
)
from app.schemas.results import OSINTResult, ResultStatus
from app.services.deduplication import deduplicate
from app.services.normalization import normalize_results, normalize_target, validate_target


class InvestigationService:
    """Stateless service that runs an investigation pipeline."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self._registry = registry

    async def investigate(
        self,
        target_type: str,
        target_value: str,
    ) -> InvestigationResponse:
        """Execute a full investigation and return a structured report."""
        investigation_id = f"inv_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(UTC)

        # 1. Validate
        normalized = normalize_target(target_type, target_value)
        is_valid, error = validate_target(target_type, normalized)
        if not is_valid:
            return InvestigationResponse(
                id=investigation_id,
                target=InvestigationTarget(type=target_type, value=target_value),
                status="failed",
                results=[],
                summary=InvestigationSummary(),
                created_at=created_at,
                completed_at=datetime.now(UTC),
                metadata={"error": error},
            )

        # 2. Select providers
        providers = self._registry.get(target_type)
        if not providers:
            return InvestigationResponse(
                id=investigation_id,
                target=InvestigationTarget(type=target_type, value=normalized),
                status="completed",
                results=[],
                summary=InvestigationSummary(),
                created_at=created_at,
                completed_at=datetime.now(UTC),
                metadata={"warning": f"No providers registered for type '{target_type}'"},
            )

        # 3. Execute providers concurrently (with concurrency limit)
        semaphore = asyncio.Semaphore(settings.max_concurrent_providers)

        async def _run_provider(provider):
            async with semaphore:
                try:
                    return await asyncio.wait_for(
                        provider.search(normalized),
                        timeout=settings.request_timeout,
                    )
                except TimeoutError:
                    logger.warning(
                        "Provider %s timed out for target type %s",
                        provider.name,
                        target_type,
                    )
                    return [
                        OSINTResult(
                            source=provider.name,
                            category=target_type,
                            status=ResultStatus.ERROR,
                            metadata={"error": "Provider timed out"},
                        )
                    ]
                except Exception as exc:
                    logger.exception("Provider %s failed: %s", provider.name, exc)
                    return [
                        OSINTResult(
                            source=provider.name,
                            category=target_type,
                            status=ResultStatus.ERROR,
                            metadata={"error": str(exc)},
                        )
                    ]

        raw_results = await asyncio.gather(
            *[_run_provider(p) for p in providers],
            return_exceptions=True,
        )

        # 4. Flatten and handle any remaining exceptions
        all_results: list[OSINTResult] = []
        errors = 0
        for batch in raw_results:
            if isinstance(batch, BaseException):
                errors += 1
                logger.error("Unhandled provider exception: %s", batch)
                continue
            if isinstance(batch, list):
                all_results.extend(batch)

        # 5. Normalize results
        all_results = normalize_results(all_results)

        # 6. Deduplicate
        all_results = deduplicate(all_results)

        # 7. Build summary
        found_count = sum(1 for r in all_results if r.status == ResultStatus.FOUND)
        error_count = errors + sum(1 for r in all_results if r.status == ResultStatus.ERROR)

        summary = InvestigationSummary(
            providers_executed=len(providers),
            total_results=len(all_results),
            found_results=found_count,
            errors=error_count,
        )

        completed_at = datetime.now(UTC)

        # 8. Audit log (no raw target values)
        audit_log(
            investigation_id=investigation_id,
            target_type=target_type,
            providers_executed=[p.name for p in providers],
            status="completed",
        )

        return InvestigationResponse(
            id=investigation_id,
            target=InvestigationTarget(type=target_type, value=normalized),
            status="completed",
            results=all_results,
            summary=summary,
            created_at=created_at,
            completed_at=completed_at,
        )
