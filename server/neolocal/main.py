"""
Neo Local Server - Handles local file operations and system tools
"""

from mcp.server.fastmcp import FastMCP
import os
import platform
import subprocess
import shlex
import time
import signal
import re
import glob
import stat
import shutil
import threading
import queue
import json
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import socket
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
import psutil
import sys

# Adjusted relative imports - Use absolute imports
# from ...debugger import create_debugger
# from ...decorators import set_debugger, trace_tool, metrics_tool
from debugger import create_debugger
from decorators import set_debugger, trace_tool, metrics_tool

# Added FastAPI import
from fastapi import FastAPI

# Initialize the MCP server
mcp = FastMCP("Neo Local MCP", port=7447, log_level="DEBUG")

# Create and mount FastAPI app
app = FastAPI()
if "pytest" not in sys.modules:
    mcp.mount_app(app)


# Initialize tracer
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "neo-local-server",
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
})

# Initialize tracing if not in test mode
is_test_mode = "pytest" in sys.modules
if not is_test_mode:
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)
    # Configure exporter (example)
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
else:
    # Mock tracer if in test mode
    class MockTracer:
        def start_as_current_span(self, *args, **kwargs):
            class MockSpan:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def set_attribute(self, *args): pass
                def record_exception(self, *args): pass
            return MockSpan()
    tracer = MockTracer()


# Apply decorators if not already applied by the import
# (Assuming trace_tool and metrics_tool handle tracer/meter initialization internally
#  or rely on global setup elsewhere if not testing)

@mcp.tool()
# @trace_tool # Assuming trace_tool is applied via import from decorators
# @metrics_tool # Assuming metrics_tool is applied via import from decorators
def get_trace_info() -> Dict[str, Any]:
    """Get information about the current tracing configuration."""
    provider = trace.get_tracer_provider()
    return {
        "status": "success",
        "tracer_provider": str(provider),
        "resource": provider.resource.attributes if hasattr(provider, 'resource') else {},
        "is_test_mode": is_test_mode
    }

@mcp.tool()
# @trace_tool
# @metrics_tool
def configure_tracing(
    exporter_endpoint: str = None,
    service_name: str = None,
    service_version: str = None
) -> Dict[str, Any]:
    """Configure tracing settings."""
    global resource
    try:
        if service_name or service_version:
            attrs = {
                ResourceAttributes.SERVICE_NAME: service_name or "neo-local-server",
                ResourceAttributes.SERVICE_VERSION: service_version or "1.0.0"
            }
            resource = Resource(attributes=attrs)

        if exporter_endpoint and not is_test_mode:
            provider = trace.get_tracer_provider()
            # Check if provider is already configured, might need re-initialization
            # For simplicity, assume adding a new processor is okay
            otlp_exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)

        return {
            "status": "success",
            "message": "Tracing configuration updated",
            "config": {
                "exporter_endpoint": exporter_endpoint,
                "service_name": service_name,
                "service_version": service_version
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to configure tracing: {str(e)}"
        }

@mcp.tool()
# @trace_tool
# @metrics_tool
def get_metrics_info() -> Dict[str, Any]:
    """Get information about the current metrics configuration."""
    # Placeholder - Actual implementation depends on the metrics setup
    return {
        "status": "success",
        "metrics_enabled": not is_test_mode,
        "exporters": ["otlp", "prometheus"] if not is_test_mode else [],
        # "resource": resource.attributes # Add if metrics uses the same resource
    }

@mcp.tool()
# @trace_tool
# @metrics_tool
def configure_metrics(exporter_endpoint: str = None) -> Dict[str, Any]:
    """Configure metrics settings."""
    # Placeholder - Actual implementation depends on the metrics setup
    try:
        if exporter_endpoint and not is_test_mode:
            # Configure metrics exporter (e.g., OTLPMetricExporter)
            pass

        return {
            "status": "success",
            "message": "Metrics configuration updated",
            "config": {
                "exporter_endpoint": exporter_endpoint
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to configure metrics: {str(e)}"
        }

@mcp.tool()
# @trace_tool
# @metrics_tool
def debug_control(
    action: str,
    session_id: str = None,
    file_path: str = None,
    line_number: int = None,
    expression: str = None
) -> Dict[str, Any]:
    """Control debugging sessions and evaluate expressions."""
    # Placeholder - Requires actual debugger implementation (e.g., using PDB)
    try:
        # Implementation using debugger module would go here
        # dbg = create_debugger()
        # result = dbg.control(action, session_id, ...)
        allowed_actions = ["start", "stop", "step", "continue", "breakpoint", "evaluate"]
        if action not in allowed_actions:
            return {"status": "error", "error": f"Unknown debug action: {action}"}

        # Mock response for now
        return {
            "status": "success",
            "action": action,
            "session_id": session_id,
            "message": f"Debug action '{action}' processed (placeholder)."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Debug control failed: {str(e)}"
        }

@mcp.tool()
# @trace_tool
# @metrics_tool
def git_operation(command: str, parameters: Dict[str, str] = None) -> Dict[str, Any]:
    """Execute Git operations safely."""
    # Placeholder - Requires robust implementation using subprocess
    try:
        allowed_commands = ["status", "diff", "log", "branch", "commit"]
        if command not in allowed_commands:
             return {"status": "error", "error": f"Unknown git command: {command}"}

        # Mock response
        return {
            "status": "success",
            "command": command,
            "parameters": parameters,
            "message": f"Git command '{command}' processed (placeholder)."

        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Git operation failed: {str(e)}"
        }

@mcp.tool()
# @trace_tool
# @metrics_tool
def install_dependency(package: str, dev: bool = False) -> Dict[str, Any]:
    """Install Python package using uv."""
    try:
        # Assuming uv is installed and in PATH
        cmd = ["uv", "pip", "install"]
        # uv doesn't have a direct --dev flag like poetry/pip-tools for install
        # Dependency groups are managed in pyproject.toml
        # This tool might need rethinking depending on project structure
        # If using requirements files:
        # req_file = "requirements-dev.txt" if dev else "requirements.txt"
        # cmd.extend(["-r", req_file]) # or install a specific package
        cmd.append(package)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False # Check return code manually
        )

        if result.returncode != 0:
             return {
                 "status": "error",
                 "error": f"Failed to install {package}. Return code: {result.returncode}",
                 "stderr": result.stderr
             }

        return {
            "status": "success",
            "message": f"Successfully installed/updated {package}",
            "output": result.stdout
        }
    except FileNotFoundError:
         return {"status": "error", "error": "'uv' command not found. Is it installed?"}
    except Exception as e:
        return {
            "status": "error",
            "error": f"Installation failed: {str(e)}"
        }

@mcp.tool()
# @trace_tool
# @metrics_tool
def run_tests(target: str = None, docker: bool = False) -> Dict[str, Any]:
    """Run tests with proper isolation."""
    # Placeholder - Needs robust implementation
    try:
        cmd = []
        if docker:
            # Basic example, needs refinement (volume mounts, image name etc.)
            cmd = ["docker", "run", "--rm", "my-python-test-image", "pytest"]
        else:
            cmd = ["pytest"]

        if target:
            cmd.append(target)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check = False
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "errors": result.stderr if result.returncode != 0 else None,
            "returncode": result.returncode
        }
    except FileNotFoundError:
        tool = "docker" if docker else "pytest"
        return {"status": "error", "error": f"Command '{tool}' not found."}
    except Exception as e:
        return {
            "status": "error",
            "error": f"Test execution failed: {str(e)}"
        }

@mcp.tool()
# @trace_tool
# @metrics_tool
def format_code(path: str = '.') -> Dict[str, Any]:
    """Format code using ruff."""
    try:
        cmd = ["ruff", "format", path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check = False
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "errors": result.stderr if result.returncode != 0 else None,
            "returncode": result.returncode
        }
    except FileNotFoundError:
        return {"status": "error", "error": "Command 'ruff' not found."}
    except Exception as e:
        return {
            "status": "error",
            "error": f"Code formatting failed: {str(e)}"
        }

@mcp.tool()
# @trace_tool
# @metrics_tool
def lint_code(path: str = '.', fix: bool = False) -> Dict[str, Any]:
    """Run ruff linting."""
    try:
        cmd = ["ruff", "check", path]
        if fix:
            cmd.append("--fix")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check = False
        )

        return {
            # Ruff check returns 1 if issues found, 0 if clean, 2 for error
            "status": "success" if result.returncode == 0 else ("warning" if result.returncode == 1 else "error"),
            "output": result.stdout,
            "errors": result.stderr if result.returncode > 1 else None,
             "returncode": result.returncode
        }
    except FileNotFoundError:
        return {"status": "error", "error": "Command 'ruff' not found."}
    except Exception as e:
        return {
            "status": "error",
            "error": f"Linting failed: {str(e)}"
        }

@mcp.tool()
# @trace_tool
# @metrics_tool
def monitor_performance(duration: int = 60, interval: float = 1.0) -> Dict[str, Any]:
    """Monitor system performance metrics."""
    # This duplicates functionality likely present in neoo server.
    # Consider consolidating or specializing.
    try:
        metrics = []
        end_time = time.time() + duration

        while time.time() < end_time:
            cpu_percent = psutil.cpu_percent(interval=None) # Get instantaneous CPU % since last call or interval=0
            memory = psutil.virtual_memory()

            metrics.append({
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_available": memory.available
            })
            time.sleep(interval)

        return {
            "status": "success",
            "duration": duration,
            "interval": interval,
            "metrics": metrics
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Performance monitoring failed: {str(e)}"
        }

# Remove main block as server is run by run_servers.py
# def main():
#     """Start the Neo Local server."""
#     if not is_test_mode:
#         print("Starting Neo Local server...")
#         mcp.run()
#
# if __name__ == "__main__":
#     main() 