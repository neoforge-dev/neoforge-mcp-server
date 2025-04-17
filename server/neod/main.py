"""
Neo Development Server - Provides development tools and workspace management.
"""

import os
import sys
import platform
import subprocess # Added for run functions
import shlex # Added import
from typing import Dict, Any, Optional

# Corrected opentelemetry imports
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps

# Corrected FastMCP import
from mcp.server.fastmcp import FastMCP

# Adjusted utils imports - Use absolute imports
from decorators import trace_tool, metrics_tool

# Added FastAPI import
from fastapi import FastAPI

# Initialize MCP server
mcp = FastMCP("Neo Development MCP", port=7445, log_level="DEBUG")

# Create and mount FastAPI app
app = FastAPI()
if "pytest" not in sys.modules:
    mcp.mount_app(app)

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
            venv.create(os.path.join(path, ".venv"), with_pip=True) # Create .venv inside path
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
        result = subprocess.run(
            build_command,
            shell=True,
            cwd=path,
            capture_output=True,
            text=True,
            check=False # Don't raise exception on non-zero exit code
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
    """Analyze project dependencies from requirements.txt."""
    dependencies = {}
    req_file = os.path.join(path, "requirements.txt")
    if not os.path.exists(req_file):
        return {"status": "error", "error": "requirements.txt not found"}

    try:
        import pkg_resources
        with open(req_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        # Handle different formats like package>=1.0,<2.0 or package==1.0
                        req = pkg_resources.Requirement.parse(line)
                        dependencies[req.name] = str(req.specifier) if req.specifier else "any"
                    except ValueError:
                        # Handle cases like git+https://... or local paths if needed
                        # For now, just note the line could not be parsed traditionally
                        if "==" in line:
                           name, version = line.split("==", 1)
                           dependencies[name.strip()] = version.strip()
                        elif ">=" in line:
                            name, version = line.split(">=", 1)
                            dependencies[name.strip()] = f">={version.strip()}"
                        elif ">" in line:
                            name, version = line.split(">", 1)
                            dependencies[name.strip()] = f">{version.strip()}"
                        elif "<=" in line:
                            name, version = line.split("<=", 1)
                            dependencies[name.strip()] = f"<={version.strip()}"
                        elif "<" in line:
                             name, version = line.split("<", 1)
                             dependencies[name.strip()] = f"<{version.strip()}"
                        else:
                            dependencies[line] = "unknown format"
        return {
            "status": "success",
            "dependencies": dependencies
        }
    except ImportError:
         return {"status": "error", "error": "pkg_resources not found. Install setuptools."}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def run_development_server(path: str, command: str, port: int) -> Dict[str, Any]:
    """Run a development server as a background process."""
    try:
        # Use Popen for background execution
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True # Start in new session to detach
        )
        # Note: This returns immediately, process runs in background.
        # We might need a way to manage/monitor this process later.
        return {
            "status": "success",
            "pid": process.pid,
            "port": port,
            "message": f"Development server started with PID {process.pid} on port {port}"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def run_tests(path: str, test_command: str = "pytest") -> Dict[str, Any]:
    """Run project tests."""
    try:
        result = subprocess.run(
            test_command,
            shell=True,
            cwd=path,
            capture_output=True,
            text=True,
            check=False
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
    """Generate project documentation using pdoc."""
    docs_dir = os.path.join(path, "docs")
    try:
        if output_format == "html":
            command = f"pdoc --html --output-dir {shlex.quote(docs_dir)} ."
        else:
             # Assuming markdown or other text format
            command = f"pdoc --output-dir {shlex.quote(docs_dir)} ."

        result = subprocess.run(
            command,
            shell=True,
            cwd=path,
            capture_output=True,
            text=True,
            check=False
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "docs_path": docs_dir,
            "returncode": result.returncode
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def check_code_quality(path: str) -> Dict[str, Any]:
    """Check code quality using flake8, mypy, and bandit."""
    results = {}
    tools = {"flake8": "flake8 .", "mypy": "mypy .", "bandit": "bandit -r ."}
    overall_status = "success"

    for tool, command in tools.items():
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=path,
                capture_output=True,
                text=True,
                check=False
            )
            tool_status = "success" if result.returncode == 0 else "error"
            results[tool] = {
                "status": tool_status,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
            if tool_status == "error":
                overall_status = "error"
        except FileNotFoundError:
             results[tool] = {"status": "error", "error": f"Tool '{tool}' not found. Is it installed?"}
             overall_status = "error"
        except Exception as e:
            results[tool] = {"status": "error", "error": str(e)}
            overall_status = "error"

    return {
        "status": overall_status,
        "results": results
    }

@mcp.tool()
@trace_tool
@metrics_tool
def manage_git_workflow(path: str, action: str, **kwargs) -> Dict[str, Any]:
    """Manage Git workflow operations (status, commit, push, pull)."""
    allowed_actions = ["status", "commit", "push", "pull"]
    if action not in allowed_actions:
        return {"status": "error", "error": f"Invalid action: {action}. Allowed actions: {', '.join(allowed_actions)}"}

    command = ["git"]
    if action == "status":
        command.append("status")
    elif action == "commit":
        message = kwargs.get("message", "Automated commit")
        # Consider adding specific files 'git add .' or 'git add <file>' before commit
        # For now, assuming files are staged manually or using 'git add .'
        command.extend(["commit", "-m", message])
    elif action == "push":
        command.append("push")
    elif action == "pull":
        command.append("pull")

    try:
        result = subprocess.run(
            command,
            cwd=path,
            capture_output=True,
            text=True,
            check=False
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
             "returncode": result.returncode
        }
    except FileNotFoundError:
         return {"status": "error", "error": "'git' command not found. Is Git installed and in PATH?"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Remove the __main__ block as this is now a module run via run_servers.py
# if __name__ == "__main__":
#     print("Starting Neo Development Server on port 7445...")
#     if not os.getenv("TEST_MODE"):
#         mcp.run() 