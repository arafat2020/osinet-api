"""Investigation API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_investigation_service, verify_api_key
from app.schemas.investigation import InvestigationRequest, InvestigationResponse
from app.services.investigation import InvestigationService

router = APIRouter(
    prefix="/api/v1",
    tags=["investigations"],
    dependencies=[Depends(verify_api_key)],
)


@router.post("/investigations", response_model=InvestigationResponse)
async def create_investigation(
    request: InvestigationRequest,
    service: InvestigationService = Depends(get_investigation_service),
) -> InvestigationResponse:
    """Create and execute a new OSINT investigation.

    Accepts an email, username, or phone number and runs the appropriate
    OSINT modules against it.  Returns a structured intelligence report
    with normalised, deduplicated results and confidence scores.
    """
    return await service.investigate(
        target_type=request.type,
        target_value=request.value,
    )
