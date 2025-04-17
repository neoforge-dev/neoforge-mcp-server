"""
Neo Operations Server - Provides operations and infrastructure management tools.
"""

import os
import sys
import platform
import psutil
import docker
import subprocess # Added for manage_services, check_network
import shutil # Added for backup_data
import datetime # Added for backup_data
import re # Added for monitor_logs
from collections import defaultdict # Added for monitor_logs
from typing import Dict, Any, Optional, List

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
mcp = FastMCP("Neo Operations MCP", port=7446, log_level="DEBUG")

# Create and mount FastAPI app
app = FastAPI()
if "pytest" not in sys.modules:
    mcp.mount_app(app)

# Set up tracing
if not os.getenv("TEST_MODE"):
    resource = Resource(attributes={
        ResourceAttributes.SERVICE_NAME: "neo-operations-server",
        ResourceAttributes.SERVICE_VERSION: "1.0.0",
    })

    tracer_provider = TracerProvider(resource=resource)
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)

@mcp.tool()
@trace_tool
@metrics_tool
def get_system_info() -> Dict[str, Any]:
    """Get detailed system information."""
    try:
        return {
            "status": "success",
            "system": {
                "os": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
                "disk_usage": psutil.disk_usage('/').percent
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def monitor_resources(duration: int = 60, interval: int = 1) -> Dict[str, Any]:
    """Monitor system resources over time."""
    try:
        import time
        metrics = []
        start_time = time.time()

        while time.time() - start_time < duration:
            metrics.append({
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            })
            time.sleep(interval)

        return {
            "status": "success",
            "metrics": metrics,
            "duration": duration,
            "interval": interval
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def manage_docker_containers(action: str, container_id: Optional[str] = None) -> Dict[str, Any]:
    """Manage Docker containers (list, start, stop)."""
    allowed_actions = ["list", "start", "stop"]
    if action not in allowed_actions:
        return {"status": "error", "error": f"Invalid action. Allowed: {allowed_actions}"}
    if action != "list" and not container_id:
         return {"status": "error", "error": f"container_id required for action '{action}'"}

    try:
        client = docker.from_env()

        if action == "list":
            containers = client.containers.list(all=True)
            return {
                "status": "success",
                "containers": [{
                    "id": c.short_id, # Use short_id for brevity
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "none"
                } for c in containers]
            }
        elif action == "start":
            container = client.containers.get(container_id)
            container.start()
            return {"status": "success", "message": f"Container {container.short_id} ({container.name}) started"}
        elif action == "stop":
            container = client.containers.get(container_id)
            container.stop()
            return {"status": "success", "message": f"Container {container.short_id} ({container.name}) stopped"}

    except docker.errors.NotFound:
        return {"status": "error", "error": f"Container '{container_id}' not found."}
    except docker.errors.APIError as e:
         return {"status": "error", "error": f"Docker API error: {e}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def manage_services(action: str, service_name: str) -> Dict[str, Any]:
    """Manage system services (status, start, stop, restart) using systemctl."""
    if platform.system() != "Linux":
        return {"status": "error", "error": "Service management only supported on Linux via systemctl"}

    allowed_actions = ["status", "start", "stop", "restart"]
    if action not in allowed_actions:
        return {"status": "error", "error": f"Invalid action. Allowed: {allowed_actions}"}

    command = ["systemctl", action, service_name]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False # Check returncode manually
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "returncode": result.returncode
        }
    except FileNotFoundError:
        return {"status": "error", "error": "'systemctl' command not found. Is it installed and in PATH?"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def backup_data(source: str, destination: str) -> Dict[str, Any]:
    """Backup a file or directory to a specified destination with timestamp."""
    if not os.path.exists(source):
        return {"status": "error", "error": f"Source path '{source}' does not exist."}
    if not os.path.isdir(destination):
         return {"status": "error", "error": f"Destination path '{destination}' is not a valid directory."}

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.basename(source)
        backup_name = f"{base_name}_backup_{timestamp}"
        backup_path = os.path.join(destination, backup_name)

        if os.path.isdir(source):
            shutil.copytree(source, backup_path)
        else:
            # os.makedirs(os.path.dirname(backup_path), exist_ok=True) # Not needed if destination is a dir
            shutil.copy2(source, backup_path)

        return {
            "status": "success",
            "source": source,
            "backup_path": backup_path,
            "timestamp": timestamp
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def monitor_logs(log_path: str, lines: int = 100) -> Dict[str, Any]:
    """Monitor and analyze the last N lines of a log file."""
    if not os.path.isfile(log_path):
         return {"status": "error", "error": f"Log file not found: {log_path}"}

    try:
        log_entries = []
        error_count = 0
        warning_count = 0
        patterns = defaultdict(int)

        # Read last N lines efficiently (might be slow for huge files without tail)
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Simple approach for moderate files:
            all_lines = f.readlines()
            last_n_lines = all_lines[-lines:]
            # More efficient for large files (requires external command or complex seek):
            # try:
            #     result = subprocess.run(['tail', '-n', str(lines), log_path], capture_output=True, text=True, check=True)
            #     last_n_lines = result.stdout.splitlines()
            # except (FileNotFoundError, subprocess.CalledProcessError):
            #     # Fallback to reading last N lines in Python if tail fails
            #     # ... (implement complex seek/read or use the simple approach above)
            #     last_n_lines = all_lines[-lines:] # Revert to simple for now

        for line in last_n_lines:
            entry = line.strip()
            log_entries.append(entry)
            if re.search(r'error|exception|fail', entry, re.I):
                error_count += 1
            if re.search(r'warning|warn', entry, re.I):
                warning_count += 1

            # Extract common patterns (Example: IP addresses)
            ip_matches = re.findall(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', entry)
            for ip in ip_matches:
                patterns[f"IP: {ip}"] += 1

            # Example: Timestamps
            # timestamp_matches = re.findall(r'\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}', entry)
            # for ts in timestamp_matches:
            #     patterns[f"Timestamp pattern"] += 1

        return {
            "status": "success",
            "log_entries": log_entries,
            "analysis": {
                "total_lines_analyzed": len(log_entries),
                "error_count": error_count,
                "warning_count": warning_count,
                "common_patterns": dict(sorted(patterns.items(), key=lambda item: item[1], reverse=True)) # Sort patterns by count
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def check_network(target: str = "8.8.8.8", count: int = 4) -> Dict[str, Any]:
    """Check network connectivity using ping."""
    try:
        if platform.system() == "Windows":
            command = ["ping", "-n", str(count), target]
        else:
            command = ["ping", "-c", str(count), target]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10 # Add a timeout
        )

        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "target": target,
            "count": count,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Ping timed out after 10 seconds for {target}"}
    except FileNotFoundError:
         return {"status": "error", "error": "'ping' command not found. Is it installed and in PATH?"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def manage_processes(action: str, pid: Optional[int] = None) -> Dict[str, Any]:
    """Manage system processes (list, kill)."""
    allowed_actions = ["list", "kill"]
    if action not in allowed_actions:
         return {"status": "error", "error": f"Invalid action. Allowed: {allowed_actions}"}
    if action == "kill" and pid is None:
        return {"status": "error", "error": "PID required for kill action"}

    try:
        if action == "list":
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass # Process might have terminated or access denied
            return {
                "status": "success",
                "processes": sorted(processes, key=lambda p: p['cpu_percent'], reverse=True) # Sort by CPU
            }
        elif action == "kill":
            try:
                process = psutil.Process(pid)
                process.terminate() # Try graceful termination first
                # Add wait and force kill if needed
                # process.wait(timeout=1)
                # if process.is_running():
                #    process.kill()
                return {
                    "status": "success",
                    "message": f"Process {pid} terminated (attempted)"
                }
            except psutil.NoSuchProcess:
                 return {"status": "error", "error": f"Process with PID {pid} not found"}
            except psutil.AccessDenied:
                 return {"status": "error", "error": f"Permission denied to terminate process {pid}"}

    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def check_security(path: str) -> Dict[str, Any]:
    """Check security configuration and permissions (basic checks)."""
    if not os.path.exists(path):
        return {"status": "error", "error": f"Path not found: {path}"}

    try:
        security_info = {
            "path_info": {},
            "suspicious_files": []
        }
        limit = 100 # Limit number of files/dirs checked to prevent large outputs
        count = 0

        # Get info for the path itself
        stat_info = os.stat(path)
        security_info["path_info"] = {
             "permissions": oct(stat_info.st_mode)[-3:], # Get octal permissions
             "uid": stat_info.st_uid,
             "gid": stat_info.st_gid
        }

        # Check some files/dirs within if it's a directory
        if os.path.isdir(path):
            for item in os.listdir(path):
                 if count >= limit:
                     security_info["warning"] = f"Check limited to first {limit} items."
                     break
                 item_path = os.path.join(path, item)
                 try:
                     stat_info = os.stat(item_path)
                     perms = oct(stat_info.st_mode)[-3:]
                     # Example check: World-writable files/dirs
                     if perms[-1] in ['2', '3', '6', '7']:
                         security_info["suspicious_files"].append({
                             "path": item_path,
                             "permissions": perms,
                             "reason": "World-writable"
                         })
                 except Exception:
                     pass # Ignore errors for individual items
                 count += 1

        return {
            "status": "success",
            "security_info": security_info
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Remove __main__ block
# if __name__ == "__main__":
#     print("Starting Neo Operations Server on port 7446...")
#     if not os.getenv("TEST_MODE"):
#         mcp.run() 