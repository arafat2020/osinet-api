"""OSINT Intelligence API — application entry point."""

from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.investigations import router as investigations_router

app = FastAPI(
    title="OSINT Intelligence API",
    description=(
        "Modular OSINT aggregation backend.  Accepts an email, username, "
        "or phone number and runs appropriate public-information OSINT "
        "modules, returning a structured intelligence report."
    ),
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(investigations_router)
