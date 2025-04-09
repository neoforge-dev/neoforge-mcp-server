"""
Shared command execution utilities for MCP servers.
"""

import os
import signal
import subprocess
import threading
import queue
import time
import sys
from typing import Dict, Any, Optional, List, Tuple
from .error_handling import SecurityError, ResourceError, handle_exceptions, validate_command, check_resource_limits
from .security import is_command_safe

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
            blacklist: Set of blacklisted command patterns (DEPRECATED - Use global blacklist in security.py)
            max_runtime: Maximum runtime in seconds
            check_resources: Whether to check resource limits
            resource_limits: Resource limits (cpu_percent, memory_percent, disk_percent)
        """
        # The instance blacklist is no longer used, relying on the global one in security.py
        # self.blacklist = blacklist or DEFAULT_BLACKLIST 
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
        # Check against the dynamic global blacklist first
        # Use the security utility function directly
        # Pass only the command; the function handles global + default lists
        if not is_command_safe(command):
            raise SecurityError(f"Command '{command}' is blocked by global blacklist.")

        # Original check against instance blacklist (commented out as is_command_safe handles it)
        # if command in self.blacklist:
        #     raise SecurityError(f"Command '{command}' is blocked by instance blacklist.")
        
    def _check_resources(self) -> None:
        """Check system resources before execution."""
        if self.check_resources and self.resource_limits:
            # Unpack the dictionary into keyword arguments
            check_resource_limits(**self.resource_limits)
        elif self.check_resources:
            # Call with defaults if no limits dict provided
            check_resource_limits()
            
    def _reader_thread(self, pipe, q):
        """Target function for reader threads."""
        try:
            for line in iter(pipe.readline, ''):
                q.put(line)
        finally:
            pipe.close()
            q.put(None) # Signal end of output
            
    def _create_process(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None
    ) -> Tuple[subprocess.Popen, queue.Queue, queue.Queue]:
        """Create a process with proper isolation and output readers."""
        # Create output queues
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        
        # Create process
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, # Ensure pipes are in text mode
            cwd=cwd,
            env=env,
            # Use setsid only on non-Windows
            preexec_fn=os.setsid if sys.platform != "win32" else None 
        )
        
        # Start reader threads
        stdout_thread = threading.Thread(
            target=self._reader_thread, 
            args=(process.stdout, stdout_queue), 
            daemon=True # Ensure threads exit when main program exits
        )
        stderr_thread = threading.Thread(
            target=self._reader_thread, 
            args=(process.stderr, stderr_queue),
            daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        
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
                except Exception as e:
                    # Log unexpected errors during simple terminate
                    print(f"Error during simple terminate for {pid}: {e}")
                finally:
                    # Always try to remove from tracking
                    self._active_processes.pop(pid, None)

    def terminate(self, pid: int, force: bool = False) -> Dict[str, Any]:
        """Terminate a running process, with optional force kill.
        This is the primary method called by execute on timeout.
        
        Args:
            pid: Process ID to terminate
            force: Whether to force kill the process
            
        Returns:
            Dictionary with termination status
        """
        with self._process_lock:
            if pid not in self._active_processes:
                # Consider logging a warning here instead of raising ValueError?
                # If execute timed out, the process might have finished *just* before terminate was called.
                # Raising ValueError might mask the original timeout error in execute.
                # For now, return an error status consistent with execute's handling.
                return {"status": "error", "error": f"No active process found with PID {pid} to terminate.", "error_code": "NOT_FOUND"}
                
            process_info = self._active_processes[pid]
            process = process_info["process"]
            command = process_info.get("command", "<unknown>") # Get command for logging
            
        terminated_signal = signal.SIGTERM
        try:
            pgid = os.getpgid(process.pid)
            print(f"Attempting to terminate process group {pgid} (PID {pid}) for command: {command}")
            if force:
                print(f"Using SIGKILL for process group {pgid}")
                terminated_signal = signal.SIGKILL
                os.killpg(pgid, signal.SIGKILL)
            else:
                print(f"Using SIGTERM for process group {pgid}")
                os.killpg(pgid, signal.SIGTERM)
                
            # Wait for the process to actually terminate
            try:
                process.wait(timeout=3)
                print(f"Process group {pgid} (PID {pid}) terminated successfully after {terminated_signal.name}.")
                return {
                    "status": "success",
                    "message": f"Process {pid} terminated with {terminated_signal.name}"
                }
            except subprocess.TimeoutExpired:
                print(f"Process group {pgid} (PID {pid}) did not terminate after 3s with {terminated_signal.name}.")
                if not force:
                    print(f"Forcing termination with SIGKILL for process group {pgid}.")
                    try:
                        os.killpg(pgid, signal.SIGKILL)
                        process.wait(timeout=1) # Short wait after SIGKILL
                        print(f"Process group {pgid} (PID {pid}) force-terminated with SIGKILL.")
                        return {
                            "status": "success",
                            "message": f"Process {pid} force-terminated with SIGKILL after SIGTERM timeout"
                        }
                    except ProcessLookupError:
                        print(f"Process group {pgid} (PID {pid}) disappeared after SIGKILL attempt.")
                        return {"status": "success", "message": f"Process {pid} disappeared after SIGKILL attempt"}
                    except subprocess.TimeoutExpired:
                        print(f"ERROR: Process group {pgid} (PID {pid}) failed to terminate even after SIGKILL.")
                        # Still need to remove from tracking, but report failure
                        return {"status": "error", "error": f"Failed to terminate process {pid} even with SIGKILL", "error_code": "TERMINATE_FAILED"}
                    except Exception as e_kill:
                        print(f"ERROR during SIGKILL for {pgid} (PID {pid}): {e_kill}")
                        return {"status": "error", "error": f"Error during SIGKILL for process {pid}: {e_kill}", "error_code": "TERMINATE_ERROR"}
                else:
                    # Already tried force (SIGKILL), but it timed out
                    print(f"ERROR: Process group {pgid} (PID {pid}) failed to terminate after initial SIGKILL.")
                    return {"status": "error", "error": f"Process {pid} failed to terminate after SIGKILL", "error_code": "TERMINATE_FAILED"}

        except ProcessLookupError:
            # Process likely finished between check and killpg
            print(f"Process group/PID {pid} not found during termination attempt. Already finished? Command: {command}")
            return {"status": "success", "message": f"Process {pid} already finished before termination."}
        except Exception as e:
            print(f"ERROR during termination of process group for PID {pid}: {e}")
            # Still try to clean up tracking
            return {"status": "error", "error": f"Unexpected error terminating process {pid}: {e}", "error_code": "TERMINATE_ERROR"}

        finally:
            # Always remove the process from tracking, regardless of termination success/failure
            with self._process_lock:
                self._active_processes.pop(pid, None)
                print(f"Removed PID {pid} from active process tracking.")

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
        
    def list_processes(self) -> Dict[str, Any]:
        """List all active processes.
        
        Returns:
            Dictionary with active processes
        """
        try:
            with self._process_lock:
                processes = []
                # Use .items() for potentially slightly better performance if dict is large
                for pid, info in self._active_processes.items(): 
                    process = info.get("process")
                    if process:
                        is_running = process.poll() is None
                        current_status = info.get("status", "unknown") # Get tracked status
                        # Update status if process finished but wasn't cleaned up yet
                        if not is_running and current_status == "running":
                             current_status = "finished" # Or derive from poll() if needed
                        
                        processes.append({
                            "pid": pid,
                            "command": info.get("command", "<unknown>"),
                            "running": is_running, # Keep 'running' for consistency?
                            "status": current_status, # Add the status field
                            "start_time": info.get("start_time", 0),
                            "duration": time.time() - info.get("start_time", time.time())
                        })
                    else:
                        print(f"Warning: Process object missing for PID {pid} in _active_processes.")

            return {
                "status": "success",
                "processes": processes
            }
        except Exception as e:
             print(f"Error during list_processes: {e}")
             return {"status": "error", "error": f"Failed to list processes: {e}", "error_code": "LIST_ERROR"}

    # --- New method for true background execution ---
    def start_background(
        self,
        command: str,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Start a command in the background without waiting for it.

        Args:
            command: Command to execute
            cwd: Working directory
            env: Environment variables

        Returns:
            Dictionary with process PID and status.
        """
        try:
            # Validate command and check resources
            self._validate_command(command)
            self._check_resources()
        except (SecurityError, ResourceError) as e:
            print(f"Pre-execution check failed for background command '{command}': {e}")
            return {"status": "error", "error": str(e), "error_code": getattr(e, 'error_code', 'PREFLIGHT_ERROR'), "pid": None}
        except Exception as e_preflight:
            print(f"Unexpected pre-flight error for background command '{command}': {e_preflight}")
            return {"status": "error", "error": f"Unexpected pre-flight check error: {e_preflight}", "error_code": "PREFLIGHT_UNEXPECTED", "pid": None}

        process = None
        pid = None
        try:
            # Create process
            process, stdout_queue, stderr_queue = self._create_process(command, cwd, env)
            pid = process.pid
            print(f"Started background process {pid} for command: {command}")

            # Track process
            with self._process_lock:
                self._active_processes[pid] = {
                    "process": process,
                    "command": command,
                    "start_time": time.time(),
                    "stdout_queue": stdout_queue,
                    "stderr_queue": stderr_queue,
                    "status": "running" # Initial status
                }

            # Return immediately without waiting
            return {
                "status": "success", # Indicates successful launch
                "pid": pid,
                "message": f"Command '{command}' started in background with PID {pid}"
            }

        except Exception as e_runtime:
            # Catch errors during process creation/tracking
            print(f"Runtime error starting background command '{command}' (PID: {pid}): {e_runtime}")
            # No need to terminate here as process likely didn't start fully or track
            return {"status": "error", "error": f"Runtime error starting background command: {e_runtime}", "error_code": "RUNTIME_UNEXPECTED", "pid": pid}

    def execute(
        self,
        command: str,
        timeout: Optional[int] = None,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        allow_background: bool = False
    ) -> Dict[str, Any]:
        """Execute a command synchronously with proper isolation and monitoring.
        Handles validation, resource checks, execution, timeout, and output collection.
        
        Args:
            command: Command to execute
            timeout: Timeout in seconds
            cwd: Working directory
            env: Environment variables
            allow_background: Whether to allow background execution
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Validate command and check resources
            self._validate_command(command)
            self._check_resources()
        except (SecurityError, ResourceError) as e:
            # If validation/resource check fails, return error immediately
            print(f"Pre-execution check failed for command '{command}': {e}")
            # Format error using the utility function if available, else basic dict
            if 'format_error_response' in globals():
                return format_error_response(e)
            else:
                return {"status": "error", "error": str(e), "error_code": getattr(e, 'error_code', 'PREFLIGHT_ERROR'), "details": getattr(e, 'details', {})}
        except Exception as e_preflight:
            # Catch any other unexpected preflight errors
            print(f"Unexpected pre-flight error for command '{command}': {e_preflight}")
            return {"status": "error", "error": f"Unexpected pre-flight check error: {e_preflight}", "error_code": "PREFLIGHT_UNEXPECTED"}

        # Proceed with execution if preflight checks pass
        process = None
        pid = None
        try:
            # Create process
            process, stdout_queue, stderr_queue = self._create_process(command, cwd, env)
            pid = process.pid
            print(f"Started process {pid} for command: {command}")
            
            # Track process
            with self._process_lock:
                self._active_processes[pid] = {
                    "process": process,
                    "command": command,
                    "start_time": time.time(),
                    "stdout_queue": stdout_queue,
                    "stderr_queue": stderr_queue
                }
                
            # Wait for process with timeout
            effective_timeout = timeout if timeout is not None else self.max_runtime
            try:
                print(f"Waiting for process {pid} with timeout {effective_timeout}s...")
                process.wait(timeout=effective_timeout)
                print(f"Process {pid} completed with return code {process.poll()}. ")
            except subprocess.TimeoutExpired:
                print(f"Process {pid} timed out after {effective_timeout} seconds.")
                if not allow_background:
                    print(f"Timeout exceeded for foreground process {pid}. Terminating...")
                    # Call the *synchronous* second terminate method
                    terminate_result = self.terminate(pid, force=False)
                    print(f"Termination result for {pid}: {terminate_result}")
                    # Return a specific timeout error, potentially including termination info
                    return {
                        "status": "error",
                        "error": f"Command timed out after {effective_timeout} seconds and was terminated.",
                        "error_code": "TIMEOUT_TERMINATED",
                        "pid": pid,
                        "termination_details": terminate_result
                    }
                else:
                    # Background process timed out, but we let it continue running
                    print(f"Process {pid} allowed to run in background after timeout.")
                    # We will still collect output gathered so far and return
           
            # --- Output Collection (Runs after wait/timeout) ---          
            print(f"Collecting output for process {pid}...")
            # Collect output - give a short grace period even if process finished/timed out
            stdout_lines, stderr_lines = self._collect_output(
                stdout_queue,
                stderr_queue,
                timeout=1 # Collect for up to 1 sec after process ends/times out
            )
            print(f"Collected {len(stdout_lines)} stdout lines, {len(stderr_lines)} stderr lines for {pid}.")
            
            # Determine final status
            return_code = process.poll() # Check final exit code
            is_running = return_code is None
            if is_running and allow_background:
                 final_status = "success" # Backgrounded process still running is okay
            elif not is_running and return_code == 0:
                 final_status = "success" # Completed successfully
            else:
                 final_status = "error" # Completed with error OR still running unexpectedly (not backgrounded)

            # Construct result dictionary
            result = {
                "status": final_status,
                "pid": pid,
                "returncode": return_code,
                "stdout": "".join(stdout_lines),
                "stderr": "".join(stderr_lines),
                "running": is_running
            }
            if final_status == "error" and return_code is not None and return_code != 0:
                result["error"] = f"Command exited with non-zero status: {return_code}"
                result["error_code"] = "NON_ZERO_EXIT"

            return result
            
        except Exception as e_runtime:
            # Catch unexpected errors during process creation or management
            print(f"Runtime error during execution of command '{command}' (PID: {pid}): {e_runtime}")
            # Ensure process is terminated if it started
            if pid is not None and process is not None and process.poll() is None:
                print(f"Attempting cleanup termination for PID {pid} due to runtime error...")
                self.terminate(pid, force=True) # Force kill on unexpected error
            return {"status": "error", "error": f"Runtime execution error: {e_runtime}", "error_code": "RUNTIME_UNEXPECTED", "pid": pid}

        finally:
            # Final check to clean up tracking if process finished, 
            # but wasn't caught by earlier finally block (e.g., background timeout)
            if pid is not None and process is not None and process.poll() is not None:
                with self._process_lock:
                    if pid in self._active_processes:
                        print(f"Final tracking cleanup for completed process {pid}.")
                        self._active_processes.pop(pid, None) 