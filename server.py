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

# Initialize the MCP server
mcp = FastMCP("Terminal Command Runner MCP")

# Store for active command sessions
active_sessions = {}
# Command blacklist (can be modified at runtime)
blacklisted_commands = set(['rm -rf /', 'mkfs'])
# Lock for thread safety
session_lock = threading.Lock()
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
def list_sessions() -> Dict[str, List[Dict[str, Any]]]:
    """
    List all active command sessions
    
    Returns:
        Dictionary with list of active sessions
    """
    with session_lock:
        # Convert to list to avoid dictionary changing during iteration
        sessions = list(active_sessions.values())
    
    # Add runtime to each session
    for session in sessions:
        start_time = datetime.fromisoformat(session["start_time"])
        runtime_seconds = (datetime.now() - start_time).total_seconds()
        session["runtime_seconds"] = round(runtime_seconds, 2)
    
    return {"sessions": sessions}

@mcp.tool()
def list_processes() -> Dict[str, List[Dict[str, Any]]]:
    """
    List all processes on the system
    
    Returns:
        Dictionary with list of processes
    """
    try:
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        processes = []
        for line in result.stdout.splitlines()[1:]:  # Skip header
            parts = line.split(None, 10)
            if len(parts) >= 11:
                process = {
                    "user": parts[0],
                    "pid": int(parts[1]),
                    "cpu": float(parts[2]),
                    "mem": float(parts[3]),
                    "vsz": parts[4],
                    "rss": parts[5],
                    "tty": parts[6],
                    "stat": parts[7],
                    "start": parts[8],
                    "time": parts[9],
                    "command": parts[10]
                }
                processes.append(process)
        
        return {"processes": processes}
    except Exception as e:
        return {"error": str(e), "processes": []}

@mcp.tool()
def kill_process(pid: int, signal_type: str = "TERM") -> Dict[str, Any]:
    """
    Kill a process by PID
    
    Args:
        pid: Process ID to kill
        signal_type: Signal to send ("TERM" for graceful, "KILL" for force)
    
    Returns:
        Dictionary with kill status
    """
    try:
        sig = signal.SIGTERM if signal_type == "TERM" else signal.SIGKILL
        os.kill(pid, sig)
        return {
            "success": True,
            "message": f"Process {pid} sent signal {signal_type}"
        }
    except ProcessLookupError:
        return {
            "success": False,
            "message": f"Process {pid} not found"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error killing process {pid}: {str(e)}"
        }

@mcp.tool()
def block_command(command: str) -> Dict[str, Any]:
    """
    Add a command pattern to the blacklist
    
    Args:
        command: Command pattern to block
    
    Returns:
        Dictionary with operation status
    """
    blacklisted_commands.add(command)
    return {
        "success": True,
        "message": f"Command pattern '{command}' added to blacklist",
        "current_blacklist": list(blacklisted_commands)
    }

@mcp.tool()
def unblock_command(command: str) -> Dict[str, Any]:
    """
    Remove a command pattern from the blacklist
    
    Args:
        command: Command pattern to unblock
    
    Returns:
        Dictionary with operation status
    """
    if command in blacklisted_commands:
        blacklisted_commands.remove(command)
        return {
            "success": True,
            "message": f"Command pattern '{command}' removed from blacklist",
            "current_blacklist": list(blacklisted_commands)
        }
    else:
        return {
            "success": False,
            "message": f"Command pattern '{command}' not found in blacklist",
            "current_blacklist": list(blacklisted_commands)
        }

# Filesystem Tools

@mcp.tool()
def read_file(path: str, max_size_mb: float = 10) -> Dict[str, Any]:
    """
    Read contents of a file
    
    Args:
        path: Path to the file
        max_size_mb: Maximum file size to read in MB
    
    Returns:
        Dictionary with file content or error
    """
    try:
        # Ensure the path exists and is a file
        if not os.path.exists(path):
            return {"success": False, "error": f"File not found: {path}"}
        
        if not os.path.isfile(path):
            return {"success": False, "error": f"Path is not a file: {path}"}
        
        # Check file size
        file_size_bytes = os.path.getsize(path)
        max_size_bytes = int(max_size_mb * 1024 * 1024)
        
        if file_size_bytes > max_size_bytes:
            return {
                "success": False, 
                "error": f"File size ({file_size_bytes / 1024 / 1024:.2f} MB) exceeds maximum allowed ({max_size_mb} MB)"
            }
        
        # Read the file
        with open(path, 'r', errors='replace') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "size_bytes": file_size_bytes,
            "path": path
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def write_file(path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
    """
    Write content to a file
    
    Args:
        path: Path to the file
        content: Content to write
        create_dirs: Whether to create parent directories if they don't exist
    
    Returns:
        Dictionary with operation status
    """
    try:
        # Ensure parent directory exists if requested
        if create_dirs:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # Write to the file
        with open(path, 'w') as f:
            f.write(content)
        
        return {
            "success": True,
            "message": f"Successfully wrote {len(content)} bytes to {path}",
            "path": path,
            "size_bytes": len(content)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def create_directory(path: str) -> Dict[str, Any]:
    """
    Create a directory
    
    Args:
        path: Path to create
    
    Returns:
        Dictionary with operation status
    """
    try:
        os.makedirs(path, exist_ok=True)
        return {
            "success": True,
            "message": f"Directory created: {path}",
            "path": path
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def list_directory(path: str, show_hidden: bool = False) -> Dict[str, Any]:
    """
    List contents of a directory
    
    Args:
        path: Directory to list
        show_hidden: Whether to include hidden files
    
    Returns:
        Dictionary with directory contents
    """
    try:
        if not os.path.exists(path):
            return {"success": False, "error": f"Path does not exist: {path}"}
        
        if not os.path.isdir(path):
            return {"success": False, "error": f"Path is not a directory: {path}"}
        
        items = []
        for item in os.listdir(path):
            # Skip hidden files if not requested
            if not show_hidden and item.startswith('.'):
                continue
            
            full_path = os.path.join(path, item)
            stats = os.stat(full_path)
            
            # Determine item type
            if os.path.isdir(full_path):
                item_type = "directory"
            elif os.path.islink(full_path):
                item_type = "symlink"
            elif os.path.isfile(full_path):
                item_type = "file"
            else:
                item_type = "other"
            
            # Format permissions
            mode = stats.st_mode
            perms = ""
            for who in "USR", "GRP", "OTH":
                for what in "R", "W", "X":
                    if mode & getattr(stat, "S_I" + what + who):
                        perms += what.lower()
                    else:
                        perms += "-"
            
            items.append({
                "name": item,
                "type": item_type,
                "full_path": full_path,
                "size_bytes": stats.st_size,
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "permissions": perms,
                "owner": stats.st_uid,
                "group": stats.st_gid
            })
        
        return {
            "success": True,
            "path": path,
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def move_file(source: str, destination: str) -> Dict[str, Any]:
    """
    Move or rename a file or directory
    
    Args:
        source: Source path
        destination: Destination path
    
    Returns:
        Dictionary with operation status
    """
    try:
        # Ensure source exists
        if not os.path.exists(source):
            return {"success": False, "error": f"Source path does not exist: {source}"}
        
        # Create parent directories if they don't exist
        dest_dir = os.path.dirname(destination)
        if dest_dir and not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
        
        # Move the file or directory
        shutil.move(source, destination)
        
        return {
            "success": True,
            "message": f"Successfully moved {source} to {destination}",
            "source": source,
            "destination": destination
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def search_files(directory: str, pattern: str, recursive: bool = True, max_results: int = 100) -> Dict[str, Any]:
    """
    Search for files matching a pattern
    
    Args:
        directory: Directory to search in
        pattern: Glob pattern for matching files
        recursive: Whether to search subdirectories
        max_results: Maximum number of results to return
    
    Returns:
        Dictionary with matching files
    """
    try:
        if not os.path.exists(directory) or not os.path.isdir(directory):
            return {"success": False, "error": f"Directory does not exist: {directory}"}
        
        # Prepare search path
        search_path = os.path.join(directory, "**", pattern) if recursive else os.path.join(directory, pattern)
        
        # Find matching files
        matches = []
        for path in glob.glob(search_path, recursive=recursive):
            if len(matches) >= max_results:
                break
                
            stats = os.stat(path)
            matches.append({
                "path": path,
                "size_bytes": stats.st_size,
                "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                "type": "directory" if os.path.isdir(path) else "file"
            })
        
        return {
            "success": True,
            "matches": matches,
            "count": len(matches),
            "pattern": pattern,
            "directory": directory,
            "truncated": len(matches) >= max_results
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def get_file_info(path: str) -> Dict[str, Any]:
    """
    Get detailed information about a file
    
    Args:
        path: Path to the file
    
    Returns:
        Dictionary with file information
    """
    try:
        if not os.path.exists(path):
            return {"success": False, "error": f"Path does not exist: {path}"}
        
        stats = os.stat(path)
        info = {
            "path": path,
            "exists": True,
            "size_bytes": stats.st_size,
            "type": "directory" if os.path.isdir(path) else "file",
            "is_symlink": os.path.islink(path),
            "created": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stats.st_atime).isoformat(),
            "owner": stats.st_uid,
            "group": stats.st_gid,
            "permissions_octal": oct(stats.st_mode)[-3:],
            "absolute_path": os.path.abspath(path)
        }
        
        # Add mime type for files
        if os.path.isfile(path):
            try:
                import magic
                info["mime_type"] = magic.from_file(path, mime=True)
            except ImportError:
                # Fall back to simple extension check if python-magic not available
                extension = os.path.splitext(path)[1].lower()
                mime_map = {
                    '.txt': 'text/plain',
                    '.py': 'text/x-python',
                    '.js': 'application/javascript',
                    '.html': 'text/html',
                    '.css': 'text/css',
                    '.json': 'application/json',
                    '.xml': 'application/xml',
                    '.md': 'text/markdown',
                    '.png': 'image/png',
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.gif': 'image/gif',
                    '.pdf': 'application/pdf'
                }
                info["mime_type"] = mime_map.get(extension, 'application/octet-stream')
        
        return {
            "success": True,
            "info": info
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# Edit Tools

@mcp.tool()
def edit_block(edit_block: str) -> Dict[str, Any]:
    """
    Apply surgical text replacements to a file
    
    Args:
        edit_block: Block of text with filepath and search/replace sections
                   Format:
                   filepath.ext
                   <<<<<<< SEARCH
                   existing code to replace
                   =======
                   new code to insert
                   >>>>>>> REPLACE
    
    Returns:
        Dictionary with edit operation status
    """
    try:
        # Parse the edit block
        lines = edit_block.strip().split('\n')
        
        if len(lines) < 5:  # Need at minimum: filename, search marker, search text, replace marker, replace text, end marker
            return {"success": False, "error": "Edit block format invalid: too few lines"}
        
        filepath = lines[0].strip()
        
        # Find the markers
        search_start = -1
        separator = -1
        replace_end = -1
        
        for i, line in enumerate(lines):
            if "<<<<<<< SEARCH" in line:
                search_start = i
            elif "=======" in line and search_start != -1 and separator == -1:
                separator = i
            elif ">>>>>>> REPLACE" in line and separator != -1:
                replace_end = i
                break
        
        if search_start == -1 or separator == -1 or replace_end == -1:
            return {"success": False, "error": "Edit block format invalid: missing markers"}
        
        # Extract search and replace strings
        search_text = "\n".join(lines[search_start + 1:separator])
        replace_text = "\n".join(lines[separator + 1:replace_end])
        
        # Read the original file
        if not os.path.exists(filepath):
            return {"success": False, "error": f"File not found: {filepath}"}
        
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            original_content = f.read()
        
        # Check if search text exists exactly once
        if search_text not in original_content:
            return {"success": False, "error": f"Search text not found in {filepath}"}
        
        if original_content.count(search_text) > 1:
            return {"success": False, "error": f"Search text appears multiple times in {filepath}, ambiguous which to replace"}
        
        # Make the replacement
        new_content = original_content.replace(search_text, replace_text)
        
        # Write back to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            "success": True,
            "message": f"Successfully updated {filepath}",
            "filepath": filepath,
            "chars_changed": len(new_content) - len(original_content)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# System Info

@mcp.resource("info://system")
def system_info() -> Dict[str, Any]:
    """Get detailed system information"""
    info = {
        "os": {
            "name": platform.system(),
            "version": platform.version(),
            "release": platform.release()
        },
        "python": platform.python_version(),
        "cpu": {
            "cores": os.cpu_count(),
            "architecture": platform.machine(),
            "processor": platform.processor()
        },
        "hostname": platform.node(),
        "time": {
            "now": datetime.now().isoformat(),
            "utc": datetime.utcnow().isoformat(),
            "uptime": None  # Will be filled if available
        }
    }
    
    # Try to get uptime
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        info["time"]["uptime"] = round(uptime_seconds)
    except:
        pass
    
    # Try to get memory info
    try:
        with open('/proc/meminfo', 'r') as f:
            mem_info = {}
            for line in f:
                key, value = line.split(':')
                mem_info[key.strip()] = value.strip()
        
        info["memory"] = {
            "total": mem_info.get("MemTotal", "N/A"),
            "free": mem_info.get("MemFree", "N/A"),
            "available": mem_info.get("MemAvailable", "N/A")
        }
    except:
        info["memory"] = "N/A"
    
    # Try to get disk usage
    try:
        usage = shutil.disk_usage('/')
        info["disk"] = {
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent_used": round(usage.used * 100 / usage.total, 2)
        }
    except:
        info["disk"] = "N/A"
    
    return info

# Add utility for calculating expressions
@mcp.tool()
def calculate(expression: str) -> Dict[str, Union[float, str]]:
    """
    Evaluate mathematical expressions
    
    Args:
        expression: Mathematical expression to evaluate
    
    Returns:
        Dictionary with the result or error
    """
    try:
        # Simple security check
        if any(keyword in expression for keyword in ['import', 'exec', 'eval', 'open', '__']):
            return {"error": "Potentially unsafe expression"}
        
        # Evaluate the expression
        result = eval(expression, {"__builtins__": {}}, {"abs": abs, "max": max, "min": min, "pow": pow, "round": round})
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Set up the server
    import uvicorn
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)