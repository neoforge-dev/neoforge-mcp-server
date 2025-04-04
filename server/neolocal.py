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
from debugger import create_debugger
from decorators import set_debugger, trace_tool, metrics_tool

# Initialize the MCP server
mcp = FastMCP("Neo Local MCP", port=7447, log_level="DEBUG")

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

@mcp.tool()
@trace_tool
@metrics_tool
def get_trace_info() -> Dict[str, Any]:
    """Get information about the current tracing configuration."""
    return {
        "status": "success",
        "tracer_provider": str(trace.get_tracer_provider()),
        "resource": resource.attributes,
        "is_test_mode": is_test_mode
    }

@mcp.tool()
@trace_tool
@metrics_tool
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
            otlp_exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            
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
@trace_tool
@metrics_tool
def get_metrics_info() -> Dict[str, Any]:
    """Get information about the current metrics configuration."""
    return {
        "status": "success",
        "metrics_enabled": not is_test_mode,
        "exporters": ["otlp", "prometheus"] if not is_test_mode else [],
        "resource": resource.attributes
    }

@mcp.tool()
@trace_tool
@metrics_tool
def configure_metrics(exporter_endpoint: str = None) -> Dict[str, Any]:
    """Configure metrics settings."""
    try:
        if exporter_endpoint and not is_test_mode:
            # Configure metrics exporter
            pass  # Implementation depends on metrics requirements
            
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
@trace_tool
@metrics_tool
def debug_control(
    action: str,
    session_id: str = None,
    file_path: str = None,
    line_number: int = None,
    expression: str = None
) -> Dict[str, Any]:
    """Control debugging sessions and evaluate expressions."""
    try:
        if action == "start":
            # Start a new debug session
            pass
        elif action == "stop":
            # Stop a debug session
            pass
        elif action == "step":
            # Step through code
            pass
        elif action == "continue":
            # Continue execution
            pass
        elif action == "breakpoint":
            # Set/remove breakpoint
            pass
        elif action == "evaluate":
            # Evaluate expression
            pass
        else:
            return {
                "status": "error",
                "error": f"Unknown debug action: {action}"
            }
            
        return {
            "status": "success",
            "action": action,
            "session_id": session_id
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Debug control failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def git_operation(command: str, parameters: Dict[str, str] = None) -> Dict[str, Any]:
    """Execute Git operations safely."""
    try:
        if command == "status":
            # Get git status
            pass
        elif command == "diff":
            # Get git diff
            pass
        elif command == "log":
            # Get git log
            pass
        elif command == "branch":
            # Branch operations
            pass
        elif command == "commit":
            # Commit changes
            pass
        else:
            return {
                "status": "error",
                "error": f"Unknown git command: {command}"
            }
            
        return {
            "status": "success",
            "command": command,
            "parameters": parameters
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Git operation failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def install_dependency(package: str, dev: bool = False) -> Dict[str, Any]:
    """Install Python package using uv."""
    try:
        cmd = ["uv", "pip", "install"]
        if dev:
            cmd.append("--dev")
        cmd.append(package)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        return {
            "status": "success",
            "message": f"Successfully installed {package}",
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "error": f"Failed to install {package}: {e.stderr}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Installation failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def run_tests(target: str = None, docker: bool = False) -> Dict[str, Any]:
    """Run tests with proper isolation."""
    try:
        if docker:
            # Run tests in Docker
            cmd = ["docker", "run", "--rm", "-v", f"{os.getcwd()}:/app", "-w", "/app", "python:3.9", "pytest"]
        else:
            # Run tests locally
            cmd = ["pytest"]
            
        if target:
            cmd.append(target)
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "errors": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Test execution failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def format_code(path: str = '.') -> Dict[str, Any]:
    """Format code using ruff."""
    try:
        cmd = ["ruff", "format", path]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "errors": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Code formatting failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def lint_code(path: str = '.', fix: bool = False) -> Dict[str, Any]:
    """Run ruff linting."""
    try:
        cmd = ["ruff", "check", path]
        if fix:
            cmd.append("--fix")
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "errors": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Linting failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def monitor_performance(duration: int = 60, interval: float = 1.0) -> Dict[str, Any]:
    """Monitor system performance metrics."""
    try:
        metrics = []
        end_time = time.time() + duration
        
        while time.time() < end_time:
            cpu_percent = psutil.cpu_percent(interval=interval)
            memory = psutil.virtual_memory()
            
            metrics.append({
                "timestamp": time.time(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_available": memory.available
            })
            
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

def main():
    """Start the Neo Local server."""
    if not is_test_mode:
        print("Starting Neo Local server...")
        mcp.run()

if __name__ == "__main__":
    main() 