# Terminal Command Runner MCP - Tech Context

## Technology Stack

- **Python**: Core implementation language (3.8+)
- **FastMCP**: Framework for creating MCP servers (based on FastAPI)
- **psutil**: System and process monitoring
- **pytest**: Testing framework with parallel execution
- **Subprocess**: Standard library for process execution
- **Threading**: For concurrent execution and output streaming
- **Queue**: Thread-safe data structures for output collection
- **Signal**: For process control and termination
- **OS**: Operating system interfaces for file and process operations

## Development Setup & Conventions

### Package Management
- **uv**: Primary package manager for Python dependencies
  - All dependencies must be installed using `uv add`
  - Direct pip usage is not allowed
  - Requirements are managed through `pyproject.toml`, not requirements.txt

### Code Quality
- **ruff**: Single tool for all code quality checks
  - Replaces flake8, isort, and other linting tools
  - Handles both linting and formatting
  - Configuration in pyproject.toml

### Testing
- **pytest**: Primary testing framework
  - Parallel test execution with pytest-xdist
  - Coverage reporting with pytest-cov
  - Test categorization (unit, integration)
- **Docker**: For isolated testing environments
- **Makefile**: For standardized test commands

## Technical Constraints

- **Security**: Must prevent execution of dangerous commands
- **Concurrency**: Must handle multiple concurrent processes
- **Timeouts**: All operations should have configurable timeouts
- **Error Handling**: All operations must have robust error handling
- **Cross-Platform**: Core functionality should work across operating systems
- **Context Management**: Must track and manage LLM context length

## Dependencies

### Core Dependencies
- **FastMCP**: For the MCP server implementation
- **psutil**: System monitoring and metrics
- **pytest**: Testing framework with plugins
  - pytest-xdist: Parallel test execution
  - pytest-cov: Coverage reporting
- **Standard Library**: Core functionality relies only on Python standard library

### Development Tools
- **uv**: Modern Python package manager
- **ruff**: All-in-one Python linter and formatter
- **pytest**: Testing framework with plugins

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

5. **Development Tools**:
   - `install_dependency`: Install Python packages using uv
   - `run_tests`: Execute tests with proper isolation
   - `format_code`: Run ruff formatting
   - `lint_code`: Run ruff linting
   - `filter_output`: Process and format long command outputs

6. **Code Analysis**:
   - `analyze_codebase`: Static code analysis
   - `monitor_performance`: System performance tracking
   - `manage_llm_context`: LLM context optimization
   - `enhanced_testing`: Advanced test execution

7. **Utilities**:
   - `system_info`: Get system information
   - `calculate`: Evaluate a mathematical expression
   - `context_length`: Track LLM context usage

## Performance Considerations

- **Output Streaming**: Efficient handling of process output
- **Resource Management**: Proper cleanup of resources for long-running processes
- **Memory Usage**: Careful handling of large file content or command output
- **Threading**: Proper synchronization for concurrent operations
- **Context Length**: Monitoring and managing LLM context usage
- **Test Performance**: Parallel test execution and efficient coverage tracking
- **System Monitoring**: Low-overhead performance metrics collection

## Observability Stack

### Distributed Tracing
- OpenTelemetry integration for distributed tracing
- OTLP exporter configured for trace collection
- Automatic tracing for all MCP tools via decorator pattern
- Configurable service name and version
- Default endpoint: http://localhost:4317

### Dependencies
- OpenTelemetry packages:
  - opentelemetry-api==1.31.1
  - opentelemetry-sdk==1.31.1
  - opentelemetry-exporter-otlp==1.31.1
  - opentelemetry-semantic-conventions==0.52b1

### Metrics Collection
- OpenTelemetry Metrics integration
- OTLP exporter for metrics collection
- Default endpoint: http://localhost:4317
- Key metrics:
  - Tool execution duration (histogram)
  - Tool call count (counter)
  - Error count (counter)
  - Active sessions (up/down counter)
  - Memory usage (observable gauge)

### System Dependencies
- psutil for system metrics collection
- OpenTelemetry metrics packages:
  - opentelemetry-sdk-metrics
  - opentelemetry-exporter-otlp-proto-grpc 