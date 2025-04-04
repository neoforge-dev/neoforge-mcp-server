"""
Tests for server initialization.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock

# Import servers
from server.neod.server import server as neod_server
from server.neoo.server import server as neoo_server
from server.neolocal.server import server as neolocal_server

def test_neod_server_init():
    """Test Neo Development Server initialization."""
    app = neod_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neod_mcp"

def test_neoo_server_init():
    """Test Neo Operations Server initialization."""
    app = neoo_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neoo_mcp"

def test_neolocal_server_init():
    """Test Neo Local Server initialization."""
    app = neolocal_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neolocal_mcp"

@pytest.mark.skipif(
    not os.environ.get("TEST_LOCAL_LLM"),
    reason="Local LLM tests are disabled"
)
def test_neollm_server_init():
    """Test Neo Local LLM Server initialization."""
    # Dynamically import to avoid loading the model during test collection
    from server.neollm.server import server as neollm_server
    
    app = neollm_server.get_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "neollm_mcp" 