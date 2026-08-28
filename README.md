# OSINT Intelligence API

Modular OSINT aggregation backend built with **FastAPI** and managed by **uv**.

The API accepts an email address, username, or phone number, runs appropriate public-information OSINT modules, and returns a structured intelligence report.

## Architecture

```
POST /api/v1/investigations
        │
        ▼
  Input Validation & Normalization
        │
        ▼
  Provider Registry
        │
  ┌─────┼─────────────┐
  ▼     ▼             ▼
Email  Username      Phone
├─Holehe ├─Sherlock   └─PhoneInfoga
└─BreachCheck
        │
        ▼
  Result Normalization
        │
        ▼
  Deduplication + Confidence Scoring
        │
        ▼
  Structured Report
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Docker & Docker Compose (for full stack)

### Local Development

```bash
# Install dependencies
uv sync

# Start the dev server
uv run fastapi dev src/app/main.py

# Run tests
uv run pytest

# Lint & format
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy src
```

### Docker Compose (Full Stack)

```bash
# Copy and configure environment
cp .env.example .env

# Start all services (API + PostgreSQL + Redis + Worker + PhoneInfoga)
docker compose up --build
```

### API Usage

```bash
# Health check
curl http://localhost:8000/health

# Run a username investigation
curl -X POST http://localhost:8000/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{"type": "username", "value": "example_user"}'

# Run an email investigation
curl -X POST http://localhost:8000/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{"type": "email", "value": "user@example.com"}'

# Run a phone investigation
curl -X POST http://localhost:8000/api/v1/investigations \
  -H "Content-Type: application/json" \
  -d '{"type": "phone", "value": "+1234567890"}'
```

## Feature Flags

All major features can be toggled on/off via environment variables:

| Variable | Default | Description |
|---|---|---|
| `ENABLE_AUTH` | `false` | API key authentication |
| `ENABLE_RATE_LIMITING` | `false` | Request rate limiting |
| `ENABLE_BACKGROUND_WORKERS` | `false` | Redis-backed async processing |
| `ENABLE_DATABASE` | `false` | PostgreSQL persistence |

## Project Structure

```
osint-api/
├── src/app/
│   ├── main.py                  # FastAPI entry point
│   ├── api/                     # HTTP layer
│   │   ├── deps.py              # Dependency injection
│   │   └── routes/              # Endpoint definitions
│   ├── core/                    # Configuration & logging
│   ├── schemas/                 # Pydantic models
│   ├── services/                # Business logic
│   │   ├── investigation.py     # Orchestration pipeline
│   │   ├── normalization.py     # Input/output normalization
│   │   └── deduplication.py     # Result deduplication
│   ├── osint/                   # OSINT provider adapters
│   │   ├── base.py              # Abstract interface + registry
│   │   ├── email/               # Email providers
│   │   ├── username/            # Username providers
│   │   └── phone/               # Phone providers
│   ├── db/                      # Database layer
│   └── workers/                 # Background job workers
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── uv.lock
```

## Adding New Providers

1. Create a new file in the appropriate `osint/<type>/` directory
2. Implement the `OSINTProvider` interface
3. Register it in `osint/base.py → build_default_registry()`

```python
from app.osint.base import OSINTProvider
from app.schemas.results import OSINTResult

class MyProvider(OSINTProvider):
    name = "my_provider"

    async def search(self, target: str) -> list[OSINTResult]:
        # Your implementation here
        ...
```

## License

Private — not for redistribution.
