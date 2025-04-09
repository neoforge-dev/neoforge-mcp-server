"""
LLM MCP Server package.
"""

# Use the app factory pattern
from .server import create_app

# You might expose the server class too if needed
# from .server import LLMServer

# Create the app instance here if needed by other modules immediately,
# otherwise, let consumers call create_app()
# app = create_app()

# Adjust __all__ accordingly
__all__ = ["create_app"] # Or expose 'app' if created above 