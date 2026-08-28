"""Pydantic schemas for the investigation API."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.results import OSINTResult


class InvestigationRequest(BaseModel):
    """Request body for creating a new investigation."""

    type: Literal["email", "username", "phone"] = Field(
        description="The type of target to investigate"
    )
    value: str = Field(
        min_length=1,
        max_length=256,
        description="The target value (email, username, or phone number)",
    )


class InvestigationTarget(BaseModel):
    """The normalized target of an investigation."""

    type: str
    value: str


class InvestigationSummary(BaseModel):
    """Summary statistics for an investigation."""

    providers_executed: int = 0
    total_results: int = 0
    found_results: int = 0
    errors: int = 0


class InvestigationResponse(BaseModel):
    """Full response body for an investigation."""

    id: str = Field(description="Unique investigation identifier")
    target: InvestigationTarget
    status: str = Field(description="Investigation status: pending, running, completed, failed")
    results: list[OSINTResult] = Field(default_factory=list)
    summary: InvestigationSummary = Field(default_factory=InvestigationSummary)
    created_at: datetime
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
