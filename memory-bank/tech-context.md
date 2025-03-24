# Terminal Command Runner MCP - Tech Context

## Technology Stack

- **Python**: Core implementation language (3.8+)
- **FastMCP**: Framework for creating MCP servers (based on FastAPI)
- **Subprocess**: Standard library for process execution
- **Threading**: For concurrent execution and output streaming
- **Queue**: Thread-safe data structures for output collection
- **Signal**: For process control and termination
- **OS**: Operating system interfaces for file and process operations

## Development Setup

- Python 3.8+ environment
- Virtual environment for dependency isolation
- Development tooling for testing and debugging

## Technical Constraints

- **Security**: Must prevent execution of dangerous commands
- **Concurrency**: Must handle multiple concurrent processes
- **Timeouts**: All operations should have configurable timeouts
- **Error Handling**: All operations must have robust error handling
- **Cross-Platform**: Core functionality should work across operating systems

## Dependencies

- **FastMCP**: For the MCP server implementation
- **Standard Library**: Core functionality relies only on Python standard library
- **Operating System**: Access to OS-level process and file operations

## API Structure

The API consists of tool functions that can be invoked remotely:

1. **Command Execution**:
   - `execute_command`: Run a command with timeout control
   - `read_output`: Stream output from a running command
   - `force_terminate`: Stop a running command

2. **Process Management**:
   - `list_sessions`: Show active command sessions
   - `list_processes`: List system processes
   - `kill_process`: Terminate a process by PID

3. **Command Control**:
   - `block_command`: Add a command to the blacklist
   - `unblock_command`: Remove a command from the blacklist

4. **File Operations**:
   - `read_file`: Read file contents with size limits
   - `write_file`: Write content to a file
   - `create_directory`: Create a new directory
   - `list_directory`: List directory contents
   - `move_file`: Move or rename files
   - `search_files`: Find files matching a pattern
   - `get_file_info`: Get metadata about a file

5. **Utilities**:
   - `system_info`: Get system information
   - `calculate`: Evaluate a mathematical expression

## Performance Considerations

- **Output Streaming**: Efficient handling of process output
- **Resource Management**: Proper cleanup of resources for long-running processes
- **Memory Usage**: Careful handling of large file content or command output
- **Threading**: Proper synchronization for concurrent operations 