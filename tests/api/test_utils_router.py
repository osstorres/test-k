from __future__ import annotations

import pytest
from fastapi import status
from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """Test the health check endpoint returns 200 OK with True."""
    response = client.get("/api/v1/health")
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True


def test_health_check_response_type(client: TestClient) -> None:
    """Test the health check endpoint returns a boolean value."""
    response = client.get("/api/v1/health")
    
    assert isinstance(response.json(), bool)
    assert response.json() is True


def test_health_check_method_not_allowed(client: TestClient) -> None:
    """Test that POST method is not allowed on health check endpoint."""
    response = client.post("/api/v1/health")
    
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
