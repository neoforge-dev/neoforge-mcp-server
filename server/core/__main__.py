"""
Entry point for Core MCP Server.
"""

import os
import sys
from .server import server

def main():
    """Start the Core MCP Server."""
    try:
        # Get port from environment or use default
        port = int(os.getenv("MCP_PORT", "7443"))
        
        print(f"Starting Core MCP Server on port {port}...")
        server.run(port=port)
        
    except Exception as e:
        print(f"Failed to start server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 