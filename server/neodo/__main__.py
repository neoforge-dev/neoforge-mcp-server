"""
Entry point for Neo DO MCP Server.
"""

import os
import sys
from . import server

def main():
    """Start the Neo DO MCP Server."""
    try:
        # Get port from environment or use default
        port = int(os.getenv("MCP_PORT", "7449"))
        
        # Start server
        server.app.run(host="0.0.0.0", port=port)
        
    except Exception as e:
        print(f"Error starting Neo DO MCP Server: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 