import pytest
import asyncio
from fastapi.testclient import TestClient
from server.core.server import app as core_app
from server.llm.server import app as llm_app
from server.neod.server import app as neod_app
from server.neoo.server import app as neoo_app
from server.neolocal.server import app as neolocal_app
from server.neollm.server import app as neollm_app
from server.neodo.server import app as neodo_app

# Test clients for each server
core_client = TestClient(core_app)
llm_client = TestClient(llm_app)
neod_client = TestClient(neod_app)
neoo_client = TestClient(neoo_app)
neolocal_client = TestClient(neolocal_app)
neollm_client = TestClient(neollm_app)
neodo_client = TestClient(neodo_app)

@pytest.mark.asyncio
async def test_core_server_health():
    """Test Core MCP Server health check"""
    response = core_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_llm_server_health():
    """Test LLM MCP Server health check"""
    response = llm_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_neod_server_health():
    """Test Neo Development Server health check"""
    response = neod_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_neoo_server_health():
    """Test Neo Operations Server health check"""
    response = neoo_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_neolocal_server_health():
    """Test Neo Local Server health check"""
    response = neolocal_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_neollm_server_health():
    """Test Neo Local LLM Server health check"""
    response = neollm_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_neodo_server_health():
    """Test Neo DO Server health check"""
    response = neodo_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_core_to_llm_integration():
    """Test integration between Core and LLM servers"""
    # Register LLM tool with Core
    response = core_client.post("/api/v1/tools/register", json={
        "name": "llm_generate",
        "description": "Generate text using LLM",
        "endpoint": "http://localhost:7444/api/v1/llm/generate"
    })
    assert response.status_code == 200

    # Test tool execution
    response = core_client.post("/api/v1/tools/execute", json={
        "tool": "llm_generate",
        "params": {
            "prompt": "Hello, world!",
            "max_tokens": 10
        }
    })
    assert response.status_code == 200
    assert "text" in response.json()

@pytest.mark.asyncio
async def test_core_to_neod_integration():
    """Test integration between Core and Neo Development servers"""
    # Register development tool with Core
    response = core_client.post("/api/v1/tools/register", json={
        "name": "run_tests",
        "description": "Run Python tests",
        "endpoint": "http://localhost:7445/api/v1/development/run_tests"
    })
    assert response.status_code == 200

    # Test tool execution
    response = core_client.post("/api/v1/tools/execute", json={
        "tool": "run_tests",
        "params": {
            "test_path": "tests/test_server_integration.py"
        }
    })
    assert response.status_code == 200
    assert "results" in response.json()

@pytest.mark.asyncio
async def test_core_to_neoo_integration():
    """Test integration between Core and Neo Operations servers"""
    # Register operations tool with Core
    response = core_client.post("/api/v1/tools/register", json={
        "name": "system_info",
        "description": "Get system information",
        "endpoint": "http://localhost:7446/api/v1/operations/system_info"
    })
    assert response.status_code == 200

    # Test tool execution
    response = core_client.post("/api/v1/tools/execute", json={
        "tool": "system_info",
        "params": {}
    })
    assert response.status_code == 200
    assert "cpu" in response.json()
    assert "memory" in response.json()

@pytest.mark.asyncio
async def test_core_to_neolocal_integration():
    """Test integration between Core and Neo Local servers"""
    # Register local tool with Core
    response = core_client.post("/api/v1/tools/register", json={
        "name": "file_info",
        "description": "Get file information",
        "endpoint": "http://localhost:7447/api/v1/local/file_info"
    })
    assert response.status_code == 200

    # Test tool execution
    response = core_client.post("/api/v1/tools/execute", json={
        "tool": "file_info",
        "params": {
            "path": "README.md"
        }
    })
    assert response.status_code == 200
    assert "size" in response.json()
    assert "type" in response.json()

@pytest.mark.asyncio
async def test_core_to_neollm_integration():
    """Test integration between Core and Neo Local LLM servers"""
    # Register local LLM tool with Core
    response = core_client.post("/api/v1/tools/register", json={
        "name": "local_llm_generate",
        "description": "Generate text using local LLM",
        "endpoint": "http://localhost:7448/api/v1/llm/generate"
    })
    assert response.status_code == 200

    # Test tool execution
    response = core_client.post("/api/v1/tools/execute", json={
        "tool": "local_llm_generate",
        "params": {
            "prompt": "Hello, world!",
            "max_tokens": 10
        }
    })
    assert response.status_code == 200
    assert "text" in response.json()

@pytest.mark.asyncio
async def test_core_to_neodo_integration():
    """Test integration between Core and Neo DO servers"""
    # Register DO tool with Core
    response = core_client.post("/api/v1/tools/register", json={
        "name": "list_droplets",
        "description": "List DigitalOcean droplets",
        "endpoint": "http://localhost:7449/api/v1/do/list_droplets"
    })
    assert response.status_code == 200

    # Test tool execution
    response = core_client.post("/api/v1/tools/execute", json={
        "tool": "list_droplets",
        "params": {}
    })
    assert response.status_code == 200
    assert isinstance(response.json(), list) 