"""
Neo Local LLM MCP Server package.
"""

# Remove old imports
# from . import server
# from .server import app
# from .main import app

# Import only the factory function
from .main import create_app

# Do NOT automatically create app instance
# Instead, provide a function to get the app when needed
def get_app():
    """Get the app instance, initializing it only when needed."""
    from .main import app
    return app

# Export the factory function and app accessor
__all__ = ["create_app", "get_app"] 