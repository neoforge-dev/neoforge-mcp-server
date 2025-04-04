"""
Entry point for Neo Local LLM MCP Server.
"""

import os
import sys
import uvicorn
from . import server

def main():
    """Start the Neo Local LLM MCP Server."""
    try:
        # Get port from environment or use default
        port = int(os.getenv("MCP_PORT", "7448"))
        
        # Get app instance
        app = server.server.get_app()
        
        # Start server with uvicorn
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        
    except Exception as e:
        print(f"Error starting Neo Local LLM MCP Server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 