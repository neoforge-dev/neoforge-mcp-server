"""
Mock server module to satisfy imports.
"""

from typing import Optional


class MCPServer:
    """Mock MCPServer class."""
    
    def __init__(self, name: str, version: Optional[str] = None):
        self.name = name
        self.version = version 