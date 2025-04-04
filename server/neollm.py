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
from decorators import trace_tool, metrics_tool
import tiktoken

# Initialize the MCP server
mcp = FastMCP("Neo Local LLM MCP", port=7448, log_level="DEBUG")

# Initialize tracer
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "neo-local-llm-server",
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
})

# Initialize tracing if not in test mode
is_test_mode = "pytest" in sys.modules
if not is_test_mode:
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)

@mcp.tool()
@trace_tool
@metrics_tool
def generate_code(
    prompt: str,
    model: str = "claude-3-sonnet",
    system_prompt: str = None,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generate code using various models."""
    try:
        # Implementation will depend on the model being used
        if model == "claude-3-sonnet":
            # Use Anthropic's Claude
            pass
        elif model.startswith("gpt-"):
            # Use OpenAI's GPT models
            pass
        else:
            # Use local models or other providers
            pass
            
        return {
            "status": "success",
            "model": model,
            "generated_code": "# Generated code will go here"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Code generation failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def manage_llm_context(
    content: str,
    model: str = "claude-3-sonnet",
    max_tokens: int = None
) -> Dict[str, Any]:
    """Advanced LLM context management and optimization."""
    try:
        # Get encoding for the model
        if model.startswith("gpt-"):
            encoding = tiktoken.encoding_for_model(model)
        else:
            encoding = tiktoken.get_encoding("cl100k_base")  # Default to Claude's encoding
            
        # Count tokens
        token_count = len(encoding.encode(content))
        
        # Check if content needs to be truncated
        if max_tokens and token_count > max_tokens:
            # Implement smart truncation logic
            pass
            
        return {
            "status": "success",
            "token_count": token_count,
            "encoding": encoding.name,
            "truncated": token_count > max_tokens if max_tokens else False
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Context management failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def context_length(text: str) -> Dict[str, Any]:
    """Track LLM context usage."""
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

@mcp.tool()
@trace_tool
@metrics_tool
def filter_output(
    content: str,
    max_lines: int = 50,
    important_patterns: Optional[list[str]] = None
) -> Dict[str, Any]:
    """Process and format long command outputs for better LLM consumption."""
    try:
        lines = content.splitlines()
        total_lines = len(lines)
        
        if important_patterns:
            # Filter lines matching important patterns
            filtered_lines = []
            for line in lines:
                if any(pattern in line for pattern in important_patterns):
                    filtered_lines.append(line)
            lines = filtered_lines
            
        # Truncate if still too long
        if len(lines) > max_lines:
            half = max_lines // 2
            lines = lines[:half] + ["..."] + lines[-half:]
            
        return {
            "status": "success",
            "filtered_content": "\n".join(lines),
            "original_lines": total_lines,
            "filtered_lines": len(lines),
            "truncated": total_lines > max_lines
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Output filtering failed: {str(e)}"
        }

def main():
    """Start the Neo Local LLM server."""
    if not is_test_mode:
        print("Starting Neo Local LLM server...")
        mcp.run()

if __name__ == "__main__":
    main() 