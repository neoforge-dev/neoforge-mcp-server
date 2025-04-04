#!/usr/bin/env python3
import os
import sys
import pytest
import asyncio
from pathlib import Path

def main():
    """Run integration tests with proper configuration."""
    # Add the project root to the Python path
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # Set up test environment variables
    os.environ["MCP_PORT"] = "7443"
    os.environ["LLM_PORT"] = "7444"
    os.environ["NEOD_PORT"] = "7445"
    os.environ["NEOO_PORT"] = "7446"
    os.environ["NEOLOCAL_PORT"] = "7447"
    os.environ["NEOLM_PORT"] = "7448"
    os.environ["NEODO_PORT"] = "7449"
    os.environ["DO_TOKEN"] = "test_token"

    # Configure pytest
    pytest_args = [
        "-v",  # Verbose output
        "--tb=short",  # Shorter traceback format
        "--showlocals",  # Show local variables in failures
        "--maxfail=3",  # Stop after 3 failures
        "--no-header",  # Remove pytest header
        "--cov=server",  # Coverage for server package
        "--cov-report=term-missing",  # Show missing lines in coverage
        "--cov-report=html",  # Generate HTML coverage report
        "test_server_integration.py",  # Run integration tests
    ]

    # Run pytest
    exit_code = pytest.main(pytest_args)
    sys.exit(exit_code)

if __name__ == "__main__":
    main() 