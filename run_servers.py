"""
Script to run both MCP servers (core and LLM).
"""

import multiprocessing
import uvicorn
import os
import signal
import sys

def run_core_server():
    """Run the core MCP server on port 7443."""
    from server.core import mcp
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=7443)

def run_llm_server():
    """Run the LLM MCP server on port 7444."""
    from server.llm import mcp
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=7444)

def signal_handler(signum, frame):
    """Handle termination signals."""
    print("\nShutting down servers...")
    sys.exit(0)

if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start servers in separate processes
    core_process = multiprocessing.Process(target=run_core_server)
    llm_process = multiprocessing.Process(target=run_llm_server)

    try:
        print("Starting Core MCP server on port 7443...")
        core_process.start()

        print("Starting LLM MCP server on port 7444...")
        llm_process.start()

        # Wait for processes to complete
        core_process.join()
        llm_process.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
    finally:
        # Clean up processes
        core_process.terminate()
        llm_process.terminate()
        core_process.join()
        llm_process.join() 