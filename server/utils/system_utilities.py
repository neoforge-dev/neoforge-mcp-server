"""Utility functions for system information and operations."""

import platform
import socket
import os
import psutil
import re
import math
import sys
import signal
from typing import Dict, Any, List, Optional


def system_info() -> Dict[str, Any]:
    """
    Get system information.
    
    Returns:
        Dictionary with system information details
    """
    try:
        return {
            "success": True,
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": psutil.cpu_count(logical=True),
            "hostname": socket.gethostname(),
            "memory_total": psutil.virtual_memory().total,
            "memory_available": psutil.virtual_memory().available,
            "disk_usage": {
                "total": psutil.disk_usage('/').total,
                "used": psutil.disk_usage('/').used,
                "free": psutil.disk_usage('/').free,
                "percent": psutil.disk_usage('/').percent
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def calculate(expression: str) -> Dict[str, Any]:
    """
    Evaluate a mathematical expression.
    
    Args:
        expression: The mathematical expression to evaluate
        
    Returns:
        Dictionary with result or error
    """
    # Add security by restricting allowed names and functions
    allowed_names = {
        'abs': abs,
        'max': max,
        'min': min,
        'pow': pow,
        'round': round,
        'sum': sum,
    }
    
    # Add math functions
    for name in dir(math):
        if not name.startswith('_'):
            allowed_names[name] = getattr(math, name)
    
    # Check for suspicious patterns in the expression
    suspicious_patterns = [
        r'__', r'import', r'eval', r'exec', r'compile', r'open',
        r'file', r'os', r'sys', r'subprocess', r'getattr', r'setattr',
        r'delattr', r'hasattr', r'globals', r'locals', r'dir'
    ]
    
    if any(re.search(pattern, expression) for pattern in suspicious_patterns):
        return {
            "success": False,
            "error": "Expression contains forbidden patterns"
        }
    
    try:
        # Evaluate the expression with restricted globals
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def edit_block(edit_block: str) -> Dict[str, Any]:
    """
    Apply edits to a file using a diff-like syntax.
    
    Args:
        edit_block: The edit block with file name and content
        
    Returns:
        Dictionary with success status and details
    """
    try:
        # Parse the edit block
        lines = edit_block.strip().split('\n')
        
        # Check for file marker
        file_markers = [line for line in lines if line.strip().startswith('@@')]
        if not file_markers:
            return {"success": False, "error": "No file marker (@@) found in edit block"}
        
        # Extract file path (remove @@ and whitespace)
        file_path = file_markers[0].strip()[2:].strip()
        
        # Get content (skip the file marker line)
        content = '\n'.join([line for line in lines if not line.strip().startswith('@@')])
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Write content to file
        with open(file_path, 'w') as f:
            f.write(content)
            
        return {
            "success": True,
            "file": file_path,
            "lines_changed": len(content.split('\n'))
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "file": file_path if 'file_path' in locals() else None
        }


def list_processes() -> Dict[str, Any]:
    """
    List current running processes.
    
    Returns:
        Dictionary with list of process information
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'status', 'cpu_percent', 'memory_percent']):
            processes.append({
                "pid": proc.info['pid'],
                "name": proc.info['name'],
                "username": proc.info['username'],
                "status": proc.info['status'],
                "cpu_percent": proc.info['cpu_percent'],
                "memory_percent": proc.info['memory_percent']
            })
        
        return {
            "status": "success",
            "processes": processes
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def kill_process(pid: int, signal_type: str = "TERM") -> Dict[str, Any]:
    """
    Kill a process by PID.
    
    Args:
        pid: Process ID to kill
        signal_type: Signal type (TERM, KILL)
        
    Returns:
        Dictionary with success status
    """
    try:
        # Validate PID
        if not isinstance(pid, int) or pid <= 0:
            return {
                "success": False,
                "error": f"Invalid PID: {pid}"
            }
        
        # Validate signal type
        signal_map = {
            "TERM": signal.SIGTERM,
            "KILL": signal.SIGKILL,
            "INT": signal.SIGINT,
            "HUP": signal.SIGHUP
        }
        
        if signal_type not in signal_map:
            return {
                "success": False,
                "error": f"Invalid signal type: {signal_type}. Must be one of {', '.join(signal_map.keys())}"
            }
        
        # Check if process exists
        if not psutil.pid_exists(pid):
            return {
                "success": False,
                "error": f"No process with PID {pid} exists"
            }
        
        # Get process group ID
        try:
            pgid = os.getpgid(pid)
        except Exception:
            # If we can't get the process group ID, just kill the process
            pgid = None
        
        # Kill the process group if possible, otherwise just the process
        if pgid is not None and pgid != 1:  # Avoid killing init
            os.killpg(pgid, signal_map[signal_type])
        else:
            os.kill(pid, signal_map[signal_type])
        
        return {
            "success": True,
            "pid": pid,
            "signal": signal_type
        }
    except ProcessLookupError:
        return {
            "success": False,
            "error": f"Process with PID {pid} not found"
        }
    except PermissionError:
        return {
            "success": False,
            "error": f"Permission denied to kill process with PID {pid}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        } 