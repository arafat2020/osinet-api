"""Tests for the investigation endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from app.schemas.results import OSINTResult, ResultCategory, ResultStatus


def test_investigation_username_returns_200(client):
    """POST /api/v1/investigations with a valid username should return 200."""
    response = client.post(
        "/api/v1/investigations",
        json={"type": "username", "value": "testuser"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("completed", "failed")
    assert data["target"]["type"] == "username"
    assert "results" in data
    assert "summary" in data
    assert "id" in data


def test_investigation_email_returns_200(client):
    """POST /api/v1/investigations with a valid email should return 200."""
    response = client.post(
        "/api/v1/investigations",
        json={"type": "email", "value": "test@example.com"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["target"]["type"] == "email"
    assert data["target"]["value"] == "test@example.com"


def test_investigation_phone_returns_200(client):
    """POST /api/v1/investigations with a valid phone should return 200."""
    response = client.post(
        "/api/v1/investigations",
        json={"type": "phone", "value": "+1234567890"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["target"]["type"] == "phone"


def test_investigation_invalid_type_returns_422(client):
    """POST with an invalid type should return 422."""
    response = client.post(
        "/api/v1/investigations",
        json={"type": "invalid", "value": "something"},
    )
    assert response.status_code == 422


def test_investigation_empty_value_returns_422(client):
    """POST with an empty value should return 422."""
    response = client.post(
        "/api/v1/investigations",
        json={"type": "username", "value": ""},
    )
    assert response.status_code == 422


def test_investigation_missing_fields_returns_422(client):
    """POST with missing fields should return 422."""
    response = client.post(
        "/api/v1/investigations",
        json={},
    )
    assert response.status_code == 422


def test_investigation_with_mock_provider(client):
    """POST with a mocked provider should return the mocked results."""
    mock_result = OSINTResult(
        source="test_provider",
        category=ResultCategory.USERNAME,
        status=ResultStatus.FOUND,
        value="testuser",
        url="https://example.com/testuser",
        confidence=0.9,
        metadata={"platform": "example"},
    )

    with patch(
        "app.osint.username.sherlock.SherlockProvider.search",
        new_callable=AsyncMock,
        return_value=[mock_result],
    ):
        response = client.post(
            "/api/v1/investigations",
            json={"type": "username", "value": "testuser"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert len(data["results"]) >= 1

    # Find our mocked result
    test_results = [r for r in data["results"] if r["source"] == "test_provider"]
    assert len(test_results) == 1
    assert test_results[0]["confidence"] == 0.9
    assert test_results[0]["url"] == "https://example.com/testuser"
