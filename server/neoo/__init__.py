"""
Neo Operations MCP Server package.
"""

# Use the app factory pattern
from .server import create_app
from .main import app

# Expose the factory function
__all__ = ["create_app"] 