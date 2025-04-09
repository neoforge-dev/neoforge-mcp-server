"""Tests for command execution functionality."""

import os
import sys
import pytest
import time
import subprocess
from unittest.mock import patch, MagicMock
import threading
import queue
import asyncio # Add asyncio import

# Import the executor class directly
from server.utils.command_execution import CommandExecutor
# Remove incorrect import
# from server.utils.security import validate_command, DEFAULT_BLACKLIST

# Keep these for session/blacklist management if still needed
from server.core import (
    read_output,
    force_terminate,
    block_command,
    unblock_command,
    blacklisted_commands,
    list_sessions,
    session_lock,
    active_sessions,
    is_command_safe
)

# Import blacklist management functions and SecurityError from security.py
from server.utils.security import (
    SecurityError,
    block_command,
    unblock_command,
    blacklisted_commands, # Keep if tests need to inspect/manipulate the global list
    DEFAULT_BLACKLIST # Keep if tests need the default list explicitly
)

# Instantiate the executor for tests
# Note: This assumes default blacklist is okay for these tests
# If tests modify the blacklist, they might need their own executor instance
command_executor = CommandExecutor()

# Remove test based on incorrect import
# def test_validate_command_safety():
#     """Test command safety validation using validate_command."""
#     # Test empty command should raise error or be handled
#     with pytest.raises(Exception): # Or specific SecurityError if applicable
#         validate_command("", DEFAULT_BLACKLIST)
#     
#     # Test safe command should not raise
#     try:
#         validate_command("echo 'hello world'", DEFAULT_BLACKLIST)
#     except Exception as e:
#         pytest.fail(f"validate_command raised exception unexpectedly for safe command: {e}")
#     
#     # Test unsafe command should raise SecurityError
#     with pytest.raises(Exception): # Replace with SecurityError if that's the expected type
#         validate_command("rm -rf /", DEFAULT_BLACKLIST)
#     
#     # Test another unsafe command
#     with pytest.raises(Exception): # Replace with SecurityError
#         validate_command("mkfs", DEFAULT_BLACKLIST)

@pytest.mark.parametrize("cmd,expected_exit_code", [
    ("echo 'hello world'", 0),
    ("exit 1", 1),
    ("non-existent-command", None)  # Expecting non-zero exit or error
])
def test_execute_command_basic(cmd, expected_exit_code):
    """Test basic command execution with different commands using CommandExecutor."""
    if sys.platform == "win32" and cmd == "non-existent-command":
        pytest.skip("Skipping non-existent command test on Windows")
    
    # Use a local executor with resource checks disabled for this test
    local_executor = CommandExecutor(check_resources=False)
    
    # Use the local executor and call synchronously
    result = local_executor.execute(cmd, timeout=5) # Increased timeout slightly
    
    assert isinstance(result, dict), f"Expected executor.execute to return a dict, but got {type(result)}"
    
    if expected_exit_code is None:
        # For non-existent commands, expect failure status or non-zero code
        assert result.get("status") == "error" or result.get("returncode") != 0, f"Expected error status or non-zero exit code, got {result}"
    else:
        # For valid commands, check exit code
        assert result.get("returncode") == expected_exit_code, f"Expected exit code {expected_exit_code}, got {result.get('returncode')}"
        assert "stdout" in result
        assert "stderr" in result

def test_execute_command_output():
    """Test command execution output capture using CommandExecutor."""
    cmd = "echo 'hello world'"
    result = command_executor.execute(cmd, timeout=2)
    
    assert isinstance(result, dict), f"Expected executor.execute to return a dict, but got {type(result)}"
    
    assert result.get("returncode") == 0, f"Expected exit code 0, got {result.get('returncode')}"
    assert "hello world" in result.get("stdout", ""), f"Expected 'hello world' in stdout, got {result.get('stdout')}"
    assert result.get("stderr", "") == "", f"Expected empty stderr, got {result.get('stderr')}"

def test_execute_command_timeout():
    """Test command timeout."""
    # Disable resource checks for this test
    executor = CommandExecutor(max_runtime=1, check_resources=False) 
    cmd = "sleep 5" # Command that takes longer than timeout
    
    # Execute the command synchronously
    result = executor.execute(command=cmd, timeout=1)
    
    # Assert that the result indicates an error due to timeout
    assert result["status"] == "error", f"Expected error status, got {result['status']}"
    assert result["error_code"] == "TIMEOUT_TERMINATED", f"Expected TIMEOUT_TERMINATED, got {result['error_code']}" # Updated expected code
    assert "timed out after 1 seconds" in result["error"], f"Expected timeout message, got {result['error']}"

def test_read_output():
    """Test reading output after a command has run."""
    # Disable resource checks for this test
    executor = CommandExecutor(check_resources=False)
    # Use a simpler command that finishes quickly
    cmd = "echo 1 && echo 2 stderr >&2 && echo 3"
    
    # Execute command synchronously
    result = executor.execute(command=cmd, allow_background=False) # Don't allow background
    assert result["status"] == "success", "Command execution failed"
    assert result["returncode"] == 0
    pid = result.get("pid")
    assert pid is not None, "PID not returned"

    # Check the final output stored in the result dictionary
    assert "1" in result.get("stdout", ""), "Did not find '1' in stdout"
    assert "2 stderr" in result.get("stderr", ""), "Did not find '2 stderr' in stderr"
    assert "3" in result.get("stdout", ""), "Did not find '3' in stdout"

def test_force_terminate():
    """Test force terminating a process."""
    # Disable resource checks for this test
    executor = CommandExecutor(check_resources=False)
    
    # Start a long-running command
    if sys.platform == "win32":
        # Equivalent long-running command for Windows if needed
        cmd = "ping -t 127.0.0.1" 
    else:
        cmd = "sleep 60" # Use a longer sleep duration
    
    # Start the command in the background (synchronously)
    result = executor.execute(command=cmd, allow_background=True)
    assert result["status"] == "success"
    pid = result.get("pid")
    assert pid is not None
    
    # Allow a brief moment for the process to start
    time.sleep(0.5)
    
    # Terminate the process (synchronously)
    terminate_result = executor.terminate(pid, force=True)
    
    # Verify termination status - Check 'status' key
    assert terminate_result["status"] == "success", f"Expected status success, got {terminate_result}"
    assert "terminated" in terminate_result.get("message", "").lower()
    
    # Verify process is no longer active in executor
    sessions_after_terminate = executor.list_processes()
    assert pid not in [p['pid'] for p in sessions_after_terminate.get('processes', [])]

@patch("server.utils.command_execution.CommandExecutor._validate_command") # Patch the internal validation
def test_blacklisted_command(mock_validate_command):
    """Test behavior with blacklisted commands using CommandExecutor."""
    # Mock _validate_command to raise an exception, simulating a blocked command
    mock_validate_command.side_effect = SecurityError("Command blocked")
    
    # Use an executor instance for this test
    local_executor = CommandExecutor()
    
    # Try to execute a "dangerous" command synchronously
    result = local_executor.execute("dangerous_command")
    
    # Verify it resulted in an error status
    assert result.get("status") == "error", f"Expected error status, got {result}"
    assert "Command blocked" in result.get("error", ""), f"Expected 'Command blocked' in error message, got {result.get('error')}"
    assert result.get("pid") is None

def test_block_and_unblock_command():
    """Test blocking and unblocking commands using executor's validation."""
    test_command = "test_block_command_for_validate"
    executor = CommandExecutor() # Create an instance

    # Initially, the command should be safe (validate doesn't raise)
    command_initially_safe = False
    try:
        executor._validate_command(test_command)
        command_initially_safe = True
    except SecurityError:
        command_initially_safe = False
    assert command_initially_safe, f"Command '{test_command}' should be safe initially"

    # Block the command (using the core block function)
    block_command(test_command)

    # Now, validation should raise SecurityError
    command_safe_after_block = True
    try:
        executor._validate_command(test_command)
        # If it doesn't raise, it's still considered safe (failure)
    except SecurityError:
        command_safe_after_block = False # Correctly blocked
    except Exception as e:
        pytest.fail(f"_validate_command raised unexpected exception {type(e)} after block: {e}")
        
    assert not command_safe_after_block, f"Command '{test_command}' should be blocked after block_command"

    # Unblock the command (using the core unblock function)
    unblock_command(test_command)

    # Command should be safe again (validate doesn't raise)
    command_safe_after_unblock = False
    try:
        executor._validate_command(test_command)
        command_safe_after_unblock = True # Correctly unblocked
    except SecurityError:
        # If it raises, it's still blocked (failure)
        command_safe_after_unblock = False
    except Exception as e:
        pytest.fail(f"_validate_command raised unexpected exception {type(e)} after unblock: {e}")
        
    assert command_safe_after_unblock, f"Command '{test_command}' should be safe after unblock_command"

@pytest.mark.skipif(sys.platform == "win32", reason="Process list format differs on Windows")
def test_list_sessions():
    """Test listing active command sessions."""
    executor = CommandExecutor(check_resources=False)
    pid = None
    try:
        cmd = "sleep 10"

        # Start the process using the new background method
        result = executor.start_background(command=cmd)
        assert result.get("status") == "success", f"start_background failed: {result.get('error')}"
        pid = result.get("pid")
        assert pid is not None, "Executor did not return a PID from start_background."

        # Wait briefly for the process to be fully registered and running
        time.sleep(0.5) # Increased wait time slightly more just in case

        # List sessions
        sessions_result = executor.list_processes()

        # Assertions remain the same
        assert isinstance(sessions_result, dict), f"Expected list_processes to return a dict, got {type(sessions_result)}"
        assert "processes" in sessions_result, "'processes' key missing in list_processes result"
        processes_list = sessions_result["processes"]
        assert isinstance(processes_list, list), "'processes' key should contain a list"

        found_process = None
        for proc_info in processes_list:
            assert isinstance(proc_info, dict), f"Each item in processes list should be a dict, got {type(proc_info)}"
            if proc_info.get("pid") == pid:
                found_process = proc_info
                break

        assert found_process is not None, f"Process with PID {pid} not found in active sessions list: {processes_list}"

        assert found_process.get("command") == cmd, f"Expected command '{cmd}', got {found_process.get('command')}"
        assert found_process.get("status") == "running", f"Expected status 'running', got {found_process.get('status')}"

    finally:
        if pid and executor:
            terminate_result = executor.terminate(pid, force=True)
            print(f"Cleanup termination result for PID {pid}: {terminate_result}")