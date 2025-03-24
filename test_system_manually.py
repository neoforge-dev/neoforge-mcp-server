import os
import sys
import time
import subprocess
import threading

# Import the server module
import server

def test_system_info():
    """Test retrieving system information."""
    result = server.system_info()
    print(f"System info result: {result}")
    
    # Verify the result contains expected fields
    assert "platform" in result
    assert "python_version" in result
    assert "system" in result
    assert "machine" in result
    assert "processor" in result
    
    print("system_info test passed!")

def test_calculate():
    """Test the calculate utility function."""
    # Test basic arithmetic
    result = server.calculate("2 + 3 * 4")
    print(f"Calculate arithmetic result: {result}")
    assert result["success"] is True
    assert result["result"] == 14
    
    # Test more complex expressions
    result = server.calculate("sqrt(16) + pow(2, 3)")
    print(f"Calculate complex result: {result}")
    assert result["success"] is True
    assert result["result"] == 12.0
    
    # Test invalid expression
    result = server.calculate("invalid expression")
    print(f"Calculate invalid result: {result}")
    assert "error" in result
    
    # Test potentially dangerous expressions
    result = server.calculate("__import__('os').system('echo hack')")
    print(f"Calculate dangerous result: {result}")
    assert "error" in result
    
    print("calculate test passed!")

def test_edit_block():
    """Test the edit_block functionality."""
    # Create a temporary file for testing
    test_file = "test_edit_block.txt"
    try:
        with open(test_file, "w") as f:
            f.write("This is a test file\nfor edit_block functionality\nIt has three lines")
        
        # Test edit block functionality
        edit_block = f"""@@ {test_file}
This is the NEW CONTENT
with completely different text
than the original"""
        
        result = server.edit_block(edit_block)
        print(f"Edit block result: {result}")
        
        # Verify the result
        assert result["success"] is True
        
        # Verify the file content was updated
        with open(test_file, "r") as f:
            content = f.read()
        
        assert "NEW CONTENT" in content
        assert "completely different text" in content
        
        print("edit_block test passed!")
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

def test_list_processes():
    """Test listing system processes."""
    result = server.list_processes()
    print(f"List processes result (showing first 3): {result['processes'][:3]}")
    
    # Verify result structure
    assert "processes" in result
    assert isinstance(result["processes"], list)
    assert len(result["processes"]) > 0
    
    # Check first process has expected fields
    first_process = result["processes"][0]
    assert "pid" in first_process
    
    print("list_processes test passed!")

def test_command_execution():
    """Test basic command execution and control."""
    # Execute a simple command
    result = server.execute_command("echo 'test command'")
    print(f"Execute command result: {result}")
    
    assert "test command" in result["stdout"]
    assert result["exit_code"] == 0
    
    # Execute a command with background processing
    if sys.platform == "win32":
        cmd = "ping -n 5 localhost"
    else:
        cmd = "sleep 5"
    
    result = server.execute_command(cmd, timeout=1, allow_background=True)
    print(f"Background command result: {result}")
    
    # Verify it's running in the background
    assert result["pid"] is not None
    
    # Get the PID
    pid = result["pid"]
    
    # Read output while it's running
    time.sleep(1)
    output = server.read_output(pid)
    print(f"Read output result: {output}")
    
    # Force terminate the process
    terminate_result = server.force_terminate(pid)
    print(f"Terminate result: {terminate_result}")
    assert terminate_result["success"] is True
    
    # Verify it's no longer running
    time.sleep(0.5)
    try:
        os.kill(pid, 0)
        process_running = True
    except OSError:
        process_running = False
    
    assert not process_running
    
    print("command_execution test passed!")

def test_block_unblock_command():
    """Test adding and removing commands from the blacklist."""
    test_command = "test_block_command"
    
    # Ensure command is not in the blacklist initially
    if test_command in server.blacklisted_commands:
        server.blacklisted_commands.remove(test_command)
    
    # Block the command
    result = server.block_command(test_command)
    print(f"Block command result: {result}")
    assert result["success"] is True
    
    # Verify command is now in the blacklist
    assert test_command in server.blacklisted_commands
    
    # Unblock the command
    result = server.unblock_command(test_command)
    print(f"Unblock command result: {result}")
    assert result["success"] is True
    
    # Verify command is no longer in the blacklist
    assert test_command not in server.blacklisted_commands
    
    print("block_unblock_command test passed!")

def run_tests():
    """Run all tests"""
    tests = [
        test_system_info,
        test_calculate,
        test_edit_block,
        test_list_processes,
        test_command_execution,
        test_block_unblock_command
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\nRunning test: {test.__name__}")
            test()
            passed += 1
        except Exception as e:
            print(f"Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\nTest Results: {passed} passed, {failed} failed")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 