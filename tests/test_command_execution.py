"""Tests for command execution functionality."""

import os
import sys
import pytest
import time
import subprocess
from unittest.mock import patch, MagicMock
import threading
import queue

# Import the server module - this assumes server.py is in the parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import server


def test_is_command_safe():
    """Test command safety validation function."""
    # Test empty command
    assert not server.is_command_safe("")
    
    # Test safe command
    assert server.is_command_safe("echo 'hello world'")
    
    # Test unsafe command
    assert not server.is_command_safe("rm -rf /")
    
    # Test another unsafe command
    assert not server.is_command_safe("mkfs")


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
    
    result = server.execute_command(cmd, timeout=2)
    
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
    result = server.execute_command(cmd, timeout=2)
    
    # Verify output
    assert result["exit_code"] == 0
    assert "hello world" in result["stdout"]
    assert result["stderr"] == ""  # No stderr output expected


def test_execute_command_timeout():
    """Test command execution with timeout."""
    # Choose a command that will run longer than the timeout
    if sys.platform == "win32":
        cmd = "ping -n 10 localhost"  # Will take ~10 seconds on Windows
    else:
        cmd = "sleep 5"  # Will take 5 seconds on Unix-like
    
    # Set timeout to 1 second
    result = server.execute_command(cmd, timeout=1, allow_background=False)
    
    # Command should be terminated after timeout
    assert result["runtime"] >= 1.0
    assert result["pid"] is None  # No background process should be running
    
    # Now allow background process
    result = server.execute_command(cmd, timeout=1, allow_background=True)
    
    # Command should be running in background
    assert result["pid"] is not None
    assert result["exit_code"] is None
    assert result["complete"] is False
    
    # Clean up the process
    if result["pid"]:
        server.force_terminate(result["pid"])


def test_read_output():
    """Test reading output from a background process."""
    # Start a command that produces output periodically
    if sys.platform == "win32":
        cmd = "ping -n 3 localhost"
    else:
        cmd = "for i in 1 2 3; do echo $i; sleep 0.5; done"
    
    # Execute command with background allowed
    result = server.execute_command(cmd, timeout=1, allow_background=True)
    assert result["pid"] is not None
    
    pid = result["pid"]
    
    # Wait a bit for some output to be generated
    time.sleep(1)
    
    # Read the output
    output_result = server.read_output(pid)
    
    # Check that there's some output
    assert output_result["stdout"] != "" or output_result["stderr"] != ""
    
    # Wait for process to complete
    max_wait = 5
    start_time = time.time()
    while time.time() - start_time < max_wait:
        output_result = server.read_output(pid)
        if output_result["complete"]:
            break
        time.sleep(0.5)
    
    # Verify the process completed
    assert output_result["complete"]
    assert output_result["pid"] is None


def test_force_terminate():
    """Test terminating a background process."""
    # Start a long-running command
    if sys.platform == "win32":
        cmd = "ping -n 30 localhost"  # Will run for ~30 seconds
    else:
        cmd = "sleep 30"  # Will run for 30 seconds
    
    # Execute command with background allowed
    result = server.execute_command(cmd, timeout=1, allow_background=True)
    assert result["pid"] is not None
    
    pid = result["pid"]
    
    # Force terminate the process
    terminate_result = server.force_terminate(pid)
    
    # Verify termination was successful
    assert terminate_result["success"]
    
    # Check that the process is no longer running
    time.sleep(0.5)  # Give some time for cleanup
    try:
        os.kill(pid, 0)  # This will raise an error if the process is gone
        process_still_running = True
    except OSError:
        process_still_running = False
    
    assert not process_still_running


@patch("server.is_command_safe")
def test_blacklisted_command(mock_is_command_safe):
    """Test behavior with blacklisted commands."""
    # Mock is_command_safe to return False
    mock_is_command_safe.return_value = False
    
    # Try to execute a "dangerous" command
    result = server.execute_command("dangerous_command")
    
    # Verify it was blocked
    assert "error" in result
    assert result["pid"] is None
    assert "blocked" in result["stderr"].lower()


def test_block_and_unblock_command():
    """Test adding and removing commands from the blacklist."""
    test_command = "test_block_command"
    
    # Ensure command is not in the blacklist initially
    if test_command in server.blacklisted_commands:
        server.blacklisted_commands.remove(test_command)
    
    # Verify command is considered safe initially
    assert server.is_command_safe(test_command)
    
    # Block the command
    result = server.block_command(test_command)
    assert result["success"]
    
    # Verify command is now considered unsafe
    assert not server.is_command_safe(test_command)
    
    # Unblock the command
    result = server.unblock_command(test_command)
    assert result["success"]
    
    # Verify command is safe again
    assert server.is_command_safe(test_command)


@pytest.mark.skipif(sys.platform == "win32", reason="Process list format differs on Windows")
def test_list_sessions():
    """Test listing active command sessions."""
    # Clear any existing sessions
    with server.session_lock:
        server.active_sessions.clear()
    
    # Start a background process
    cmd = "sleep 10"  # Will run for 10 seconds
    result = server.execute_command(cmd, timeout=1, allow_background=True)
    pid = result["pid"]
    
    # Get session list
    sessions_result = server.list_sessions()
    
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
    server.force_terminate(pid) 