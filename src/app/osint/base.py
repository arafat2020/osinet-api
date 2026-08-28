"""Abstract OSINT provider interface and provider registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.results import OSINTResult


class OSINTProvider(ABC):
    """Base class that every OSINT integration must implement.

    This abstraction allows adding or removing providers without
    modifying any FastAPI route or the investigation service.
    """

    name: str = "base"

    @abstractmethod
    async def search(self, target: str) -> list[OSINTResult]:
        """Run an OSINT lookup against *target* and return normalised results."""
        raise NotImplementedError


class ProviderRegistry:
    """Central registry mapping target types to provider instances.

    Usage::

        registry = ProviderRegistry()
        registry.register("email", HoleheProvider())
        registry.register("username", SherlockProvider())

        providers = registry.get("email")
    """

    def __init__(self) -> None:
        self._providers: dict[str, list[OSINTProvider]] = {}

    def register(self, target_type: str, provider: OSINTProvider) -> None:
        """Register a provider for a given target type."""
        self._providers.setdefault(target_type, []).append(provider)

    def get(self, target_type: str) -> list[OSINTProvider]:
        """Return all providers registered for *target_type*."""
        return self._providers.get(target_type, [])

    def all_types(self) -> list[str]:
        """Return all registered target types."""
        return list(self._providers.keys())


def build_default_registry() -> ProviderRegistry:
    """Build the default provider registry with all available providers."""
    from app.osint.email.breach_check import BreachCheckProvider
    from app.osint.email.holehe import HoleheProvider
    from app.osint.phone.phoneinfoga import PhoneInfogaProvider
    from app.osint.username.sherlock import SherlockProvider

    registry = ProviderRegistry()

    # ── Email providers ──────────────────────────────────────────
    registry.register("email", HoleheProvider())
    registry.register("email", BreachCheckProvider())

    # ── Username providers ───────────────────────────────────────
    registry.register("username", SherlockProvider())

    # ── Phone providers ──────────────────────────────────────────
    registry.register("phone", PhoneInfogaProvider())

    return registry
