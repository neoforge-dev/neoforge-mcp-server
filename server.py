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
import math
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Initialize the MCP server
mcp = FastMCP("Terminal Command Runner MCP", port=7443, log_level="DEBUG")

# Global variables for process management
session_lock = threading.Lock()
active_sessions = {}
blacklisted_commands = set(['rm -rf /', 'mkfs'])
output_queues = {}

# Global variables for debug state management
debug_sessions = {}
debug_breakpoints = {}

# Initialize tracer
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "mcp-server",
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
})

trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

# Configure exporter
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Initialize metrics
meter_provider = MeterProvider(
    metric_readers=[PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint="http://localhost:4317")
    )]
)
set_meter_provider(meter_provider)
meter = get_meter_provider().get_meter("mcp-server")

# Create metrics
tool_duration = meter.create_histogram(
    name="mcp.tool.duration",
    description="Duration of MCP tool execution",
    unit="s"
)

tool_calls = meter.create_counter(
    name="mcp.tool.calls",
    description="Number of MCP tool calls",
    unit="1"
)

tool_errors = meter.create_counter(
    name="mcp.tool.errors",
    description="Number of MCP tool errors",
    unit="1"
)

active_sessions = meter.create_up_down_counter(
    name="mcp.sessions.active",
    description="Number of active MCP sessions",
    unit="1"
)

memory_usage = meter.create_observable_gauge(
    name="mcp.system.memory_usage",
    description="Memory usage of the MCP server",
    unit="bytes",
    callbacks=[lambda _: psutil.Process().memory_info().rss]
)

def trace_tool(func):
    """Decorator to add tracing to MCP tools"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(
            name=f"mcp.tool.{func.__name__}",
            attributes={
                "mcp.tool.name": func.__name__,
                "mcp.tool.args": str(args),
                "mcp.tool.kwargs": str(kwargs)
            }
        ) as span:
            try:
                result = func(*args, **kwargs)
                if isinstance(result, dict):
                    span.set_attribute("mcp.tool.status", result.get("status", "unknown"))
                    if "error" in result:
                        span.set_attribute("mcp.tool.error", result["error"])
                return result
            except Exception as e:
                span.set_attribute("mcp.tool.error", str(e))
                span.record_exception(e)
                raise
    return wrapper

def metrics_tool(func):
    """Decorator to add metrics to MCP tools"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_calls.add(1, {"tool": func.__name__})
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            tool_duration.record(duration, {"tool": func.__name__})
            return result
        except Exception as e:
            tool_errors.add(1, {"tool": func.__name__, "error": str(e)})
            raise
    return wrapper

# Add tracing to existing tools
def add_tracing_to_tools():
    """Add tracing to all registered MCP tools"""
    for tool_name, tool_func in mcp.tools.items():
        if not hasattr(tool_func, "_traced"):
            traced_func = trace_tool(tool_func)
            traced_func._traced = True
            mcp.tools[tool_name] = traced_func

@mcp.tool()
def get_trace_info() -> Dict[str, Any]:
    """
    Get information about the current tracing configuration
    
    Returns:
        Dictionary with tracing information
    """
    try:
        current_span = trace.get_current_span()
        
        return {
            'status': 'success',
            'tracer': {
                'name': tracer.name,
                'version': trace.get_tracer_provider().__class__.__name__
            },
            'current_span': {
                'name': current_span.name if current_span else None,
                'context': str(current_span.get_span_context()) if current_span else None,
                'active': bool(current_span)
            },
            'exporter': {
                'type': otlp_exporter.__class__.__name__,
                'endpoint': otlp_exporter.endpoint
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def configure_tracing(exporter_endpoint: str = None, service_name: str = None, service_version: str = None) -> Dict[str, Any]:
    """
    Configure tracing settings
    
    Args:
        exporter_endpoint: OTLP exporter endpoint URL
        service_name: Service name for tracing
        service_version: Service version for tracing
    
    Returns:
        Dictionary with configuration result
    """
    try:
        global otlp_exporter, resource
        
        # Update exporter if endpoint provided
        if exporter_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
            trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # Update resource if service info provided
        if service_name or service_version:
            attributes = {}
            if service_name:
                attributes[ResourceAttributes.SERVICE_NAME] = service_name
            if service_version:
                attributes[ResourceAttributes.SERVICE_VERSION] = service_version
            
            resource = Resource(attributes=attributes)
            
            # Update tracer provider with new resource
            trace.set_tracer_provider(TracerProvider(resource=resource))
        
        return {
            'status': 'success',
            'config': {
                'exporter_endpoint': otlp_exporter.endpoint,
                'service_name': resource.attributes.get(ResourceAttributes.SERVICE_NAME),
                'service_version': resource.attributes.get(ResourceAttributes.SERVICE_VERSION)
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def get_metrics_info() -> Dict[str, Any]:
    """
    Get information about the current metrics configuration
    
    Returns:
        Dictionary with metrics information
    """
    try:
        return {
            'status': 'success',
            'meter': {
                'name': meter.name,
                'version': meter_provider.__class__.__name__
            },
            'metrics': {
                'tool_duration': {
                    'name': tool_duration.name,
                    'description': tool_duration.description,
                    'unit': tool_duration.unit
                },
                'tool_calls': {
                    'name': tool_calls.name,
                    'description': tool_calls.description,
                    'unit': tool_calls.unit
                },
                'tool_errors': {
                    'name': tool_errors.name,
                    'description': tool_errors.description,
                    'unit': tool_errors.unit
                },
                'active_sessions': {
                    'name': active_sessions.name,
                    'description': active_sessions.description,
                    'unit': active_sessions.unit
                },
                'memory_usage': {
                    'name': memory_usage.name,
                    'description': memory_usage.description,
                    'unit': memory_usage.unit
                }
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def configure_metrics(exporter_endpoint: str = None) -> Dict[str, Any]:
    """
    Configure metrics settings
    
    Args:
        exporter_endpoint: OTLP exporter endpoint URL
    
    Returns:
        Dictionary with configuration result
    """
    try:
        global meter_provider, meter
        
        if exporter_endpoint:
            # Create new meter provider with updated endpoint
            meter_provider = MeterProvider(
                metric_readers=[PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=exporter_endpoint)
                )]
            )
            set_meter_provider(meter_provider)
            meter = get_meter_provider().get_meter("mcp-server")
            
            # Recreate metrics with new meter
            global tool_duration, tool_calls, tool_errors, active_sessions, memory_usage
            tool_duration = meter.create_histogram(
                name="mcp.tool.duration",
                description="Duration of MCP tool execution",
                unit="s"
            )
            tool_calls = meter.create_counter(
                name="mcp.tool.calls",
                description="Number of MCP tool calls",
                unit="1"
            )
            tool_errors = meter.create_counter(
                name="mcp.tool.errors",
                description="Number of MCP tool errors",
                unit="1"
            )
            active_sessions = meter.create_up_down_counter(
                name="mcp.sessions.active",
                description="Number of active MCP sessions",
                unit="1"
            )
            memory_usage = meter.create_observable_gauge(
                name="mcp.system.memory_usage",
                description="Memory usage of the MCP server",
                unit="bytes",
                callbacks=[lambda _: psutil.Process().memory_info().rss]
            )
        
        return {
            'status': 'success',
            'config': {
                'exporter_endpoint': exporter_endpoint or "http://localhost:4317"
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# Add metrics to all tools
def add_metrics_to_tools():
    """Add metrics to all registered MCP tools"""
    for tool_name, tool_func in mcp.tools.items():
        if not hasattr(tool_func, "_metrics"):
            metriced_func = metrics_tool(tool_func)
            metriced_func._metrics = True
            mcp.tools[tool_name] = metriced_func

add_metrics_to_tools()

def is_command_safe(cmd: str) -> bool:
    """Check if a command is safe to execute"""
    if not cmd.strip():
        return False
    for blocked in blacklisted_commands:
        if blocked in cmd:
            return False
    return True

# Terminal Tools

@mcp.tool()
def execute_command(command: str, timeout: int = 10, allow_background: bool = True) -> Dict[str, Any]:
    """
    Execute a command in the terminal with configurable timeout
    
    Args:
        command: The command to execute
        timeout: Maximum time in seconds to wait for command completion (default: 10)
        allow_background: Whether to allow the command to continue in background after timeout
    
    Returns:
        Dictionary with command output information
    """
    if not is_command_safe(command):
        return {"error": f"Command not allowed: {command}", "pid": None, "stdout": "", "stderr": "Command blocked for safety reasons"}
    
    try:
        # Create a timestamp ID for this session
        session_id = str(int(time.time() * 1000))
        
        # Start the process
        process = subprocess.Popen(
            shlex.split(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        output_queue = queue.Queue()
        output_queues[process.pid] = output_queue
        
        # Create reader threads for stdout and stderr
        def reader(pipe, queue, type_name):
            for line in iter(pipe.readline, ''):
                queue.put((type_name, line))
            pipe.close()
        
        stdout_thread = threading.Thread(target=reader, args=(process.stdout, output_queue, "stdout"))
        stderr_thread = threading.Thread(target=reader, args=(process.stderr, output_queue, "stderr"))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Collect output for timeout seconds
        stdout_data = []
        stderr_data = []
        start_time = time.time()
        
        try:
            while process.poll() is None and time.time() - start_time < timeout:
                try:
                    type_name, line = output_queue.get(timeout=0.1)
                    if type_name == "stdout":
                        stdout_data.append(line)
                    else:
                        stderr_data.append(line)
                except queue.Empty:
                    pass
        except KeyboardInterrupt:
            pass
        
        # Check if process completed
        exit_code = process.poll()
        
        # Register the active session if still running
        if exit_code is None and allow_background:
            with session_lock:
                active_sessions[process.pid] = {
                    "command": command,
                    "start_time": datetime.now().isoformat(),
                    "pid": process.pid,
                    "session_id": session_id
                }
        elif exit_code is None:
            # If not allowing background processes, terminate
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            exit_code = process.poll()
        
        # Join stdout and stderr data
        stdout = "".join(stdout_data)
        stderr = "".join(stderr_data)
        
        return {
            "pid": process.pid if exit_code is None else None,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "session_id": session_id,
            "complete": exit_code is not None,
            "runtime": round(time.time() - start_time, 2)
        }
    
    except Exception as e:
        return {"error": str(e), "pid": None, "stdout": "", "stderr": f"Error: {str(e)}"}

@mcp.tool()
def read_output(pid: int) -> Dict[str, Any]:
    """
    Get output from a long-running command session
    
    Args:
        pid: Process ID of the running command
    
    Returns:
        Dictionary with command output information
    """
    with session_lock:
        if pid not in active_sessions:
            return {"error": f"No active session with PID {pid}", "stdout": "", "stderr": ""}
    
    if pid not in output_queues:
        return {"error": f"No output queue for PID {pid}", "stdout": "", "stderr": ""}
    
    queue = output_queues[pid]
    stdout_data = []
    stderr_data = []
    
    # Get all available output
    while not queue.empty():
        try:
            type_name, line = queue.get_nowait()
            if type_name == "stdout":
                stdout_data.append(line)
            else:
                stderr_data.append(line)
        except queue.Empty:
            break
    
    # Check if process has completed
    try:
        exit_code = os.waitpid(pid, os.WNOHANG)[1]
        process_running = exit_code == 0
    except ChildProcessError:
        # Process already completed
        process_running = False
        exit_code = -1
    
    # If process completed, remove from active sessions
    if not process_running:
        with session_lock:
            if pid in active_sessions:
                del active_sessions[pid]
        if pid in output_queues:
            del output_queues[pid]
    
    return {
        "pid": pid if process_running else None,
        "stdout": "".join(stdout_data),
        "stderr": "".join(stderr_data),
        "complete": not process_running,
        "exit_code": None if process_running else exit_code
    }

@mcp.tool()
def force_terminate(pid: int) -> Dict[str, Any]:
    """
    Stop a running command session
    
    Args:
        pid: Process ID to terminate
    
    Returns:
        Dictionary with termination status
    """
    try:
        # First try graceful termination
        os.kill(pid, signal.SIGTERM)
        
        # Wait a bit for process to terminate
        for _ in range(5):
            try:
                # Check if process still exists
                if os.waitpid(pid, os.WNOHANG)[0]:
                    # Process has terminated
                    break
            except ChildProcessError:
                # Process already completed
                break
            time.sleep(0.1)
        
        # If still running, force kill
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            # Process already terminated
            pass
        
        # Remove from active sessions
        with session_lock:
            if pid in active_sessions:
                command = active_sessions[pid]["command"]
                del active_sessions[pid]
            else:
                command = "Unknown"
        
        if pid in output_queues:
            del output_queues[pid]
        
        return {
            "success": True,
            "message": f"Process {pid} ({command}) terminated successfully"
        }
    except ProcessLookupError:
        return {
            "success": False,
            "message": f"Process {pid} not found, it may have already terminated"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error terminating process {pid}: {str(e)}"
        }

@mcp.tool()
def list_sessions() -> Dict[str, Any]:
    """
    List all active command sessions
    
    Returns:
        Dictionary with active sessions information
    """
    with session_lock:
        sessions = []
        for pid, session in active_sessions.items():
            sessions.append({
                "pid": pid,
                "command": session["command"],
                "start_time": session["start_time"],
                "session_id": session["session_id"]
            })
    
    return {
        "success": True,
        "sessions": sessions,
        "count": len(sessions)
    }

@mcp.tool()
def list_processes() -> Dict[str, Any]:
    """
    List all system processes
    
    Returns:
        Dictionary with system processes information
    """
    try:
        processes = []
        
        # Use different commands based on platform
        if platform.system() == "Windows":
            # Windows implementation using wmic
            output = subprocess.check_output(["wmic", "process", "get", "ProcessId,Name,CommandLine,ParentProcessId,ExecutablePath,Priority,ThreadCount /format:csv"], 
                                             text=True)
            lines = output.strip().split('\n')
            if len(lines) > 1:  # Skip header
                header = lines[0].strip().split(',')
                for line in lines[1:]:
                    if line.strip():
                        parts = line.strip().split(',')
                        process = {}
                        for i, field in enumerate(header):
                            if i < len(parts):
                                process[field.lower()] = parts[i]
                        
                        if "processid" in process:
                            try:
                                process["pid"] = int(process["processid"])
                                processes.append(process)
                            except ValueError:
                                pass
        else:
            # Unix/Linux/macOS implementation using ps
            output = subprocess.check_output(["ps", "-eo", "pid,ppid,user,stat,pcpu,pmem,command"], text=True)
            lines = output.strip().split('\n')
            if len(lines) > 0:  # Has at least header
                header = lines[0].strip().split()
                for line in lines[1:]:
                    if line.strip():
                        parts = line.strip().split(None, 6)  # Split for up to 7 columns
                        if len(parts) >= 7:
                            try:
                                process = {
                                    "pid": int(parts[0]),
                                    "ppid": int(parts[1]),
                                    "username": parts[2],
                                    "state": parts[3],
                                    "cpu_percent": float(parts[4]),
                                    "memory_percent": float(parts[5]),
                                    "command": parts[6],
                                    "name": os.path.basename(parts[6].split()[0])
                                }
                                processes.append(process)
                            except (ValueError, IndexError):
                                pass
        
        return {
            "success": True,
            "processes": processes,
            "count": len(processes)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def kill_process(pid: int, signal_type: str = "TERM") -> Dict[str, Any]:
    """
    Terminate a process by PID
    
    Args:
        pid: Process ID to kill
        signal_type: Signal to send (TERM, KILL, etc.)
    
    Returns:
        Dictionary with operation status
    """
    try:
        # Determine signal to send
        if platform.system() == "Windows":
            # On Windows, just use taskkill
            if signal_type == "KILL":
                subprocess.check_call(["taskkill", "/F", "/PID", str(pid)])
            else:
                subprocess.check_call(["taskkill", "/PID", str(pid)])
        else:
            # On Unix-like systems, map string signal names to signal numbers
            signal_map = {
                "TERM": signal.SIGTERM,
                "KILL": signal.SIGKILL,
                "INT": signal.SIGINT,
                "HUP": signal.SIGHUP,
                "QUIT": signal.SIGQUIT
            }
            
            sig = signal_map.get(signal_type.upper(), signal.SIGTERM)
            os.kill(pid, sig)
        
        # Check if this was an active session and remove it
        with session_lock:
            if pid in active_sessions:
                del active_sessions[pid]
        
        return {
            "success": True,
            "pid": pid,
            "signal": signal_type
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Command Control Tools

@mcp.tool()
def block_command(command: str) -> Dict[str, Any]:
    """
    Add a command to the blacklist
    
    Args:
        command: Command pattern to block
    
    Returns:
        Dictionary with operation status
    """
    try:
        blacklisted_commands.add(command)
        return {
            "success": True,
            "message": f"Command '{command}' added to blacklist",
            "blacklist": list(blacklisted_commands)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def unblock_command(command: str) -> Dict[str, Any]:
    """
    Remove a command from the blacklist
    
    Args:
        command: Command pattern to unblock
    
    Returns:
        Dictionary with operation status
    """
    try:
        if command in blacklisted_commands:
            blacklisted_commands.remove(command)
            message = f"Command '{command}' removed from blacklist"
        else:
            message = f"Command '{command}' was not in blacklist"
        
        return {
            "success": True,
            "message": message,
            "blacklist": list(blacklisted_commands)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Filesystem Tools

@mcp.tool()
def read_file(path: str, max_size_mb: float = 10.0) -> Dict[str, Any]:
    """
    Read file contents with size limits
    
    Args:
        path: Path to the file to read
        max_size_mb: Maximum file size in MB to read (default: 10MB)
    
    Returns:
        Dictionary with file content and metadata
    """
    try:
        # Convert MB to bytes
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        
        # Check if file exists
        if not os.path.exists(path):
            return {
                "success": False,
                "error": f"File not found: {path}"
            }
        
        # Check file size
        file_size = os.path.getsize(path)
        if file_size > max_size_bytes:
            return {
                "success": False,
                "error": f"File exceeds size limit of {max_size_mb}MB (actual size: {file_size / (1024 * 1024):.2f}MB)"
            }
        
        # Read file content
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "size": file_size,
            "path": path
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def write_file(path: str, content: str, create_dirs: bool = False) -> Dict[str, Any]:
    """
    Write content to a file
    
    Args:
        path: Path to the file to write
        content: Content to write to the file
        create_dirs: Whether to create parent directories if they don't exist
    
    Returns:
        Dictionary with operation status
    """
    try:
        # Create parent directories if needed
        if create_dirs:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # Write content to file
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return {
            "success": True,
            "path": path,
            "size": len(content)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def create_directory(path: str) -> Dict[str, Any]:
    """
    Create a new directory
    
    Args:
        path: Path to the directory to create
    
    Returns:
        Dictionary with operation status
    """
    try:
        # Check if directory already exists
        if os.path.exists(path):
            if os.path.isdir(path):
                return {
                    "success": False,
                    "error": f"Directory already exists: {path}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Path exists but is not a directory: {path}"
                }
        
        # Create directory and parents
        os.makedirs(path)
        
        return {
            "success": True,
            "path": path
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def list_directory(path: str, show_hidden: bool = False) -> Dict[str, Any]:
    """
    List directory contents
    
    Args:
        path: Path to the directory to list
        show_hidden: Whether to include hidden files (starting with .) in the output
    
    Returns:
        Dictionary with directory contents
    """
    try:
        # Check if directory exists
        if not os.path.exists(path):
            return {
                "success": False,
                "error": f"Directory not found: {path}"
            }
        
        if not os.path.isdir(path):
            return {
                "success": False,
                "error": f"Path is not a directory: {path}"
            }
        
        # List directory contents
        contents = []
        for item in os.listdir(path):
            # Skip hidden files if not showing them
            if not show_hidden and item.startswith('.'):
                continue
            
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            
            # Get item stats
            stats = os.stat(item_path)
            
            contents.append({
                "name": item,
                "type": "directory" if is_dir else "file",
                "size": stats.st_size if not is_dir else 0,
                "modified": stats.st_mtime
            })
        
        return {
            "success": True,
            "path": path,
            "contents": contents
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def move_file(source: str, destination: str) -> Dict[str, Any]:
    """
    Move or rename a file or directory
    
    Args:
        source: Path to the source file or directory
        destination: Path to the destination
    
    Returns:
        Dictionary with operation status
    """
    try:
        # Check if source exists
        if not os.path.exists(source):
            return {
                "success": False,
                "error": f"Source path not found: {source}"
            }
        
        # Move the file or directory
        shutil.move(source, destination)
        
        return {
            "success": True,
            "source": source,
            "destination": destination
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def search_files(path: str, pattern: str, recursive: bool = True, max_results: int = 100) -> Dict[str, Any]:
    """
    Find files matching a pattern
    
    Args:
        path: Directory to search in
        pattern: Glob pattern to match files against
        recursive: Whether to search recursively in subdirectories
        max_results: Maximum number of results to return
    
    Returns:
        Dictionary with matching files
    """
    try:
        # Check if directory exists
        if not os.path.exists(path):
            return {
                "success": False,
                "error": f"Directory not found: {path}"
            }
        
        if not os.path.isdir(path):
            return {
                "success": False,
                "error": f"Path is not a directory: {path}"
            }
        
        # Set up glob pattern
        if recursive:
            search_pattern = os.path.join(path, "**", pattern)
        else:
            search_pattern = os.path.join(path, pattern)
        
        # Find matching files
        matches = []
        for file_path in glob.glob(search_pattern, recursive=recursive):
            if len(matches) >= max_results:
                break
            
            # Get relative path from search directory
            rel_path = os.path.relpath(file_path, path)
            matches.append(rel_path)
        
        return {
            "success": True,
            "path": path,
            "pattern": pattern,
            "matches": matches,
            "truncated": len(matches) >= max_results
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def get_file_info(path: str) -> Dict[str, Any]:
    """
    Get metadata about a file or directory
    
    Args:
        path: Path to the file or directory
    
    Returns:
        Dictionary with file metadata
    """
    try:
        # Common result structure for all cases
        result = {
            "success": True,
            "path": path,
            "exists": os.path.exists(path)
        }
        
        # If path doesn't exist, return early
        if not result["exists"]:
            return result
        
        # Get file stats
        stats = os.stat(path)
        
        # Determine type
        if os.path.isdir(path):
            result["type"] = "directory"
        else:
            result["type"] = "file"
            
        # Add more metadata
        result["size"] = stats.st_size
        result["modified"] = stats.st_mtime
        result["created"] = stats.st_ctime
        result["permissions"] = oct(stats.st_mode)[-3:]  # Last 3 digits of octal representation
        
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# Edit Tools

@mcp.tool()
def edit_block(content: str) -> Dict[str, Any]:
    """
    Apply edits to a file with a diff-like syntax
    
    Args:
        content: Edit block in the format:
                 @@ file_path
                 new content
                 to write
    
    Returns:
        Dictionary with operation status
    """
    try:
        lines = content.strip().split("\n")
        
        # Extract the file path from the first line
        if not lines or not lines[0].startswith("@@"):
            return {
                "success": False,
                "error": "Invalid edit block format. First line must start with @@ followed by file path"
            }
        
        file_path = lines[0][2:].strip()
        if not file_path:
            return {
                "success": False,
                "error": "No file path specified in the edit block"
            }
        
        # Extract the new content (all lines after the first)
        new_content = "\n".join(lines[1:])
        
        # Write to the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return {
            "success": True,
            "file": file_path,
            "size": len(new_content)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# System Info

@mcp.resource("info://system")
def system_info() -> Dict[str, Any]:
    """
    Get detailed system information
    
    Returns:
        Dictionary with system information
    """
    try:
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.architecture(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "node": platform.node(),
            "hostname": socket.gethostname(),
            "cpu_count": os.cpu_count() or 0,
            "timezone": time.tzname,
            "current_time": datetime.now().isoformat(),
            "uptime": None  # Will be filled conditionally
        }
        
        # Get memory info if psutil is available
        try:
            import psutil
            mem = psutil.virtual_memory()
            info["memory"] = {
                "total": mem.total,
                "available": mem.available,
                "percent_used": mem.percent
            }
            info["uptime"] = time.time() - psutil.boot_time()
        except ImportError:
            # psutil not available, try to get some info from os
            if platform.system() == "Linux":
                try:
                    with open("/proc/uptime", "r") as f:
                        uptime_seconds = float(f.readline().split()[0])
                        info["uptime"] = uptime_seconds
                except:
                    pass
                    
                try:
                    with open("/proc/meminfo", "r") as f:
                        meminfo = {}
                        for line in f:
                            parts = line.split(":")
                            if len(parts) == 2:
                                key = parts[0].strip()
                                value = parts[1].strip().split(" ")[0]
                                meminfo[key] = int(value) * 1024  # Convert from KB to bytes
                        
                        info["memory"] = {
                            "total": meminfo.get("MemTotal", 0),
                            "available": meminfo.get("MemAvailable", 0),
                            "percent_used": (1 - (meminfo.get("MemAvailable", 0) / meminfo.get("MemTotal", 1))) * 100
                        }
                except:
                    pass
        
        return info
    except Exception as e:
        return {
            "error": str(e)
        }

# Add utility for calculating expressions
@mcp.tool()
def calculate(expression: str) -> Dict[str, Any]:
    """
    Evaluate a mathematical expression
    
    Args:
        expression: Mathematical expression to evaluate
    
    Returns:
        Dictionary with evaluation result
    """
    try:
        # Create a safe environment with only mathematical functions and constants
        safe_dict = {
            "abs": abs, "max": max, "min": min,
            "pow": pow, "round": round,
            "sum": sum, "len": len,
            "int": int, "float": float,
            "pi": math.pi, "e": math.e,
            "sqrt": math.sqrt, "exp": math.exp,
            "log": math.log, "log10": math.log10,
            "sin": math.sin, "cos": math.cos,
            "tan": math.tan, "asin": math.asin,
            "acos": math.acos, "atan": math.atan,
            "ceil": math.ceil, "floor": math.floor
        }
        
        # Check for suspicious patterns
        suspicious_patterns = [
            "import", "exec", "eval", "compile", 
            "getattr", "setattr", "delattr",
            "hasattr", "globals", "locals", 
            "__", "os.", "sys.", "subprocess",
            "lambda", "open", "file"
        ]
        
        for pattern in suspicious_patterns:
            if pattern in expression:
                return {
                    "success": False,
                    "error": f"Expression contains suspicious pattern: {pattern}"
                }
        
        # Evaluate the expression in the safe environment
        result = eval(expression, {"__builtins__": {}}, safe_dict)
        
        return {
            "success": True,
            "expression": expression,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool()
def codebase_navigate(pattern: str, scope: str = "project", max_depth: int = None) -> Dict[str, Any]:
    """
    Advanced codebase navigation tool for finding symbols, functions, and patterns
    
    Args:
        pattern: Search pattern or symbol name
        scope: Search scope ('file' or 'project')
        max_depth: Maximum directory depth to search
    
    Returns:
        Dictionary with matching locations and context
    """
    try:
        results = []
        
        if scope == "file" and os.path.isfile(pattern):
            # If pattern is a file path, analyze single file
            with open(pattern, 'r') as f:
                content = f.read()
                results.extend(_analyze_file_content(pattern, content))
        else:
            # Search through project files
            for root, _, files in os.walk('.', topdown=True):
                if max_depth and root.count(os.sep) > max_depth:
                    continue
                    
                for file in files:
                    if file.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.h', '.c')):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r') as f:
                                content = f.read()
                                matches = _analyze_file_content(file_path, content, pattern)
                                if matches:
                                    results.extend(matches)
                        except Exception as e:
                            continue
                            
        return {
            "status": "success",
            "matches": results,
            "count": len(results)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "matches": [],
            "count": 0
        }

def _analyze_file_content(file_path: str, content: str, pattern: str = None) -> List[Dict[str, Any]]:
    """Helper function to analyze file content for symbols and patterns"""
    results = []
    lines = content.split('\n')
    
    # Simple symbol detection regex patterns
    patterns = {
        'function': r'^\s*(?:def|function|async def)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        'class': r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)',
        'variable': r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=',
        'import': r'^\s*(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_\.]*)',
    }
    
    for i, line in enumerate(lines):
        # If pattern is provided, only look for that
        if pattern and pattern not in line:
            continue
            
        for symbol_type, regex in patterns.items():
            match = re.search(regex, line)
            if match:
                symbol = match.group(1)
                # If pattern provided, only include if it matches
                if not pattern or pattern in symbol:
                    results.append({
                        'file': file_path,
                        'line': i + 1,
                        'symbol': symbol,
                        'type': symbol_type,
                        'context': line.strip(),
                        'preview': '\n'.join(lines[max(0, i-1):min(len(lines), i+2)])
                    })
    
    return results

@mcp.tool()
def static_analyze(file_path: str, checks: List[str] = None) -> Dict[str, Any]:
    """
    Static code analysis tool for finding potential issues
    
    Args:
        file_path: Path to the file to analyze
        checks: List of check types to perform ('type', 'security', 'style', 'complexity')
    
    Returns:
        Dictionary with analysis results
    """
    if not checks:
        checks = ['type', 'security', 'style', 'complexity']
        
    results = {
        'issues': [],
        'metrics': {},
        'status': 'success'
    }
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            lines = content.split('\n')
            
        # Basic security checks
        if 'security' in checks:
            security_patterns = {
                'hardcoded_secret': r'(?i)(?:password|secret|key|token)\s*=\s*[\'"][^\'"]+[\'"]',
                'sql_injection': r'(?i)(?:execute|executemany)\s*\([^)]*\%[^)]*\)',
                'command_injection': r'(?i)(?:os\.system|subprocess\.(?:call|Popen|run))\s*\([^)]*\%[^)]*\)',
            }
            
            for i, line in enumerate(lines):
                for issue_type, pattern in security_patterns.items():
                    if re.search(pattern, line):
                        results['issues'].append({
                            'type': 'security',
                            'subtype': issue_type,
                            'line': i + 1,
                            'message': f'Potential {issue_type} vulnerability detected',
                            'severity': 'high',
                            'context': line.strip()
                        })
        
        # Style checks
        if 'style' in checks:
            for i, line in enumerate(lines):
                # Line length
                if len(line) > 100:
                    results['issues'].append({
                        'type': 'style',
                        'subtype': 'line_length',
                        'line': i + 1,
                        'message': 'Line exceeds 100 characters',
                        'severity': 'low',
                        'context': line.strip()
                    })
                    
                # Trailing whitespace
                if line.rstrip() != line:
                    results['issues'].append({
                        'type': 'style',
                        'subtype': 'trailing_whitespace',
                        'line': i + 1,
                        'message': 'Line contains trailing whitespace',
                        'severity': 'low',
                        'context': line
                    })
        
        # Complexity metrics
        if 'complexity' in checks:
            results['metrics'] = {
                'total_lines': len(lines),
                'code_lines': sum(1 for line in lines if line.strip() and not line.strip().startswith('#')),
                'comment_lines': sum(1 for line in lines if line.strip().startswith('#')),
                'functions': len(re.findall(r'^\s*def\s+', content, re.MULTILINE)),
                'classes': len(re.findall(r'^\s*class\s+', content, re.MULTILINE)),
            }
            
            # Cyclomatic complexity estimation
            complexity_indicators = ['if', 'elif', 'for', 'while', 'except', 'with', 'assert']
            complexity = 1 + sum(content.count(f' {indicator} ') for indicator in complexity_indicators)
            results['metrics']['cyclomatic_complexity'] = complexity
            
            if complexity > 15:
                results['issues'].append({
                    'type': 'complexity',
                    'subtype': 'high_complexity',
                    'line': None,
                    'message': f'High cyclomatic complexity ({complexity})',
                    'severity': 'medium',
                    'context': None
                })
        
        return results
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'issues': [],
            'metrics': {}
        }

@mcp.resource("debug://state")
def debug_state() -> Dict[str, Any]:
    """
    Resource that provides current debug state information
    
    Returns:
        Dictionary with debug state information
    """
    active_sessions = []
    
    for session_id, session in debug_sessions.items():
        if session.get('active', False):
            active_sessions.append({
                'session_id': session_id,
                'file': session.get('file'),
                'line': session.get('line'),
                'variables': session.get('variables', {}),
                'call_stack': session.get('call_stack', []),
                'breakpoints': debug_breakpoints.get(session_id, [])
            })
    
    return {
        'active_sessions': active_sessions,
        'global_breakpoints': [bp for bp_list in debug_breakpoints.values() for bp in bp_list],
        'timestamp': datetime.now().isoformat()
    }

@mcp.tool()
def debug_control(action: str, session_id: str = None, file_path: str = None, line_number: int = None, expression: str = None) -> Dict[str, Any]:
    """
    Control debugging sessions and evaluate expressions
    
    Args:
        action: Debug action ('start', 'stop', 'step', 'continue', 'breakpoint', 'evaluate')
        session_id: Debug session identifier
        file_path: Path to the file being debugged
        line_number: Line number for breakpoint
        expression: Expression to evaluate in current context
    
    Returns:
        Dictionary with operation result
    """
    try:
        if action == 'start':
            if not file_path:
                return {'status': 'error', 'error': 'File path required to start debugging'}
                
            # Create new debug session
            session_id = f"debug_{int(time.time())}"
            debug_sessions[session_id] = {
                'active': True,
                'file': file_path,
                'line': 1,
                'variables': {},
                'call_stack': [],
                'start_time': datetime.now().isoformat()
            }
            
            # Start debug process
            process = subprocess.Popen(
                ['python', '-m', 'pdb', file_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            debug_sessions[session_id]['process'] = process
            return {
                'status': 'success',
                'session_id': session_id,
                'message': f'Debug session started for {file_path}'
            }
            
        elif action == 'stop':
            if not session_id or session_id not in debug_sessions:
                return {'status': 'error', 'error': 'Invalid session ID'}
                
            session = debug_sessions[session_id]
            if session.get('process'):
                session['process'].terminate()
            
            session['active'] = False
            return {
                'status': 'success',
                'message': f'Debug session {session_id} stopped'
            }
            
        elif action == 'breakpoint':
            if not file_path or not line_number:
                return {'status': 'error', 'error': 'File path and line number required for breakpoint'}
                
            if session_id not in debug_breakpoints:
                debug_breakpoints[session_id] = []
                
            breakpoint_info = {
                'file': file_path,
                'line': line_number,
                'enabled': True
            }
            
            debug_breakpoints[session_id].append(breakpoint_info)
            return {
                'status': 'success',
                'message': f'Breakpoint set at {file_path}:{line_number}'
            }
            
        elif action in ['step', 'continue']:
            if not session_id or session_id not in debug_sessions:
                return {'status': 'error', 'error': 'Invalid session ID'}
                
            session = debug_sessions[session_id]
            if not session.get('process'):
                return {'status': 'error', 'error': 'Debug process not running'}
                
            # Send appropriate command to debugger
            cmd = 'n' if action == 'step' else 'c'
            session['process'].stdin.write(f'{cmd}\n')
            session['process'].stdin.flush()
            
            # Read output until next break
            output = []
            while True:
                line = session['process'].stdout.readline()
                if not line or '(Pdb)' in line:
                    break
                output.append(line.strip())
            
            return {
                'status': 'success',
                'output': output,
                'action': action
            }
            
        elif action == 'evaluate':
            if not session_id or session_id not in debug_sessions:
                return {'status': 'error', 'error': 'Invalid session ID'}
                
            if not expression:
                return {'status': 'error', 'error': 'Expression required for evaluation'}
                
            session = debug_sessions[session_id]
            if not session.get('process'):
                return {'status': 'error', 'error': 'Debug process not running'}
                
            # Send expression to debugger
            session['process'].stdin.write(f'p {expression}\n')
            session['process'].stdin.flush()
            
            # Read result
            result = session['process'].stdout.readline().strip()
            return {
                'status': 'success',
                'expression': expression,
                'result': result
            }
            
        else:
            return {'status': 'error', 'error': f'Unknown action: {action}'}
            
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def git_operation(command: str, parameters: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Execute Git operations safely
    
    Args:
        command: Git command to execute ('status', 'diff', 'log', 'branch', 'commit')
        parameters: Additional parameters for the command
    
    Returns:
        Dictionary with operation result
    """
    if not parameters:
        parameters = {}
        
    # Validate command
    allowed_commands = {
        'status': [],
        'diff': ['file', 'staged'],
        'log': ['limit', 'file'],
        'branch': ['name', 'delete'],
        'commit': ['message', 'files']
    }
    
    if command not in allowed_commands:
        return {
            'status': 'error',
            'error': f'Unsupported git command: {command}'
        }
    
    try:
        if command == 'status':
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                 capture_output=True, text=True, check=True)
            
            # Parse status output
            changes = {
                'staged': [],
                'unstaged': [],
                'untracked': []
            }
            
            for line in result.stdout.split('\n'):
                if not line:
                    continue
                status = line[:2]
                file = line[3:]
                
                if status[0] != ' ':
                    changes['staged'].append({'file': file, 'status': status[0]})
                if status[1] != ' ':
                    changes['unstaged'].append({'file': file, 'status': status[1]})
                if status == '??':
                    changes['untracked'].append(file)
                    
            return {
                'status': 'success',
                'changes': changes
            }
            
        elif command == 'diff':
            cmd = ['git', 'diff']
            if parameters.get('staged'):
                cmd.append('--staged')
            if parameters.get('file'):
                cmd.append(parameters['file'])
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                'status': 'success',
                'diff': result.stdout
            }
            
        elif command == 'log':
            cmd = ['git', 'log', '--pretty=format:%H|%an|%ad|%s']
            if parameters.get('limit'):
                cmd.append(f'-n{parameters["limit"]}')
            if parameters.get('file'):
                cmd.append(parameters['file'])
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            commits = []
            for line in result.stdout.split('\n'):
                if line:
                    hash, author, date, message = line.split('|')
                    commits.append({
                        'hash': hash,
                        'author': author,
                        'date': date,
                        'message': message
                    })
                    
            return {
                'status': 'success',
                'commits': commits
            }
            
        elif command == 'branch':
            if parameters.get('delete'):
                if not parameters.get('name'):
                    return {'status': 'error', 'error': 'Branch name required for deletion'}
                cmd = ['git', 'branch', '-d', parameters['name']]
            elif parameters.get('name'):
                cmd = ['git', 'checkout', '-b', parameters['name']]
            else:
                cmd = ['git', 'branch']
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                'status': 'success',
                'output': result.stdout
            }
            
        elif command == 'commit':
            if not parameters.get('message'):
                return {'status': 'error', 'error': 'Commit message required'}
                
            # Stage files if specified
            if parameters.get('files'):
                files = parameters['files'] if isinstance(parameters['files'], list) else [parameters['files']]
                for file in files:
                    subprocess.run(['git', 'add', file], check=True)
            
            # Create commit
            result = subprocess.run(['git', 'commit', '-m', parameters['message']], 
                                 capture_output=True, text=True, check=True)
                                 
            return {
                'status': 'success',
                'message': result.stdout
            }
            
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'error': e.stderr
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# Development Tools

@mcp.tool()
def install_dependency(package: str, dev: bool = False) -> Dict[str, Any]:
    """
    Install Python package using uv
    
    Args:
        package: Package name and optional version spec
        dev: Whether to install as a development dependency
    
    Returns:
        Dictionary with installation result
    """
    try:
        cmd = ['uv', 'add']
        if dev:
            cmd.append('--dev')
        cmd.append(package)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Read pyproject.toml to verify installation
        with open('pyproject.toml', 'r') as f:
            pyproject_content = f.read()
            
        return {
            'status': 'success',
            'output': result.stdout,
            'package': package,
            'pyproject_toml': pyproject_content
        }
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'error': e.stderr
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def run_tests(target: str = None, docker: bool = False) -> Dict[str, Any]:
    """
    Run tests with proper isolation
    
    Args:
        target: Specific test target (file or directory)
        docker: Whether to run tests in Docker
    
    Returns:
        Dictionary with test results
    """
    try:
        if docker:
            cmd = ['make', 'test']
            if target:
                cmd.extend(['TEST_TARGET=' + target])
        else:
            cmd = ['pytest']
            if target:
                cmd.append(target)
            cmd.extend(['-v', '--capture=no'])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Process the output to be more LLM-friendly
        output_lines = result.stdout.split('\n')
        filtered_output = _filter_test_output(output_lines)
        
        return {
            'status': 'success' if result.returncode == 0 else 'failure',
            'output': filtered_output,
            'exit_code': result.returncode,
            'errors': result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _filter_test_output(lines: List[str]) -> str:
    """Helper to filter and format test output for LLM consumption"""
    important_lines = []
    summary_stats = {}
    
    for line in lines:
        # Keep test results
        if line.startswith('test_'):
            important_lines.append(line)
        # Keep error messages
        elif 'ERROR' in line or 'FAILED' in line:
            important_lines.append(line)
        # Extract summary statistics
        elif 'failed' in line and 'passed' in line:
            summary_stats['summary'] = line.strip()
            
    return {
        'details': important_lines,
        'summary': summary_stats
    }

@mcp.tool()
def format_code(path: str = '.') -> Dict[str, Any]:
    """
    Format code using ruff
    
    Args:
        path: Path to format (file or directory)
    
    Returns:
        Dictionary with formatting result
    """
    try:
        cmd = ['ruff', 'format', path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            'status': 'success' if result.returncode == 0 else 'error',
            'output': result.stdout,
            'errors': result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def lint_code(path: str = '.', fix: bool = False) -> Dict[str, Any]:
    """
    Run ruff linting
    
    Args:
        path: Path to lint (file or directory)
        fix: Whether to automatically fix issues
    
    Returns:
        Dictionary with linting result
    """
    try:
        cmd = ['ruff', 'check']
        if fix:
            cmd.append('--fix')
        cmd.append(path)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Process output to be more LLM-friendly
        output_lines = result.stdout.split('\n')
        filtered_output = _filter_lint_output(output_lines)
        
        return {
            'status': 'success' if result.returncode == 0 else 'warning',
            'issues': filtered_output,
            'errors': result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _filter_lint_output(lines: List[str]) -> List[Dict[str, Any]]:
    """Helper to filter and format lint output for LLM consumption"""
    issues = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Parse ruff output format
        try:
            file_path, line_no, message = line.split(':', 2)
            issues.append({
                'file': file_path.strip(),
                'line': int(line_no),
                'message': message.strip()
            })
        except ValueError:
            continue
            
    return issues

@mcp.tool()
def filter_output(content: str, max_lines: int = 50, important_patterns: List[str] = None) -> Dict[str, Any]:
    """
    Process and format long command outputs for better LLM consumption
    
    Args:
        content: The text content to filter
        max_lines: Maximum number of lines to include
        important_patterns: List of regex patterns to always include
    
    Returns:
        Dictionary with filtered content
    """
    try:
        lines = content.split('\n')
        total_lines = len(lines)
        
        if not important_patterns:
            important_patterns = [
                r'error', r'warning', r'fail', r'exception',
                r'success', r'completed', r'starting', r'finished'
            ]
        
        # Always keep lines matching important patterns
        important_lines = []
        other_lines = []
        
        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in important_patterns):
                important_lines.append(line)
            else:
                other_lines.append(line)
        
        # Calculate remaining space for other lines
        remaining_space = max_lines - len(important_lines)
        
        if remaining_space <= 0:
            filtered_lines = important_lines[:max_lines]
        else:
            # Select a representative sample of other lines
            step = len(other_lines) // remaining_space if remaining_space > 0 else 1
            sampled_lines = other_lines[::step][:remaining_space]
            filtered_lines = important_lines + sampled_lines
        
        return {
            'filtered_content': '\n'.join(filtered_lines),
            'total_lines': total_lines,
            'included_lines': len(filtered_lines),
            'important_lines': len(important_lines),
            'truncated': total_lines > len(filtered_lines)
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def context_length(text: str) -> Dict[str, Any]:
    """
    Track LLM context usage
    
    Args:
        text: Text to analyze for context length
    
    Returns:
        Dictionary with context length metrics
    """
    try:
        # Simple tokenization (this is a basic approximation)
        words = text.split()
        characters = len(text)
        lines = text.count('\n') + 1
        
        # Rough token estimation (OpenAI GPT-style)
        # This is a very rough approximation - actual tokenization is more complex
        estimated_tokens = len(words) * 1.3
        
        # Context length limits (example values)
        limits = {
            'claude-3-opus': 200000,
            'claude-3-sonnet': 100000,
            'gpt-4': 128000,
            'gpt-3.5': 16000
        }
        
        # Calculate percentage of context used
        usage = {model: (estimated_tokens / limit) * 100 for model, limit in limits.items()}
        
        return {
            'estimated_tokens': int(estimated_tokens),
            'words': len(words),
            'characters': characters,
            'lines': lines,
            'context_usage_percent': usage,
            'approaching_limit': any(pct > 75 for pct in usage.values())
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def analyze_codebase(path: str = ".", analysis_type: str = "all") -> Dict[str, Any]:
    """
    Advanced codebase analysis tool
    
    Args:
        path: Path to analyze
        analysis_type: Type of analysis ('complexity', 'dependencies', 'security', 'all')
    
    Returns:
        Dictionary with analysis results
    """
    try:
        results = {
            'metrics': {},
            'dependencies': {},
            'security_issues': [],
            'complexity_hotspots': []
        }
        
        # Get all Python files
        python_files = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        if analysis_type in ('all', 'complexity'):
            # Analyze code complexity
            for file_path in python_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Calculate complexity metrics
                complexity = _calculate_complexity(content)
                if complexity['score'] > 15:
                    results['complexity_hotspots'].append({
                        'file': file_path,
                        'complexity': complexity
                    })
                results['metrics'][file_path] = complexity
        
        if analysis_type in ('all', 'dependencies'):
            # Analyze dependencies
            import_pattern = re.compile(r'^(?:from|import)\s+([\w\.]+)', re.MULTILINE)
            for file_path in python_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                imports = import_pattern.findall(content)
                results['dependencies'][file_path] = list(set(imports))
        
        if analysis_type in ('all', 'security'):
            # Security analysis
            security_patterns = {
                'hardcoded_secret': (r'(?i)(?:password|secret|key|token)\s*=\s*[\'"][^\'"]+[\'"]', 'high'),
                'sql_injection': (r'(?i)(?:execute|executemany)\s*\([^)]*\%[^)]*\)', 'high'),
                'command_injection': (r'(?i)(?:os\.system|subprocess\.(?:call|Popen|run))\s*\([^)]*\%[^)]*\)', 'high'),
                'unsafe_yaml': (r'(?i)yaml\.load\(', 'medium'),
                'pickle_usage': (r'(?i)pickle\.loads?\(', 'medium')
            }
            
            for file_path in python_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                for issue_type, (pattern, severity) in security_patterns.items():
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_no = content[:match.start()].count('\n') + 1
                        results['security_issues'].append({
                            'file': file_path,
                            'line': line_no,
                            'type': issue_type,
                            'severity': severity,
                            'context': match.group(0)
                        })
        
        return {
            'status': 'success',
            'results': results
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _calculate_complexity(content: str) -> Dict[str, Any]:
    """Helper function to calculate code complexity metrics"""
    complexity = {
        'score': 1,
        'functions': 0,
        'classes': 0,
        'branches': 0,
        'loops': 0,
        'cognitive_score': 0
    }
    
    # Count basic structures
    complexity['functions'] = len(re.findall(r'^\s*def\s+', content, re.MULTILINE))
    complexity['classes'] = len(re.findall(r'^\s*class\s+', content, re.MULTILINE))
    
    # Count control flow structures
    control_patterns = {
        'if': r'\bif\s+',
        'elif': r'\belif\s+',
        'else': r'\belse\s*:',
        'for': r'\bfor\s+',
        'while': r'\bwhile\s+',
        'try': r'\btry\s*:',
        'except': r'\bexcept\s*',
        'with': r'\bwith\s+'
    }
    
    for pattern in control_patterns.values():
        count = len(re.findall(pattern, content))
        complexity['branches'] += count
        complexity['cognitive_score'] += count
    
    # Calculate overall complexity score
    complexity['score'] = (
        complexity['cognitive_score'] +
        complexity['functions'] * 1.5 +
        complexity['classes'] * 2 +
        complexity['branches'] * 0.5
    )
    
    return complexity

@mcp.tool()
def monitor_performance(duration: int = 60, interval: float = 1.0) -> Dict[str, Any]:
    """
    Monitor system performance metrics
    
    Args:
        duration: Monitoring duration in seconds
        interval: Sampling interval in seconds
    
    Returns:
        Dictionary with performance metrics
    """
    try:
        import psutil
        from datetime import datetime, timedelta
        
        metrics = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'network': []
        }
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration)
        
        while datetime.now() < end_time:
            # CPU metrics
            metrics['cpu'].append({
                'timestamp': datetime.now().isoformat(),
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            })
            
            # Memory metrics
            mem = psutil.virtual_memory()
            metrics['memory'].append({
                'timestamp': datetime.now().isoformat(),
                'total': mem.total,
                'available': mem.available,
                'percent': mem.percent,
                'used': mem.used,
                'free': mem.free
            })
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics['disk'].append({
                'timestamp': datetime.now().isoformat(),
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            })
            
            # Network metrics
            net = psutil.net_io_counters()
            metrics['network'].append({
                'timestamp': datetime.now().isoformat(),
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
                'packets_sent': net.packets_sent,
                'packets_recv': net.packets_recv
            })
            
            time.sleep(interval)
        
        # Calculate summary statistics
        summary = {
            'cpu': {
                'avg': sum(m['percent'] for m in metrics['cpu']) / len(metrics['cpu']),
                'max': max(m['percent'] for m in metrics['cpu']),
                'min': min(m['percent'] for m in metrics['cpu'])
            },
            'memory': {
                'avg_percent': sum(m['percent'] for m in metrics['memory']) / len(metrics['memory']),
                'max_percent': max(m['percent'] for m in metrics['memory']),
                'min_available': min(m['available'] for m in metrics['memory'])
            },
            'disk': {
                'avg_percent': sum(m['percent'] for m in metrics['disk']) / len(metrics['disk']),
                'available': metrics['disk'][-1]['free']
            },
            'network': {
                'total_sent': metrics['network'][-1]['bytes_sent'] - metrics['network'][0]['bytes_sent'],
                'total_recv': metrics['network'][-1]['bytes_recv'] - metrics['network'][0]['bytes_recv']
            }
        }
        
        return {
            'status': 'success',
            'metrics': metrics,
            'summary': summary,
            'duration': duration,
            'samples': len(metrics['cpu'])
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def manage_llm_context(content: str, model: str = "claude-3-sonnet", max_tokens: int = None) -> Dict[str, Any]:
    """
    Advanced LLM context management and optimization
    
    Args:
        content: Text content to analyze and optimize
        model: Target LLM model
        max_tokens: Maximum desired tokens (defaults to model limit)
    
    Returns:
        Dictionary with context management results
    """
    try:
        # Model context limits
        model_limits = {
            'claude-3-opus': 200000,
            'claude-3-sonnet': 100000,
            'gpt-4': 128000,
            'gpt-3.5': 16000
        }
        
        if model not in model_limits:
            return {
                'status': 'error',
                'error': f'Unknown model: {model}'
            }
        
        # Use specified max_tokens or model limit
        token_limit = max_tokens or model_limits[model]
        
        # Analyze content
        words = content.split()
        chars = len(content)
        lines = content.count('\n') + 1
        
        # Estimate tokens (improved estimation)
        estimated_tokens = int(len(words) * 1.3)  # Rough approximation
        
        # Calculate context metrics
        metrics = {
            'estimated_tokens': estimated_tokens,
            'words': len(words),
            'characters': chars,
            'lines': lines,
            'usage_percent': (estimated_tokens / token_limit) * 100
        }
        
        # Generate optimization suggestions
        suggestions = []
        if estimated_tokens > token_limit:
            suggestions.append({
                'type': 'truncation',
                'message': f'Content exceeds {model} token limit by approximately {estimated_tokens - token_limit} tokens'
            })
            
            # Suggest specific optimizations
            if lines > 100:
                suggestions.append({
                    'type': 'structure',
                    'message': 'Consider reducing line count by combining related lines'
                })
            
            code_blocks = len(re.findall(r'```.*?```', content, re.DOTALL))
            if code_blocks > 5:
                suggestions.append({
                    'type': 'code',
                    'message': 'Consider reducing number of code blocks or showing only relevant portions'
                })
        
        # Optimize content if needed
        optimized_content = content
        if estimated_tokens > token_limit:
            optimized_content = _optimize_content(content, token_limit)
        
        return {
            'status': 'success',
            'metrics': metrics,
            'suggestions': suggestions,
            'optimized_content': optimized_content if optimized_content != content else None,
            'model': model,
            'token_limit': token_limit
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _optimize_content(content: str, token_limit: int) -> str:
    """Helper function to optimize content for token limit"""
    # Split content into sections
    sections = re.split(r'\n\s*\n', content)
    
    # Calculate approximate tokens per section
    section_tokens = [(s, int(len(s.split()) * 1.3)) for s in sections]
    
    # Sort sections by importance (keeping code blocks and error messages)
    def section_importance(section_tuple):
        section, _ = section_tuple
        if re.match(r'```.*?```', section, re.DOTALL):
            return 3  # Highest priority for code blocks
        if re.search(r'error|exception|warning|fail', section, re.IGNORECASE):
            return 2  # High priority for errors/warnings
        return 1  # Normal priority
    
    section_tokens.sort(key=section_importance, reverse=True)
    
    # Rebuild content within token limit
    optimized_sections = []
    current_tokens = 0
    
    for section, tokens in section_tokens:
        if current_tokens + tokens <= token_limit:
            optimized_sections.append(section)
            current_tokens += tokens
        elif tokens > 100:  # For large sections, try to keep important parts
            # Keep first and last few lines
            lines = section.split('\n')
            if len(lines) > 6:
                truncated = '\n'.join(lines[:3] + ['...'] + lines[-3:])
                truncated_tokens = int(len(truncated.split()) * 1.3)
                if current_tokens + truncated_tokens <= token_limit:
                    optimized_sections.append(truncated)
                    current_tokens += truncated_tokens
    
    return '\n\n'.join(optimized_sections)

@mcp.tool()
def enhanced_testing(test_type: str = "unit", coverage: bool = True, parallel: bool = True) -> Dict[str, Any]:
    """
    Enhanced testing support with coverage and parallel execution
    
    Args:
        test_type: Type of tests to run ("unit", "integration", "all")
        coverage: Whether to collect coverage data
        parallel: Whether to run tests in parallel
    
    Returns:
        Dictionary with test results and coverage data
    """
    try:
        cmd = ['pytest']
        
        # Add test selection based on type
        if test_type == "unit":
            cmd.extend(['-m', 'unit'])
        elif test_type == "integration":
            cmd.extend(['-m', 'integration'])
        
        # Add coverage if requested
        if coverage:
            cmd.extend(['--cov=.', '--cov-report=term-missing'])
        
        # Add parallel execution if requested
        if parallel:
            cmd.extend(['-n', 'auto'])
        
        # Add output capture and verbosity
        cmd.extend(['-v', '--capture=no'])
        
        # Run tests
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse test results
        test_results = _parse_test_output(result.stdout)
        
        # Parse coverage data if collected
        coverage_data = None
        if coverage and result.returncode == 0:
            coverage_data = _parse_coverage_output(result.stdout)
        
        return {
            'status': 'success' if result.returncode == 0 else 'failure',
            'test_results': test_results,
            'coverage': coverage_data,
            'exit_code': result.returncode,
            'errors': result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _parse_test_output(output: str) -> Dict[str, Any]:
    """Helper function to parse pytest output"""
    results = {
        'passed': [],
        'failed': [],
        'skipped': [],
        'warnings': [],
        'summary': {}
    }
    
    for line in output.split('\n'):
        if line.startswith('test_'):
            if 'PASSED' in line:
                results['passed'].append(line)
            elif 'FAILED' in line:
                results['failed'].append(line)
            elif 'SKIPPED' in line:
                results['skipped'].append(line)
        elif 'warning' in line.lower():
            results['warnings'].append(line)
        elif '===' in line and ('failed' in line or 'passed' in line):
            results['summary']['final'] = line.strip()
    
    # Calculate statistics
    results['summary']['total'] = len(results['passed']) + len(results['failed']) + len(results['skipped'])
    results['summary']['pass_rate'] = (len(results['passed']) / results['summary']['total'] * 100) if results['summary']['total'] > 0 else 0
    
    return results

def _parse_coverage_output(output: str) -> Dict[str, Any]:
    """Helper function to parse coverage output"""
    coverage_data = {
        'total': 0,
        'covered': 0,
        'missing': 0,
        'files': {}
    }
    
    coverage_section = False
    for line in output.split('\n'):
        if '---------- coverage:' in line:
            coverage_section = True
            continue
        
        if coverage_section and line.strip():
            if line.startswith('TOTAL'):
                parts = line.split()
                try:
                    coverage_data['total'] = int(parts[1])
                    coverage_data['covered'] = int(parts[2])
                    coverage_data['missing'] = int(parts[3])
                except (IndexError, ValueError):
                    pass
            elif '.py' in line:
                parts = line.split()
                try:
                    file_name = parts[0]
                    coverage_data['files'][file_name] = {
                        'statements': int(parts[1]),
                        'missing': int(parts[2]),
                        'coverage': int(parts[3].rstrip('%'))
                    }
                except (IndexError, ValueError):
                    pass
    
    return coverage_data

if __name__ == "__main__":
    # Set up the server
    import uvicorn
    print("Starting server from MAIN")
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
    # Only run the SSE transport when the script is run directly

    mcp.run(transport="sse")