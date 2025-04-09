"""Common test fixtures for Terminal Command Runner MCP tests."""

import os
import sys
import pytest
import tempfile
import shutil
from contextlib import contextmanager
from typing import Generator, Dict, Any
import threading
import time
import asyncio
from fastapi.testclient import TestClient
from server.core.server import app as core_app
from server.llm import create_app as create_llm_app
from server.neod import create_app as create_neod_app
from server.neoo import create_app as create_neoo_app
from server.neolocal import create_app as create_neolocal_app
from server.neollm.server import app as neollm_app
from server.neodo.server import app as neodo_app

# Add the parent directory to path to import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for file operation tests."""
    test_dir = tempfile.mkdtemp()
    yield test_dir
    # Clean up after tests
    shutil.rmtree(test_dir)


@pytest.fixture
def sample_text_file(temp_dir: str) -> Generator[str, None, None]:
    """Create a sample text file for testing file operations."""
    file_path = os.path.join(temp_dir, "sample.txt")
    with open(file_path, "w") as f:
        f.write("This is a sample test file.\nIt has multiple lines.\nThird line.")
    yield file_path


@pytest.fixture
def long_running_process() -> Generator[Dict[str, Any], None, None]:
    """Start a long-running process for testing process management."""
    if sys.platform == "win32":
        cmd = "ping -t localhost"
        proc = None
    else:
        cmd = "sleep 30"
        proc = None
    
    # Use subprocess to start a process, but do it in a way that can be imported elsewhere
    # We'll implement this in the test functions
    
    yield {"command": cmd, "process": proc}
    
    # Cleanup will be handled in the tests


@contextmanager
def mock_active_sessions() -> Generator[Dict[int, Dict[str, Any]], None, None]:
    """Context manager to mock the active_sessions global variable."""
    # This is a placeholder - in actual tests, we'll need to mock the server's global state
    mock_sessions = {}
    yield mock_sessions


@contextmanager
def mock_output_queues() -> Generator[Dict[int, Any], None, None]:
    """Context manager to mock the output_queues global variable."""
    # This is a placeholder - in actual tests, we'll need to mock the server's global state
    mock_queues = {}
    yield mock_queues


@pytest.fixture
def blacklisted_commands() -> Generator[set, None, None]:
    """Fixture to provide and restore the blacklisted_commands set."""
    # This is a placeholder - in actual tests, we'll need to mock the server's global state
    original_blacklist = {'rm -rf /', 'mkfs'}
    mock_blacklist = original_blacklist.copy()
    yield mock_blacklist
    # Reset blacklist in cleanup 


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def core_client():
    """Create a test client for the Core MCP Server."""
    return TestClient(core_app)


@pytest.fixture(scope="session")
def llm_client():
    """Create a test client for the LLM MCP Server."""
    llm_app = create_llm_app()
    return TestClient(llm_app)


@pytest.fixture(scope="session")
def neod_client():
    """Create a test client for the Neo Development Server."""
    neod_app = create_neod_app()
    return TestClient(neod_app)


@pytest.fixture(scope="session")
def neoo_client():
    """Create a test client for the Neo Operations Server."""
    neoo_app = create_neoo_app()
    return TestClient(neoo_app)


@pytest.fixture(scope="session")
def neolocal_client() -> TestClient:
    """Create a test client for the NeoLocal server."""
    app = create_neolocal_app()
    return TestClient(app)


@pytest.fixture(scope="session")
def neollm_client():
    """Create a test client for the Neo Local LLM Server."""
    return TestClient(neollm_app)


@pytest.fixture(scope="session")
def neodo_client():
    """Create a test client for the Neo DO Server."""
    return TestClient(neodo_app)


@pytest.fixture(scope="session")
def all_clients(core_client, llm_client, neod_client, neoo_client, neolocal_client, neollm_client, neodo_client):
    """Return a dictionary of all test clients."""
    return {
        "core": core_client,
        "llm": llm_client,
        "neod": neod_client,
        "neoo": neoo_client,
        "neolocal": neolocal_client,
        "neollm": neollm_client,
        "neodo": neodo_client
    }


@pytest.fixture(scope="session")
def test_environment():
    """Set up test environment variables."""
    os.environ["MCP_PORT"] = "7443"
    os.environ["LLM_PORT"] = "7444"
    os.environ["NEOD_PORT"] = "7445"
    os.environ["NEOO_PORT"] = "7446"
    os.environ["NEOLOCAL_PORT"] = "7447"
    os.environ["NEOLM_PORT"] = "7448"
    os.environ["NEODO_PORT"] = "7449"
    os.environ["DO_TOKEN"] = "test_token"
    yield
    # Clean up environment variables if needed 