"""Structured logging with audit trail support."""

import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings


def _setup_logger() -> logging.Logger:
    """Configure and return the application logger."""
    logger = logging.getLogger("osint_api")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)

        if settings.log_format == "json":
            formatter = logging.Formatter(
                '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","message":"%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )

        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


logger = _setup_logger()


def audit_log(
    *,
    investigation_id: str,
    target_type: str,
    providers_executed: list[str],
    status: str,
) -> None:
    """Record an audit entry for an investigation.

    Never logs raw sensitive target values — only the type and metadata.
    """
    entry = {
        "event": "investigation_audit",
        "investigation_id": investigation_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "target_type": target_type,
        "providers_executed": providers_executed,
        "status": status,
    }
    logger.info("AUDIT | %s", entry)
