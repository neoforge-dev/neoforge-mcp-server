"""
Neo Operations Server - Provides operations and infrastructure management tools.
"""

import os
import sys
import platform
import psutil
import docker
from typing import Dict, Any, Optional, List
from trace import TracerProvider, BatchSpanProcessor, OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
from fastmcp import FastMCP
from server.utils.trace_tool import trace_tool
from server.utils.metrics_tool import metrics_tool

# Initialize MCP server
mcp = FastMCP("Neo Operations MCP", port=7446, log_level="DEBUG")

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
    """Manage Docker containers."""
    try:
        client = docker.from_env()
        
        if action == "list":
            containers = client.containers.list(all=True)
            return {
                "status": "success",
                "containers": [{
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image.tags[0] if c.image.tags else "none"
                } for c in containers]
            }
        elif action == "start" and container_id:
            container = client.containers.get(container_id)
            container.start()
            return {"status": "success", "message": f"Container {container_id} started"}
        elif action == "stop" and container_id:
            container = client.containers.get(container_id)
            container.stop()
            return {"status": "success", "message": f"Container {container_id} stopped"}
        else:
            return {"status": "error", "error": "Invalid action or missing container_id"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def manage_services(action: str, service_name: str) -> Dict[str, Any]:
    """Manage system services."""
    try:
        import subprocess
        if platform.system() == "Linux":
            if action == "status":
                result = subprocess.run(
                    f"systemctl status {service_name}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
            elif action in ["start", "stop", "restart"]:
                result = subprocess.run(
                    f"systemctl {action} {service_name}",
                    shell=True,
                    capture_output=True,
                    text=True
                )
            else:
                return {"status": "error", "error": "Invalid action"}
                
            return {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr
            }
        else:
            return {"status": "error", "error": "Service management only supported on Linux"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def backup_data(source: str, destination: str) -> Dict[str, Any]:
    """Backup data to specified destination."""
    try:
        import shutil
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{destination}/backup_{timestamp}"
        
        if os.path.isdir(source):
            shutil.copytree(source, backup_path)
        else:
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
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
    """Monitor and analyze log files."""
    try:
        import re
        from collections import defaultdict
        
        log_entries = []
        error_count = 0
        warning_count = 0
        patterns = defaultdict(int)
        
        with open(log_path, 'r') as f:
            for line in f.readlines()[-lines:]:
                log_entries.append(line.strip())
                if re.search(r'error|exception|fail', line, re.I):
                    error_count += 1
                if re.search(r'warning|warn', line, re.I):
                    warning_count += 1
                    
                # Extract common patterns
                ip_matches = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line)
                for ip in ip_matches:
                    patterns[f"IP: {ip}"] += 1
                    
                timestamp_matches = re.findall(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line)
                for ts in timestamp_matches:
                    patterns[f"Timestamp: {ts}"] += 1
                
        return {
            "status": "success",
            "log_entries": log_entries,
            "analysis": {
                "total_lines": len(log_entries),
                "error_count": error_count,
                "warning_count": warning_count,
                "common_patterns": dict(patterns)
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def check_network(target: str = "8.8.8.8", count: int = 4) -> Dict[str, Any]:
    """Check network connectivity."""
    try:
        import subprocess
        
        if platform.system() == "Windows":
            command = f"ping -n {count} {target}"
        else:
            command = f"ping -c {count} {target}"
            
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr,
            "target": target,
            "count": count
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def manage_processes(action: str, pid: Optional[int] = None) -> Dict[str, Any]:
    """Manage system processes."""
    try:
        if action == "list":
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return {
                "status": "success",
                "processes": processes
            }
        elif action == "kill" and pid:
            process = psutil.Process(pid)
            process.terminate()
            return {
                "status": "success",
                "message": f"Process {pid} terminated"
            }
        else:
            return {"status": "error", "error": "Invalid action or missing pid"}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@mcp.tool()
@trace_tool
@metrics_tool
def check_security(path: str) -> Dict[str, Any]:
    """Check security configuration and permissions."""
    try:
        security_info = {
            "file_permissions": {},
            "owner_info": {},
            "suspicious_files": []
        }
        
        for root, dirs, files in os.walk(path):
            for name in files + dirs:
                full_path = os.path.join(root, name)
                try:
                    stat = os.stat(full_path)
                    security_info["file_permissions"][full_path] = stat.st_mode
                    security_info["owner_info"][full_path] = {
                        "uid": stat.st_uid,
                        "gid": stat.st_gid
                    }
                    
                    # Check for suspicious files
                    if name.startswith('.') or name.endswith('.tmp'):
                        security_info["suspicious_files"].append(full_path)
                except Exception:
                    pass
                    
        return {
            "status": "success",
            "security_info": security_info
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    print("Starting Neo Operations Server on port 7446...")
    if not os.getenv("TEST_MODE"):
        mcp.run() 