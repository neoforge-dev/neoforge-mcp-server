"""
Neo DO MCP Server package.
"""

# from .main import app
from .main import create_app # Import the factory function

__all__ = ["create_app"] # Export the factory function 