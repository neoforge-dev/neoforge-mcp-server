"""Tests for system utilities and miscellaneous features."""

import os
import sys
import pytest
import platform
import re
import time
import asyncio
from unittest.mock import patch, MagicMock
import psutil

# Import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import server
# Import from server.core
from server.utils.command_execution import CommandExecutor
from server.core import session_lock, active_sessions


def test_system_info():
    """Test retrieving system information."""
    result = server.system_info()
    
    # Verify the result contains expected fields
    assert "platform" in result
    assert "python_version" in result
    assert "system" in result
    assert "machine" in result
    assert "processor" in result
    assert "cpu_count" in result
    assert "hostname" in result
    
    # Verify some specific values
    assert result["python_version"] == platform.python_version()
    assert result["system"] == platform.system()
    

def test_calculate():
    """Test the calculate utility function."""
    # Test basic arithmetic
    result = server.calculate("2 + 3 * 4")
    assert result["result"] == 14
    
    # Test more complex expressions
    result = server.calculate("sqrt(16) + pow(2, 3)")
    assert result["result"] == 12.0
    
    # Test invalid expression
    result = server.calculate("invalid expression")
    assert "error" in result
    
    # Test potentially dangerous expressions
    result = server.calculate("__import__('os').system('echo hack')")
    assert "error" in result


@patch('builtins.open', new_callable=MagicMock)
def test_edit_block(mock_open):
    """Test the edit_block functionality."""
    # Setup mock
    mock_file_handle = MagicMock()
    mock_open.return_value.__enter__.return_value = mock_file_handle
    
    # Test edit block functionality
    edit_block = """
    @@ test_file.py
    # This is a test file
    def test_function():
        return "Hello World"
    """
    
    result = server.edit_block(edit_block)
    
    # Verify the function tried to write to the file
    assert result["success"] is True
    mock_open.assert_called_once()
    assert "test_file.py" in mock_open.call_args[0][0]
    mock_file_handle.write.assert_called()


def test_list_processes():
    """Test listing system processes."""
    result = server.list_processes()
    
    # Verify result structure
    assert "processes" in result
    assert isinstance(result["processes"], list)
    assert len(result["processes"]) > 0
    
    # Check first process has expected fields
    first_process = result["processes"][0]
    assert "pid" in first_process
    assert "name" in first_process
    assert "username" in first_process


@pytest.mark.skipif(sys.platform == "win32", reason="kill_process behaves differently on Windows")
@pytest.mark.skip(reason="Process termination is platform-specific and may not be reliable in test environments")
def test_kill_process():
    """Test killing a process by PID."""
    # Start a process
    if sys.platform == "win32":
        cmd = "ping -n 30 localhost"
    else:
        cmd = "sleep 30"
    
    result = server.execute_command(cmd, timeout=1, allow_background=True)
    assert result["pid"] is not None
    
    pid = result["pid"]
    
    # Make sure it's running 
    assert psutil.pid_exists(pid)
    
    # Kill the process with SIGTERM
    kill_result = server.kill_process(pid, signal_type="TERM")
    
    # Verify the result
    assert kill_result["success"] is True
    
    # Give some time for the process to terminate
    # We need a loop to wait because OS might take time to clean up
    max_wait = 10
    wait_count = 0
    process_still_running = True
    
    while process_still_running and wait_count < max_wait:
        try:
            os.kill(pid, 0)  # This will raise an error if the process is gone
            time.sleep(0.5)
            wait_count += 1
            # If process still exists after multiple attempts, forcefully kill it
            if wait_count >= 5:
                server.kill_process(pid, signal_type="KILL")
        except OSError:
            process_still_running = False
    
    assert not process_still_running, f"Process {pid} was not killed after {max_wait * 0.5} seconds"


@pytest.mark.skipif(not hasattr(server.core, 'list_sessions'), reason="list_sessions function not available")
def test_list_sessions_empty():
    """Test listing active command sessions when none are running."""
    # Create a new CommandExecutor instance for testing
    executor = CommandExecutor()
    
    # Clear any existing processes in the executor
    with executor._process_lock:
        executor._active_processes.clear()
    
    # Get process list
    processes_result = executor.list_processes()
    
    # Verify result
    assert "processes" in processes_result
    assert len(processes_result["processes"]) == 0
    assert processes_result["status"] == "success"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Process output streaming test is flaky due to timing and process management differences across environments")
async def test_process_output_streaming():
    """Test that process output is properly streamed through queues."""
    # Create a command that produces output over time
    if sys.platform == "win32":
        cmd = "for /L %i in (1,1,5) do @(echo Line %i & timeout /t 1 > nul)"
    else:
        cmd = "for i in $(seq 1 5); do echo Line $i; sleep 0.5; done"
    
    # Execute command
    result = server.execute_command(cmd, timeout=1, allow_background=True)
    assert result["pid"] is not None
    
    pid = result["pid"]
    
    # Read output multiple times to verify streaming
    outputs = []
    for _ in range(5):
        time.sleep(1)
        try:
            output_result = await server.read_output(pid)
            if output_result["stdout"]:
                outputs.append(output_result["stdout"])
        except Exception as e:
            print(f"Error reading output: {e}")
            break
    
    # Cleanup
    try:
        server.force_terminate(pid)
    except Exception as e:
        print(f"Error terminating process: {e}")
    
    # Verify we got at least some output
    assert len(outputs) > 0 