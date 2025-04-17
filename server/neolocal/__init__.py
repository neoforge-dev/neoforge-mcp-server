"""
Neo Local MCP Server package.
"""

from .server import create_app
from .main import app

__all__ = ["create_app"] 