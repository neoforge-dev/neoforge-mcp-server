"""
Neo Local LLM Server - Handles local LLM operations
"""

from mcp.server.fastmcp import FastMCP
import os
import sys
from typing import Dict, Any, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
import tiktoken

# Adjusted relative imports
from decorators import trace_tool, metrics_tool

# Added FastAPI import
from fastapi import FastAPI
from .server import NeoLocalLLMServer # Assuming server logic is in server.py

# Define a variable to hold the app, but don't initialize yet
app = None

# Remove MCP instance initialization from here
# mcp = FastMCP("Neo Local LLM MCP", port=7448, log_level="DEBUG")

# Remove global app instance
# app = FastAPI()
# if "pytest" not in sys.modules:
#     mcp.mount_app(app)

# Remove tracer initialization from here
# resource = Resource(attributes={...})
# ... tracer setup ...

# Define the factory function
def create_app(config: Optional[Dict] = None, server_instance: Optional[NeoLocalLLMServer] = None) -> FastAPI:
    """Factory function to create the NeoLocalLLM FastAPI app."""
    global app
    
    # If app already created, return it (singleton pattern)
    if app is not None:
        return app
    
    # Initialize the specific server instance (passing config if needed)
    if server_instance is None:
        # If no instance provided (e.g., in production), create one
        # It should load its own config internally via BaseServer
        server = NeoLocalLLMServer() 
    else:
        # Use the provided instance (e.g., from tests with mocks)
        server = server_instance

    # Get the FastAPI app from the server instance
    app = server.get_app()

    # Register tools/routes from the server instance
    # The @mcp.tool decorator in the original file relies on a global mcp instance.
    # This needs to be shifted to registration on the server instance.
    # Assuming NeoLocalLLMServer class handles route registration (e.g., in its __init__ or a setup method)
    # server.register_routes(app) # Or however registration is handled

    # Add tool routes defined in *this* file to the app
    # These would ideally move into the NeoLocalLLMServer class
    # For now, manually add them to the app instance created by the server
    @app.post("/tools/generate_code", tags=["Tools"], response_model=Dict[str, Any])
    async def _generate_code(payload: Dict[str, Any]):
        return generate_code(**payload)

    @app.post("/tools/manage_llm_context", tags=["Tools"], response_model=Dict[str, Any])
    async def _manage_llm_context(payload: Dict[str, Any]):
        return manage_llm_context(**payload)

    @app.post("/tools/context_length", tags=["Tools"], response_model=Dict[str, Any])
    async def _context_length(payload: Dict[str, Any]):
        return context_length(**payload)

    @app.post("/tools/filter_output", tags=["Tools"], response_model=Dict[str, Any])
    async def _filter_output(payload: Dict[str, Any]):
        return filter_output(**payload)

    return app


# Tool functions remain, but decorators won't work without a global MCP instance
# @mcp.tool()
# @trace_tool
# @metrics_tool
def generate_code(
    prompt: str,
    model: str = "claude-3-sonnet",
    system_prompt: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generate code using various models."""
    # Placeholder implementation
    try:
        # Actual implementation would call the appropriate LLM API/library
        # based on the model parameter
        generated_code = f"# Mock code generated for model {model}\nprint('Hello from {model}!')"

        return {
            "status": "success",
            "model": model,
            "generated_code": generated_code
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Code generation failed: {str(e)}"
        }

# @mcp.tool()
# @trace_tool
# @metrics_tool
def manage_llm_context(
    content: str,
    model: str = "claude-3-sonnet",
    max_tokens: int = None
) -> Dict[str, Any]:
    """Advanced LLM context management and optimization using tiktoken."""
    try:
        # Get encoding for the model
        try:
            if model.startswith("gpt-") or model == "text-embedding-ada-002": # Add known OpenAI models
                encoding = tiktoken.encoding_for_model(model)
            else:
                 # Default for others like Claude or fallback
                encoding = tiktoken.get_encoding("cl100k_base")
        except KeyError:
            # Fallback if model name is unknown to tiktoken
            encoding = tiktoken.get_encoding("cl100k_base")
            print(f"Warning: Model '{model}' not found in tiktoken, using cl100k_base encoding.")

        # Count tokens
        tokens = encoding.encode(content)
        token_count = len(tokens)

        # Check if content needs to be truncated (simple truncation for now)
        truncated = False
        final_content = content
        if max_tokens and token_count > max_tokens:
            truncated_tokens = tokens[:max_tokens]
            final_content = encoding.decode(truncated_tokens)
            token_count = len(truncated_tokens)
            truncated = True

        return {
            "status": "success",
            "token_count": token_count,
            "encoding": encoding.name,
            "truncated": truncated,
            # Optionally return truncated content if needed by caller
            # "final_content": final_content
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Context management failed: {str(e)}"
        }

# @mcp.tool()
# @trace_tool
# @metrics_tool
def context_length(text: str) -> Dict[str, Any]:
    """Estimate token count for text using cl100k_base encoding."""
    try:
        # Use cl100k_base as default encoding
        encoding = tiktoken.get_encoding("cl100k_base")
        token_count = len(encoding.encode(text))

        return {
            "status": "success",
            "token_count": token_count,
            "encoding": "cl100k_base"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Token counting failed: {str(e)}"
        }

# @mcp.tool()
# @trace_tool
# @metrics_tool
def filter_output(
    content: str,
    max_lines: int = 50,
    important_patterns: Optional[list[str]] = None
) -> Dict[str, Any]:
    """Process and format long command outputs for better LLM consumption."""
    try:
        lines = content.splitlines()
        total_lines = len(lines)
        filtered_lines = lines

        if important_patterns:
            # Filter lines matching important patterns
            matched_lines = []
            for line in filtered_lines:
                if any(pattern in line for pattern in important_patterns):
                    matched_lines.append(line)
            filtered_lines = matched_lines # Keep only matching lines if patterns provided

        # Truncate if still too long
        truncated = False
        if len(filtered_lines) > max_lines:
            half = max_lines // 2
            # Ensure half isn't 0 if max_lines is 1
            if max_lines == 1:
                filtered_lines = filtered_lines[:1]
            elif half > 0:
                 filtered_lines = filtered_lines[:half] + ["..."] + filtered_lines[-half:]
            else: # max_lines is 0
                 filtered_lines = []
            truncated = True

        return {
            "status": "success",
            "filtered_content": "\n".join(filtered_lines),
            "original_lines": total_lines,
            "filtered_lines": len(filtered_lines),
            "truncated": truncated
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Output filtering failed: {str(e)}"
        }

# Remove main block
# def main():
#     """Start the Neo Local LLM server."""
#     if not is_test_mode:
#         print("Starting Neo Local LLM server...")
#         mcp.run()
#
# if __name__ == "__main__":
#     main() 