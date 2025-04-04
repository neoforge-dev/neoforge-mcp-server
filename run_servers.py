"""
Run all MCP servers concurrently.
"""

import asyncio
import signal
import sys
import uvicorn
from server.core import app as core_app
from server.llm import app as llm_app
from server.neod import app as neod_app
from server.neoo import app as neoo_app
from server.neolocal import app as neolocal_app
from server.neollm import app as neollm_app
from server.neodo import app as neodo_app

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
    config = create_server_config(core_app, 7443)
    server = uvicorn.Server(config)
    await server.serve()

async def run_llm_server():
    """Run LLM MCP Server."""
    config = create_server_config(llm_app, 7444)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neod_server():
    """Run Neo Development MCP Server."""
    config = create_server_config(neod_app, 7445)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neoo_server():
    """Run Neo Operations MCP Server."""
    config = create_server_config(neoo_app, 7446)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neolocal_server():
    """Run Neo Local MCP Server."""
    config = create_server_config(neolocal_app, 7447)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neollm_server():
    """Run Neo Local LLM MCP Server."""
    config = create_server_config(neollm_app, 7448)
    server = uvicorn.Server(config)
    await server.serve()

async def run_neodo_server():
    """Run Neo DO MCP Server."""
    config = create_server_config(neodo_app, 7449)
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