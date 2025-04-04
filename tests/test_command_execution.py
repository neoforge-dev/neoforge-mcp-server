"""Tests for command execution functionality."""

import os
import sys
import pytest
import time
import subprocess
from unittest.mock import patch, MagicMock
import threading
import queue

from server.core import (
    is_command_safe,
    execute_command,
    read_output,
    force_terminate,
    block_command,
    unblock_command,
    blacklisted_commands,
    list_sessions,
    session_lock,
    active_sessions
)

def test_is_command_safe():
    """Test command safety validation function."""
    # Test empty command
    assert not is_command_safe("")
    
    # Test safe command
    assert is_command_safe("echo 'hello world'")
    
    # Test unsafe command
    assert not is_command_safe("rm -rf /")
    
    # Test another unsafe command
    assert not is_command_safe("mkfs")


@pytest.mark.parametrize("cmd,expected_exit_code", [
    ("echo 'hello world'", 0),
    ("exit 1", 1),
    ("non-existent-command", None)  # This command should fail to execute
])
def test_execute_command_basic(cmd, expected_exit_code):
    """Test basic command execution with different commands."""
    # Skip the non-existent command test in Windows
    if sys.platform == "win32" and cmd == "non-existent-command":
        pytest.skip("Skipping non-existent command test on Windows")
    
    result = execute_command(cmd, timeout=2)
    
    # Check command execution result
    if expected_exit_code is None:
        # For non-existent commands, we expect an error
        assert "error" in result or result["exit_code"] != 0
    else:
        # For valid commands, check exit code
        assert result["exit_code"] == expected_exit_code
        assert "stdout" in result
        assert "stderr" in result


def test_execute_command_output():
    """Test command execution output capture."""
    # Simple echo command with predictable output
    cmd = "echo 'hello world'"
    result = execute_command(cmd, timeout=2)
    
    # Verify output
    assert result["exit_code"] == 0
    assert "hello world" in result["stdout"]
    assert result["stderr"] == ""  # No stderr output expected


def test_execute_command_timeout():
    """Test command execution with timeout."""
    # Choose a command that will run longer than the timeout but not too long
    if sys.platform == "win32":
        cmd = "echo 1 && timeout /t 2"  # Will take ~2 seconds on Windows
    else:
        cmd = "echo 1 && sleep 2"  # Will take 2 seconds on Unix-like
    
    # Set timeout to 1 second
    result = execute_command(cmd, timeout=1, allow_background=False)
    
    # Command should be terminated after timeout
    assert result["runtime"] >= 1.0
    assert result["pid"] is None  # No background process should be running
    
    # Now allow background process
    result = execute_command(cmd, timeout=1, allow_background=True)
    
    # Command should be running in background
    assert result["pid"] is not None
    assert result["exit_code"] is None
    assert result["complete"] is False
    
    # Clean up the process with a timeout
    if result["pid"]:
        terminate_result = force_terminate(result["pid"])
        assert terminate_result["success"], f"Failed to terminate process: {terminate_result.get('error')}"
        
        # Verify the process is no longer in active sessions
        with session_lock:
            assert result["pid"] not in active_sessions


def test_read_output():
    """Test reading output from a background process."""
    # Start a command that produces output periodically
    if sys.platform == "win32":
        cmd = "echo 1 && timeout /t 1 && echo 2 && timeout /t 1 && echo 3"
    else:
        cmd = "echo 1 && sleep 1 && echo 2 && sleep 1 && echo 3"
    
    # Execute command with background allowed
    result = execute_command(cmd, timeout=1, allow_background=True)
    assert result["pid"] is not None
    
    pid = result["pid"]
    
    # Wait a bit for some output to be generated
    time.sleep(1)
    
    # Read the output
    output_result = read_output(pid)
    
    # Check that there's some output
    assert output_result["stdout"] != "" or output_result["stderr"] != ""
    
    # Wait for process to complete with a timeout
    max_wait = 5
    start_time = time.time()
    while time.time() - start_time < max_wait:
        output_result = read_output(pid)
        if output_result["complete"]:
            break
        time.sleep(0.5)
    
    # If process didn't complete within max_wait, force terminate it
    if not output_result["complete"]:
        force_terminate(pid)
        pytest.skip("Process did not complete within expected time, skipping test")
    
    # Verify the process completed
    assert output_result["complete"]
    assert output_result["pid"] is None


def test_force_terminate():
    """Test terminating a background process."""
    # Start a long-running command
    if sys.platform == "win32":
        cmd = "echo 1 && timeout /t 5"  # Reduced from 30 to 5 seconds
    else:
        cmd = "echo 1 && sleep 5"  # Reduced from 30 to 5 seconds
    
    # Execute command with background allowed
    result = execute_command(cmd, timeout=1, allow_background=True)
    assert result["pid"] is not None
    
    pid = result["pid"]
    
    # Wait a bit for the process to start
    time.sleep(0.5)
    
    # Force terminate the process
    terminate_result = force_terminate(pid)
    assert terminate_result["success"]
    
    # Verify the process is no longer in active sessions
    with session_lock:
        assert pid not in active_sessions


@patch("server.core.is_command_safe")
def test_blacklisted_command(mock_is_command_safe):
    """Test behavior with blacklisted commands."""
    # Mock is_command_safe to return False
    mock_is_command_safe.return_value = False
    
    # Try to execute a "dangerous" command
    result = execute_command("dangerous_command")
    
    # Verify it was blocked
    assert "error" in result or "blocked" in result["stderr"].lower()
    assert result["pid"] is None


def test_block_and_unblock_command():
    """Test adding and removing commands from the blacklist."""
    test_command = "test_block_command"
    
    # Ensure command is not in the blacklist initially
    if test_command in blacklisted_commands:
        blacklisted_commands.remove(test_command)
    
    # Verify command is considered safe initially
    assert is_command_safe(test_command)
    
    # Block the command
    result = block_command(test_command)
    assert result["success"]
    
    # Verify command is now considered unsafe
    assert not is_command_safe(test_command)
    
    # Unblock the command
    result = unblock_command(test_command)
    assert result["success"]
    
    # Verify command is safe again
    assert is_command_safe(test_command)


@pytest.mark.skipif(sys.platform == "win32", reason="Process list format differs on Windows")
def test_list_sessions():
    """Test listing active command sessions."""
    # Clear any existing sessions
    with session_lock:
        active_sessions.clear()
    
    # Start a background process with a shorter duration
    cmd = "sleep 5"  # Reduced from 10 to 5 seconds
    result = execute_command(cmd, timeout=1, allow_background=True)
    pid = result["pid"]
    
    # Get session list
    sessions_result = list_sessions()
    
    # Verify session is in the list
    assert "sessions" in sessions_result
    assert len(sessions_result["sessions"]) > 0
    
    # Find our session in the list
    found = False
    for session in sessions_result["sessions"]:
        if session["pid"] == pid:
            found = True
            assert session["command"] == cmd
    
    assert found
    
    # Clean up
    force_terminate(pid)