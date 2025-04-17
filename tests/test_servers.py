"""
Tests for server initialization.
"""

import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from fastapi import FastAPI

# Import BaseServer for testing middleware
from server.utils.base_server import BaseServer

# Remove direct server imports - use factories or clients
# from server.core.server import server as core_server
# from server.neod.server import server as neod_server
# from server.neoo.server import server as neoo_server
# from server.neolocal.server import server as neolocal_server

# Import the factory functions
from server.core import create_app as create_core_app
from server.llm import create_app as create_llm_app
from server.neod import create_app as create_neod_app
from server.neoo import create_app as create_neoo_app
from server.neolocal import create_app as create_neolocal_app
# from server.neollm import create_app as create_neollm_app # Assuming this exists
from server.neodo.main import create_app as create_neodo_app

# --- BaseServer Middleware Tests ---

# Remove BaseServer Middleware Tests (lines 28-247 approximately)
# These will be moved to tests/utils/test_base_server.py

# --- Basic Server Creation Tests ---
# These tests verify that the create_app factory for each server module
# can be called without raising immediate errors. They don't test functionality.

def test_core_server_creation(core_client: TestClient): # Use the client fixture
    """Test Core server app creation via fixture."""
    assert isinstance(core_client.app, FastAPI)

def test_llm_server_creation(llm_client: TestClient): # Use the client fixture
    """Test LLM server app creation via fixture."""
    assert isinstance(llm_client.app, FastAPI)

def test_neod_server_creation(neod_client: TestClient): # Use the client fixture
    """Test NeoD server app creation via fixture."""
    assert isinstance(neod_client.app, FastAPI)

def test_neoo_server_creation(neoo_client: TestClient): # Use the client fixture
    """Test NeoO server app creation via fixture."""
    assert isinstance(neoo_client.app, FastAPI)

def test_neolocal_server_creation(neolocal_client: TestClient): # Use the client fixture
    """Test NeoLocal server app creation via fixture."""
    assert isinstance(neolocal_client.app, FastAPI)

def test_neollm_server_creation(neollm_client: TestClient): # Use the client fixture
    """Test NeoLLM server app creation via fixture."""
    assert isinstance(neollm_client.app, FastAPI)

def test_neodo_server_creation(neodo_client: TestClient): # Use the client fixture
    """Test NeoDO server app creation via fixture."""
    assert isinstance(neodo_client.app, FastAPI)

# --- Basic Health Check Tests ---
# These tests use the individual client fixtures (which create isolated apps)
# to hit the standard /health endpoint provided by BaseServer.

def test_core_health(core_client: TestClient):
    """Test Core server health endpoint."""
    response = core_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"].startswith("core") # Check service name prefix

def test_llm_health(llm_client: TestClient):
    """Test LLM server health endpoint."""
    response = llm_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"].startswith("llm") # Check service name prefix

def test_neod_health(neod_client: TestClient):
    """Test NeoD server health endpoint."""
    response = neod_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    # assert response.json()["service"] == "neod_mcp" # Or check prefix

def test_neoo_health(neoo_client: TestClient):
    """Test NeoO server health endpoint."""
    response = neoo_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"].startswith("neoo") # Check service name prefix

def test_neolocal_health(neolocal_client: TestClient):
    """Test NeoLocal server health endpoint."""
    response = neolocal_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"].startswith("neolocal") # Check service name prefix

def test_neollm_health(neollm_client: TestClient):
    """Test NeoLLM server health endpoint."""
    response = neollm_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"].startswith("neo-local-llm") # Check service name prefix

def test_neodo_health(neodo_client: TestClient):
    """Test NeoDO server health endpoint."""
    response = neodo_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"].startswith("neodo") # Check service name prefix

# TODO: Add more specific server initialization tests if needed,
# but prefer testing via TestClient and fixtures where possible. 