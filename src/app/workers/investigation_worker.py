"""Background investigation worker using ARQ (async Redis queue).

This worker picks investigation jobs from the Redis queue, executes
OSINT providers, and persists results to the database.

Only active when ``ENABLE_BACKGROUND_WORKERS=true``.
"""

from __future__ import annotations

from typing import ClassVar

from arq import cron  # noqa: F401  — re-exported for ARQ discovery
from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import logger
from app.osint.base import build_default_registry
from app.services.investigation import InvestigationService


async def run_investigation(
    ctx: dict,
    target_type: str,
    target_value: str,
    investigation_id: str | None = None,
) -> dict:
    """ARQ task: execute an investigation pipeline.

    This is the function that gets enqueued to Redis and executed by
    the ARQ worker process.
    """
    logger.info(
        "Worker picked up investigation %s (type=%s)",
        investigation_id or "inline",
        target_type,
    )

    registry = build_default_registry()
    service = InvestigationService(registry=registry)

    result = await service.investigate(
        target_type=target_type,
        target_value=target_value,
    )

    logger.info(
        "Worker completed investigation %s — %d results",
        result.id,
        result.summary.total_results,
    )

    return result.model_dump(mode="json")


class WorkerSettings:
    """ARQ worker configuration.

    ARQ discovers this class automatically when started with::

        arq app.workers.investigation_worker.WorkerSettings
    """

    functions: ClassVar[list] = [run_investigation]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs: int = settings.max_concurrent_providers
    job_timeout: int = settings.request_timeout * 5  # generous timeout for full pipelines
