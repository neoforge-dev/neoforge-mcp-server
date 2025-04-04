"""
Neo Development Server - Provides development tools and workspace management.
"""

import os
import sys
import platform
from typing import Dict, Any, Optional
from trace import TracerProvider, BatchSpanProcessor, OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
from fastmcp import FastMCP
from server.utils.trace_tool import trace_tool
from server.utils.metrics_tool import metrics_tool

# Initialize MCP server
mcp = FastMCP("Neo Development MCP", port=7445, log_level="DEBUG")

# Set up tracing
if not os.getenv("TEST_MODE"):
    resource = Resource(attributes={
        ResourceAttributes.SERVICE_NAME: "neo-development-server",
        ResourceAttributes.SERVICE_VERSION: "1.0.0",
    })

    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

@mcp.tool()
@trace_tool
@metrics_tool
def get_workspace_info() -> Dict[str, Any]:
    """Get information about the current workspace."""
    try:
        return {
            "status": "success",
            "workspace": {
                "path": os.getcwd(),
                "os": platform.system(),
                "python_version": sys.version,
                "environment": os.environ.get("VIRTUAL_ENV", "system")
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def setup_workspace(path: str, venv: bool = True) -> Dict[str, Any]:
    """Set up a new workspace with optional virtual environment."""
    try:
        os.makedirs(path, exist_ok=True)
        if venv:
            import venv
            venv.create(path, with_pip=True)
        return {
            "status": "success",
            "workspace": path,
            "venv": venv
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def build_project(path: str, build_command: str) -> Dict[str, Any]:
    """Build a project using the specified command."""
    try:
        import subprocess
        result = subprocess.run(
            build_command,
            shell=True,
            cwd=path,
            capture_output=True,
            text=True
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def analyze_dependencies(path: str) -> Dict[str, Any]:
    """Analyze project dependencies."""
    try:
        import pkg_resources
        dependencies = {}
        if os.path.exists(os.path.join(path, "requirements.txt")):
            with open(os.path.join(path, "requirements.txt")) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        try:
                            req = pkg_resources.Requirement.parse(line)
                            dependencies[req.name] = str(req.specifier)
                        except:
                            pass
        return {
            "status": "success",
            "dependencies": dependencies
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def run_development_server(path: str, command: str, port: int) -> Dict[str, Any]:
    """Run a development server."""
    try:
        import subprocess
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return {
            "status": "success",
            "pid": process.pid,
            "port": port
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def run_tests(path: str, test_command: str = "pytest") -> Dict[str, Any]:
    """Run project tests."""
    try:
        import subprocess
        result = subprocess.run(
            test_command,
            shell=True,
            cwd=path,
            capture_output=True,
            text=True
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def generate_documentation(path: str, output_format: str = "html") -> Dict[str, Any]:
    """Generate project documentation."""
    try:
        import subprocess
        if output_format == "html":
            command = "pdoc --html --output-dir docs ."
        else:
            command = "pdoc --output-dir docs ."
        
        result = subprocess.run(
            command,
            shell=True,
            cwd=path,
            capture_output=True,
            text=True
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "docs_path": os.path.join(path, "docs")
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def check_code_quality(path: str) -> Dict[str, Any]:
    """Check code quality using various tools."""
    try:
        import subprocess
        results = {}
        
        # Run flake8
        flake8_result = subprocess.run(
            "flake8 .",
            shell=True,
            cwd=path,
            capture_output=True,
            text=True
        )
        results["flake8"] = {
            "status": "success" if flake8_result.returncode == 0 else "error",
            "output": flake8_result.stdout
        }
        
        # Run mypy
        mypy_result = subprocess.run(
            "mypy .",
            shell=True,
            cwd=path,
            capture_output=True,
            text=True
        )
        results["mypy"] = {
            "status": "success" if mypy_result.returncode == 0 else "error",
            "output": mypy_result.stdout
        }
        
        # Run bandit
        bandit_result = subprocess.run(
            "bandit -r .",
            shell=True,
            cwd=path,
            capture_output=True,
            text=True
        )
        results["bandit"] = {
            "status": "success" if bandit_result.returncode == 0 else "error",
            "output": bandit_result.stdout
        }
        
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def manage_git_workflow(path: str, action: str, **kwargs) -> Dict[str, Any]:
    """Manage Git workflow operations."""
    try:
        import subprocess
        result = None
        
        if action == "status":
            result = subprocess.run(
                "git status",
                shell=True,
                cwd=path,
                capture_output=True,
                text=True
            )
        elif action == "commit":
            message = kwargs.get("message", "Update")
            result = subprocess.run(
                f'git commit -m "{message}"',
                shell=True,
                cwd=path,
                capture_output=True,
                text=True
            )
        elif action == "push":
            result = subprocess.run(
                "git push",
                shell=True,
                cwd=path,
                capture_output=True,
                text=True
            )
        elif action == "pull":
            result = subprocess.run(
                "git pull",
                shell=True,
                cwd=path,
                capture_output=True,
                text=True
            )
        
        if result:
            return {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr
            }
        else:
            return {"status": "error", "error": "Invalid action"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("Starting Neo Development Server on port 7445...")
    if not os.getenv("TEST_MODE"):
        mcp.run() 