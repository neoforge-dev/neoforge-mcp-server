"""Tests for the NeoLocal server."""
import pytest
from fastapi.testclient import TestClient

def test_neolocal_health_endpoint(neolocal_client):
    """Test the health endpoint of the NeoLocal server."""
    response = neolocal_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy" 