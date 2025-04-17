"""
Run all MCP servers concurrently.
"""

import asyncio
import signal
import sys
import uvicorn
from server.utils.config import ServerConfig
from server.core import create_app as create_core_app
from server.llm import create_app as create_llm_app
from server.neod import create_app as create_neod_app
from server.neoo import create_app as create_neoo_app
from server.neolocal import create_app as create_neolocal_app
from server.neollm.main import create_app as create_neollm_app
from server.neodo import create_app as create_neodo_app

def create_server_config(app, port: int, workers: int = 4) -> uvicorn.Config:
    """Create uvicorn server configuration.
    
    Args:
        app: FastAPI application
        port: Port to listen on
        workers: Number of worker processes
        
    Returns:
        uvicorn.Config instance
    """
    return uvicorn.Config(
        app,
        host="0.0.0.0",
        port=port,
        workers=workers,
        log_level="info"
    )

async def run_core_server():
    """Run Core MCP Server."""
    config = create_server_config(create_core_app(), 7443)
    server = uvicorn.Server(config)
    await server.serve()

async def run_llm_server():
    """Run LLM MCP Server."""
    config = create_server_config(create_llm_app(), 7444)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neod_server():
    """Run Neo Development MCP Server."""
    config = create_server_config(create_neod_app(), 7445)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neoo_server():
    """Run Neo Operations MCP Server."""
    config = create_server_config(create_neoo_app(), 7446)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neolocal_server():
    """Run Neo Local MCP Server."""
    config = create_server_config(create_neolocal_app(), 7447)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neollm_server():
    """Run Neo Local LLM MCP Server."""
    config = create_server_config(create_neollm_app(), 7448)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neodo_server():
    """Run Neo DO MCP Server."""
    app = create_neodo_app()
    config = create_server_config(app, 7449)
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    """Run all servers concurrently."""
    # Create tasks for each server
    tasks = [
        run_core_server(),
        run_llm_server(),
        run_neod_server(),
        run_neoo_server(),
        run_neolocal_server(),
        run_neollm_server(),
        run_neodo_server()
    ]
    
    # Run all servers concurrently
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("\nShutting down servers...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run the servers
    asyncio.run(main()) 