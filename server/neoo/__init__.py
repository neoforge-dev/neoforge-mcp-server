"""
Neo Operations MCP Server package.
"""

# Use the app factory pattern
from .server import create_app

# Expose the factory function
__all__ = ["create_app"] 