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

# Initialize the MCP server
mcp = FastMCP("Terminal Command Runner MCP", port=7443, log_level="DEBUG")

# Global variables for process management
session_lock = threading.Lock()
active_sessions = {}
blacklisted_commands = set(['rm -rf /', 'mkfs'])
output_queues = {}

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

if __name__ == "__main__":
    # Set up the server
    import uvicorn
    print("Starting server from MAIN")
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
    # Only run the SSE transport when the script is run directly
    mcp.run(transport="sse")