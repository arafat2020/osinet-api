"""Tests for the health endpoint."""

from __future__ import annotations


def test_health_returns_ok(client):
    """GET /health should return {"status": "ok"}."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
