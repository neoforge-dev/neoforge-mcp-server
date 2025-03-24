# Terminal Command Runner MCP - System Patterns

## Architecture Overview

The Terminal Command Runner MCP follows a tool-based architecture pattern:

```
Client <---> MCP Server <---> System Resources
              |
              v
          Tool Registry
              |
              v
        Command Execution / File System / Process Management
```

## Key Components

1. **FastMCP Server**: Base server implementation that handles client connections and tool registration
2. **Tool Registry**: Collection of functions registered as API endpoints that can be invoked remotely
3. **Command Executor**: Handles command execution with appropriate security checks and process management
4. **File System Interface**: Provides access to filesystem operations with security guardrails
5. **Process Manager**: Tracks and manages long-running processes with output streaming

## Design Patterns

### Command Pattern
- Commands are encapsulated as tool functions
- Each tool provides a specific capability with defined parameters
- Commands execute with isolated scope and return standardized results

### Producer-Consumer Pattern
- Command output is streamed through queues
- Reader threads produce output from process pipes
- API consumers read from these queues on demand

### Singleton Pattern
- Single MCP server instance manages all connections
- Global state for active sessions and output queues

### Observer Pattern
- Clients can observe long-running processes through the read_output tool
- Events are streamed as they occur rather than blocking for completion

## Technical Decisions

### Process Execution
- Uses subprocess.Popen for non-blocking execution
- Dedicated reader threads for stdout and stderr
- Timeout control for long-running processes

### Security Approach
- Command blacklist to prevent dangerous operations
- Configurable execution timeout
- Path validation for file operations

### Output Handling
- Output streaming through thread-safe queues
- Non-blocking reads from process output
- Support for both synchronous and asynchronous execution patterns

## Component Relationships

- **MCP Server** provides registration for all tool functions
- **Tools** encapsulate discrete capabilities and security checks
- **Command Execution** manages process lifecycle and output collection
- **Process Management** tracks active processes and enables interaction with them
- **File System Tools** provide controlled access to file operations 