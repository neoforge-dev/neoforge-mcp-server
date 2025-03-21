# Terminal Command Runner MCP Server

A powerful Model Control Protocol (MCP) server that provides terminal command execution and file system management capabilities for AI assistants through a RESTful API interface.

## 🌟 Features

### Terminal Management
- Execute commands with configurable timeouts
- Manage long-running processes in the background
- Fetch output from active command sessions
- List all active sessions and system processes
- Terminate or kill processes
- Command blacklisting for security

### File System Operations
- Read and write files
- Create directories
- List directory contents
- Move/rename files
- Search for files using glob patterns
- Get detailed file information

### Advanced Features
- Precise text editing with search and replace
- System information retrieval
- Mathematical expression evaluation

## 🚀 Quick Start

### Prerequisites
- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/neoforge-dev/neoforge-mcp-server.git
cd python-server-mcp
```

2. Create a virtual environment and install dependencies:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

3. Start the MCP server:
```bash
python server.py
```

The server will start on http://0.0.0.0:8000.

## 🔧 Configuration

Configure Cursor to use this MCP service by adding it to your `~/.cursor/mcp.json` file:

```json
{
  "mcpServers": {
    "NeoMCP": {
      "command": "/path/to/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "mcp",
        "run",
        "/path/to/python-server-mcp/server.py"
      ]
    }
  }
}
```

## 📖 API Reference

### Terminal Tools
- `execute_command`: Run commands with configurable timeouts
- `read_output`: Get output from running processes
- `force_terminate`: Stop a running command
- `list_sessions`: Show all active command sessions
- `list_processes`: View all system processes
- `kill_process`: Kill processes by PID
- `block_command`: Add commands to the blacklist
- `unblock_command`: Remove commands from the blacklist

### File System Tools
- `read_file`: Read file contents
- `write_file`: Write data to a file
- `create_directory`: Create new directories
- `list_directory`: List contents of a directory
- `move_file`: Move or rename files and directories
- `search_files`: Find files matching patterns
- `get_file_info`: Get detailed file information

### Edit Tools
- `edit_block`: Apply precise text replacements using diff-like syntax

### System Tools
- `system_info` (resource): Get detailed system information
- `calculate`: Evaluate mathematical expressions

## 🔒 Security Considerations

- The server implements command blacklisting to prevent dangerous commands
- File size limits for read operations
- Expression evaluation safeguards
- Default command safety checks

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
