"""Tests for Server-Sent Events (SSE) functionality."""

import pytest
from fastapi.testclient import TestClient
import json
import time

from server.core.server import CoreMCPServer

# Create server instance
server = CoreMCPServer()
client = TestClient(server.app)

def test_sse_endpoint():
    """Test the SSE endpoint functionality."""
    response = client.get("/sse")
    
    # Check response status and content type
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    
    # Read the response content
    content = response.content.decode()
    assert content.startswith("data: ")
    
    # Parse the SSE data
    data = json.loads(content[6:])  # Skip "data: " prefix
    assert "event" in data
    assert "data" in data
    assert "timestamp" in data["data"]
    assert "status" in data["data"] 