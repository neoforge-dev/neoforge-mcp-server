"""
Mock decorators module to satisfy imports.
"""

from functools import wraps
from typing import Callable, Any, Optional


def mcp_tool(description: Optional[str] = None, **kwargs: Any) -> Callable:
    """Decorator for MCP tool methods (mock implementation)."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        
        # Add metadata to the function
        wrapper.__mcp_tool__ = True
        wrapper.__description__ = description
        
        return wrapper
    return decorator 