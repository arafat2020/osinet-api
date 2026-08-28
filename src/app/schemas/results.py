"""Pydantic schemas for the common OSINT result format."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ResultStatus(StrEnum):
    """Possible statuses for an OSINT result."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"
    RATE_LIMITED = "rate_limited"
    UNSUPPORTED = "unsupported"


class ResultCategory(StrEnum):
    """Possible categories for an OSINT result."""

    SOCIAL = "social"
    EMAIL = "email"
    PHONE = "phone"
    USERNAME = "username"
    DOMAIN = "domain"
    BREACH = "breach"
    PROFILE = "profile"
    GITHUB = "github"
    WEBSITE = "website"


class OSINTResult(BaseModel):
    """Unified schema returned by every OSINT provider."""

    source: str = Field(description="Name of the provider that produced this result")
    category: ResultCategory = Field(description="Category of the finding")
    status: ResultStatus = Field(description="Status of the lookup")
    value: str | None = Field(default=None, description="The discovered value or identifier")
    url: str | None = Field(default=None, description="URL associated with the finding")
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence: 0.0-0.3 weak, 0.3-0.6 possible, 0.6-0.8 probable, 0.8-1.0 strong",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra provider-specific metadata",
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        """Ensure confidence is clamped between 0.0 and 1.0."""
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (TypeError, ValueError):
            return 0.0


class ConfidenceLevel(StrEnum):
    """Human-readable confidence level."""

    WEAK = "weak"
    POSSIBLE = "possible"
    PROBABLE = "probable"
    STRONG = "strong"


def confidence_label(score: float) -> ConfidenceLevel:
    """Return a human-readable label for a confidence score."""
    if score < 0.3:
        return ConfidenceLevel.WEAK
    if score < 0.6:
        return ConfidenceLevel.POSSIBLE
    if score < 0.8:
        return ConfidenceLevel.PROBABLE
    return ConfidenceLevel.STRONG
