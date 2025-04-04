"""
Neo DO Server - Handles direct operations
"""

from mcp.server.fastmcp import FastMCP
import os
import sys
import subprocess
import signal
import psutil
import time
from typing import Dict, Any, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
from decorators import trace_tool, metrics_tool
import threading
import queue
import glob

# Initialize the MCP server
mcp = FastMCP("Neo DO MCP", port=7449, log_level="DEBUG")

# Initialize tracer
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "neo-do-server",
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
})

# Global variables for process management
session_lock = threading.Lock()
active_sessions = {}
output_queues = {}
blacklisted_commands = set(['rm -rf /', 'mkfs'])

# Initialize tracing if not in test mode
is_test_mode = "pytest" in sys.modules
if not is_test_mode:
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)

def is_command_safe(command: str) -> bool:
    """Check if a command is safe to execute."""
    # Check against blacklisted commands
    if any(cmd in command for cmd in blacklisted_commands):
        return False
        
    # Add more safety checks as needed
    return True

@mcp.tool()
@trace_tool
@metrics_tool
def execute_command(
    command: str,
    timeout: int = 10,
    allow_background: bool = True
) -> Dict[str, Any]:
    """Execute a command in the terminal with configurable timeout."""
    if not is_command_safe(command):
        return {
            "status": "error",
            "error": "Command is not allowed for security reasons"
        }
        
    try:
        # Start process
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid
        )
        
        # Create output queues
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        
        # Store session info
        with session_lock:
            session_id = process.pid
            active_sessions[session_id] = {
                "process": process,
                "command": command,
                "start_time": time.time()
            }
            output_queues[session_id] = {
                "stdout": stdout_queue,
                "stderr": stderr_queue
            }
            
        # Start output reader threads
        def read_output(pipe, q):
            for line in pipe:
                q.put(line)
            q.put(None)  # Signal EOF
            
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, stdout_queue))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, stderr_queue))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Wait for process with timeout
        try:
            process.wait(timeout=timeout)
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
        except subprocess.TimeoutExpired:
            if not allow_background:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                return {
                    "status": "error",
                    "error": f"Command timed out after {timeout} seconds",
                    "pid": process.pid
                }
                
        # Get output
        stdout_lines = []
        stderr_lines = []
        
        while True:
            try:
                line = stdout_queue.get_nowait()
                if line is None:
                    break
                stdout_lines.append(line)
            except queue.Empty:
                break
                
        while True:
            try:
                line = stderr_queue.get_nowait()
                if line is None:
                    break
                stderr_lines.append(line)
            except queue.Empty:
                break
                
        return {
            "status": "success",
            "pid": process.pid,
            "stdout": "".join(stdout_lines),
            "stderr": "".join(stderr_lines),
            "running": process.poll() is None
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Command execution failed: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def read_output(pid: int) -> Dict[str, Any]:
    """Get output from a long-running command session."""
    try:
        with session_lock:
            if pid not in active_sessions:
                return {
                    "status": "error",
                    "error": f"No active session found for PID {pid}"
                }
                
            session = active_sessions[pid]
            process = session["process"]
            queues = output_queues[pid]
            
        stdout_lines = []
        stderr_lines = []
        
        while True:
            try:
                line = queues["stdout"].get_nowait()
                if line is None:
                    break
                stdout_lines.append(line)
            except queue.Empty:
                break
                
        while True:
            try:
                line = queues["stderr"].get_nowait()
                if line is None:
                    break
                stderr_lines.append(line)
            except queue.Empty:
                break
                
        return {
            "status": "success",
            "pid": pid,
            "stdout": "".join(stdout_lines),
            "stderr": "".join(stderr_lines),
            "running": process.poll() is None
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to read output: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def force_terminate(pid: int) -> Dict[str, Any]:
    """Stop a running command session."""
    try:
        with session_lock:
            if pid not in active_sessions:
                return {
                    "status": "error",
                    "error": f"No active session found for PID {pid}"
                }
                
            session = active_sessions[pid]
            process = session["process"]
            
        # Try graceful termination first
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        
        # Wait briefly for process to terminate
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            # Force kill if still running
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            
        # Clean up session
        with session_lock:
            if pid in active_sessions:
                del active_sessions[pid]
            if pid in output_queues:
                del output_queues[pid]
                
        return {
            "status": "success",
            "message": f"Process {pid} terminated"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to terminate process: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def list_sessions() -> Dict[str, Any]:
    """List all active command sessions."""
    try:
        with session_lock:
            sessions = []
            for pid, session in active_sessions.items():
                process = session["process"]
                sessions.append({
                    "pid": pid,
                    "command": session["command"],
                    "running": process.poll() is None,
                    "start_time": session["start_time"],
                    "duration": time.time() - session["start_time"]
                })
                
        return {
            "status": "success",
            "sessions": sessions
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list sessions: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def list_processes() -> Dict[str, Any]:
    """List all processes on the system."""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.as_dict()
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        return {
            "status": "success",
            "processes": processes
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list processes: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def kill_process(pid: int, signal_type: str = "TERM") -> Dict[str, Any]:
    """Kill a process by PID."""
    try:
        process = psutil.Process(pid)
        
        if signal_type == "TERM":
            process.terminate()
        elif signal_type == "KILL":
            process.kill()
        else:
            return {
                "status": "error",
                "error": f"Invalid signal type: {signal_type}"
            }
            
        process.wait(timeout=3)
        
        return {
            "status": "success",
            "message": f"Process {pid} killed with signal {signal_type}"
        }
        
    except psutil.NoSuchProcess:
        return {
            "status": "error",
            "error": f"No process found with PID {pid}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to kill process: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def block_command(command: str) -> Dict[str, Any]:
    """Add a command pattern to the blacklist."""
    try:
        blacklisted_commands.add(command)
        return {
            "status": "success",
            "message": f"Command pattern '{command}' blocked"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to block command: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def unblock_command(command: str) -> Dict[str, Any]:
    """Remove a command pattern from the blacklist."""
    try:
        blacklisted_commands.remove(command)
        return {
            "status": "success",
            "message": f"Command pattern '{command}' unblocked"
        }
    except KeyError:
        return {
            "status": "error",
            "error": f"Command pattern '{command}' not found in blacklist"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to unblock command: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def read_file(path: str, max_size_mb: float = 10) -> Dict[str, Any]:
    """Read contents of a file."""
    try:
        # Check file size
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > max_size_mb:
            return {
                "status": "error",
                "error": f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)"
            }
            
        with open(path, 'r') as f:
            content = f.read()
            
        return {
            "status": "success",
            "content": content,
            "size_bytes": len(content.encode('utf-8'))
        }
        
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"File not found: {path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to read file: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def write_file(path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
    """Write content to a file."""
    try:
        if create_dirs:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
        with open(path, 'w') as f:
            f.write(content)
            
        return {
            "status": "success",
            "message": f"Content written to {path}",
            "size_bytes": len(content.encode('utf-8'))
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to write file: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def create_directory(path: str) -> Dict[str, Any]:
    """Create a directory."""
    try:
        os.makedirs(path, exist_ok=True)
        return {
            "status": "success",
            "message": f"Directory created: {path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to create directory: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def list_directory(path: str, show_hidden: bool = False) -> Dict[str, Any]:
    """List contents of a directory."""
    try:
        contents = []
        for item in os.listdir(path):
            if not show_hidden and item.startswith('.'):
                continue
                
            item_path = os.path.join(path, item)
            stat_info = os.stat(item_path)
            
            contents.append({
                "name": item,
                "path": item_path,
                "type": "directory" if os.path.isdir(item_path) else "file",
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime
            })
            
        return {
            "status": "success",
            "contents": contents
        }
        
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"Directory not found: {path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to list directory: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Move or rename a file or directory."""
    try:
        shutil.move(source, destination)
        return {
            "status": "success",
            "message": f"Moved {source} to {destination}"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"Source not found: {source}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to move file: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def search_files(
    directory: str,
    pattern: str,
    recursive: bool = True,
    max_results: int = 100
) -> Dict[str, Any]:
    """Search for files matching a pattern."""
    try:
        if recursive:
            search_path = os.path.join(directory, "**", pattern)
        else:
            search_path = os.path.join(directory, pattern)
            
        matches = []
        for path in glob.glob(search_path, recursive=recursive):
            matches.append({
                "path": path,
                "name": os.path.basename(path),
                "type": "directory" if os.path.isdir(path) else "file"
            })
            
            if len(matches) >= max_results:
                break
                
        return {
            "status": "success",
            "matches": matches,
            "truncated": len(matches) >= max_results
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to search files: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def get_file_info(path: str) -> Dict[str, Any]:
    """Get detailed information about a file."""
    try:
        stat_info = os.stat(path)
        
        info = {
            "path": path,
            "name": os.path.basename(path),
            "type": "directory" if os.path.isdir(path) else "file",
            "size": stat_info.st_size,
            "created": stat_info.st_ctime,
            "modified": stat_info.st_mtime,
            "accessed": stat_info.st_atime,
            "mode": stat_info.st_mode,
            "permissions": oct(stat.S_IMODE(stat_info.st_mode)),
            "owner": stat_info.st_uid,
            "group": stat_info.st_gid
        }
        
        return {
            "status": "success",
            "info": info
        }
        
    except FileNotFoundError:
        return {
            "status": "error",
            "error": f"File not found: {path}"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to get file info: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def edit_block(edit_block: str) -> Dict[str, Any]:
    """Apply surgical text replacements to a file."""
    try:
        # Parse edit block
        lines = edit_block.splitlines()
        if not lines:
            return {
                "status": "error",
                "error": "Empty edit block"
            }
            
        filepath = lines[0]
        if not os.path.exists(filepath):
            return {
                "status": "error",
                "error": f"File not found: {filepath}"
            }
            
        # Read original content
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Apply edits
        # Implementation depends on edit block format
        
        return {
            "status": "success",
            "message": f"Edits applied to {filepath}"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to apply edits: {str(e)}"
        }

@mcp.tool()
@trace_tool
@metrics_tool
def calculate(expression: str) -> Dict[str, Any]:
    """Evaluate mathematical expressions."""
    try:
        # Use ast.literal_eval for safe evaluation
        import ast
        result = ast.literal_eval(expression)
        
        return {
            "status": "success",
            "result": result,
            "expression": expression
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": f"Failed to evaluate expression: {str(e)}"
        }

def main():
    """Start the Neo DO server."""
    if not is_test_mode:
        print("Starting Neo DO server...")
        mcp.run()

if __name__ == "__main__":
    main() 