"""FastAPI dependency injection providers."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import Settings, settings
from app.osint.base import ProviderRegistry, build_default_registry
from app.services.investigation import InvestigationService


@lru_cache
def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    return settings


@lru_cache
def get_registry() -> ProviderRegistry:
    """Return the singleton provider registry."""
    return build_default_registry()


def get_investigation_service(
    registry: ProviderRegistry = Depends(get_registry),
) -> InvestigationService:
    """Build and return an InvestigationService."""
    return InvestigationService(registry=registry)


# ── Optional API-key authentication (feature-flag controlled) ────

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
    cfg: Settings = Depends(get_settings),
) -> str | None:
    """Validate the API key if authentication is enabled.

    When ``ENABLE_AUTH=false`` (default), this dependency is a no-op.
    When ``ENABLE_AUTH=true``, a valid ``X-API-Key`` header is required.
    """
    if not cfg.enable_auth:
        return None  # Auth disabled — allow all

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
        )

    if api_key not in cfg.api_keys:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
