"""
Shared command execution utilities for MCP servers.
"""

import os
import signal
import subprocess
import threading
import queue
import time
from typing import Dict, Any, Optional, List, Tuple
from .error_handling import SecurityError, ResourceError, handle_exceptions, validate_command, check_resource_limits

# Default blacklisted commands
DEFAULT_BLACKLIST = {
    'rm -rf /',
    'mkfs',
    'dd if=/dev/zero',
    'chmod -R 777',
    'shutdown',
    'reboot',
    '> /dev/sda',
    'fork bomb',
    ':(){:|:&};:',
    'eval',
    'exec',
}

class CommandExecutor:
    """Handles safe command execution with proper isolation and monitoring."""
    
    def __init__(
        self,
        blacklist: Optional[set[str]] = None,
        max_runtime: int = 30,
        check_resources: bool = True,
        resource_limits: Optional[Dict[str, float]] = None
    ):
        """Initialize the command executor.
        
        Args:
            blacklist: Set of blacklisted command patterns
            max_runtime: Maximum runtime in seconds
            check_resources: Whether to check resource limits
            resource_limits: Resource limits (cpu_percent, memory_percent, disk_percent)
        """
        self.blacklist = blacklist or DEFAULT_BLACKLIST
        self.max_runtime = max_runtime
        self.check_resources = check_resources
        self.resource_limits = resource_limits or {
            "cpu_percent": 95.0,
            "memory_percent": 95.0,
            "disk_percent": 95.0
        }
        
        # Track active processes
        self._active_processes: Dict[int, Dict[str, Any]] = {}
        self._process_lock = threading.Lock()
        
    def _validate_command(self, command: str) -> None:
        """Validate command against security rules."""
        validate_command(command, self.blacklist)
        
    def _check_resources(self) -> None:
        """Check system resources before execution."""
        if self.check_resources:
            check_resource_limits(self.resource_limits)
            
    def _create_process(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[subprocess.Popen, queue.Queue, queue.Queue]:
        """Create a process with proper isolation."""
        # Create output queues
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        
        # Create process
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            env=env,
            preexec_fn=os.setsid
        )
        
        return process, stdout_queue, stderr_queue
        
    def _collect_output(
        self,
        stdout_queue: queue.Queue,
        stderr_queue: queue.Queue,
        timeout: Optional[float] = None
    ) -> Tuple[List[str], List[str]]:
        """Collect output from queues with timeout."""
        stdout_lines = []
        stderr_lines = []
        
        def collect_from_queue(q: queue.Queue, lines: List[str]) -> None:
            while True:
                try:
                    line = q.get_nowait()
                    if line is None:
                        break
                    lines.append(line)
                except queue.Empty:
                    break
                    
        # Collect output with timeout
        if timeout is not None:
            start_time = time.time()
            while time.time() - start_time < timeout:
                collect_from_queue(stdout_queue, stdout_lines)
                collect_from_queue(stderr_queue, stderr_lines)
                if not stdout_queue.empty() or not stderr_queue.empty():
                    time.sleep(0.1)
                else:
                    break
        else:
            collect_from_queue(stdout_queue, stdout_lines)
            collect_from_queue(stderr_queue, stderr_lines)
            
        return stdout_lines, stderr_lines
        
    def terminate(self, pid: int) -> None:
        """Terminate a process by PID."""
        with self._process_lock:
            if pid in self._active_processes:
                process = self._active_processes[pid]["process"]
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
                self._active_processes.pop(pid, None)
                
    @handle_exceptions(error_code="COMMAND_ERROR")
    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        allow_background: bool = False
    ) -> Dict[str, Any]:
        """Execute a command with proper isolation and monitoring.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            cwd: Working directory
            env: Environment variables
            allow_background: Whether to allow background execution
            
        Returns:
            Dictionary with execution results
        """
        # Validate command and check resources
        self._validate_command(command)
        self._check_resources()
        
        # Create process
        process, stdout_queue, stderr_queue = self._create_process(command, cwd, env)
        
        # Track process
        with self._process_lock:
            self._active_processes[process.pid] = {
                "process": process,
                "command": command,
                "start_time": time.time(),
                "stdout_queue": stdout_queue,
                "stderr_queue": stderr_queue
            }
            
        try:
            # Wait for process
            try:
                process.wait(timeout=timeout or self.max_runtime)
            except subprocess.TimeoutExpired:
                if not allow_background:
                    self.terminate(process.pid)
                    raise ResourceError(
                        f"Command timed out after {timeout or self.max_runtime} seconds",
                        {"pid": process.pid, "command": command}
                    )
                    
            # Collect output
            stdout_lines, stderr_lines = self._collect_output(
                stdout_queue,
                stderr_queue,
                timeout=1 if process.poll() is not None else None
            )
            
            return {
                "status": "success",
                "pid": process.pid,
                "returncode": process.poll(),
                "stdout": "".join(stdout_lines),
                "stderr": "".join(stderr_lines),
                "running": process.poll() is None
            }
            
        finally:
            # Clean up if process completed
            if process.poll() is not None:
                with self._process_lock:
                    self._active_processes.pop(process.pid, None)
                    
    @handle_exceptions(error_code="COMMAND_ERROR")
    def terminate(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """Terminate a running process.
        
        Args:
            pid: Process ID to terminate
            force: Whether to force kill the process
            
        Returns:
            Dictionary with termination status
        """
        with self._process_lock:
            if pid not in self._active_processes:
                raise ValueError(f"No active process found with PID {pid}")
                
            process_info = self._active_processes[pid]
            process = process_info["process"]
            
        try:
            if force:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                if not force:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    process.wait(timeout=1)
                    
            return {
                "status": "success",
                "message": f"Process {pid} terminated"
            }
            
        finally:
            with self._process_lock:
                self._active_processes.pop(pid, None)
                
    @handle_exceptions(error_code="COMMAND_ERROR")
    def get_output(self, pid: int) -> Dict[str, Any]:
        """Get output from a running process.
        
        Args:
            pid: Process ID
            
        Returns:
            Dictionary with process output
        """
        with self._process_lock:
            if pid not in self._active_processes:
                raise ValueError(f"No active process found with PID {pid}")
                
            process_info = self._active_processes[pid]
            process = process_info["process"]
            stdout_queue = process_info["stdout_queue"]
            stderr_queue = process_info["stderr_queue"]
            
        stdout_lines, stderr_lines = self._collect_output(stdout_queue, stderr_queue)
        
        return {
            "status": "success",
            "pid": pid,
            "stdout": "".join(stdout_lines),
            "stderr": "".join(stderr_lines),
            "running": process.poll() is None
        }
        
    @handle_exceptions(error_code="COMMAND_ERROR")
    def list_processes(self) -> Dict[str, Any]:
        """List all active processes.
        
        Returns:
            Dictionary with active processes
        """
        with self._process_lock:
            processes = []
            for pid, info in self._active_processes.items():
                process = info["process"]
                processes.append({
                    "pid": pid,
                    "command": info["command"],
                    "running": process.poll() is None,
                    "start_time": info["start_time"],
                    "duration": time.time() - info["start_time"]
                })
                
        return {
            "status": "success",
            "processes": processes
        } 