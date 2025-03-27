# LLM Tools MCP Server

This is a separate MCP server that provides LLM-related tools and functionality. It runs on port 7444 and can be used alongside the main MCP server.

## Features

### Code Generation
- Generate code using various LLM models (Claude, GPT, CodeLlama, StarCoder)
- Support for different programming languages
- Context-aware code generation
- System prompt customization

### LLM Context Management
- Track and optimize LLM context usage
- Token estimation and limits
- Content optimization suggestions
- Model-specific context handling

### Output Processing
- Filter and format command outputs for LLM consumption
- Pattern-based content filtering
- Smart line sampling
- Important information preservation

## Available Tools

### `generate_code`
Generate code using various LLM models.

Parameters:
- `prompt`: The code generation prompt
- `model`: LLM model to use (default: "claude-3-sonnet")
- `context`: Optional context information
- `system_prompt`: Optional custom system prompt

### `manage_llm_context`
Manage and optimize LLM context usage.

Parameters:
- `content`: Text content to analyze
- `model`: Target LLM model
- `max_tokens`: Maximum token limit

### `context_length`
Track LLM context usage.

Parameters:
- `text`: Text to analyze

### `filter_output`
Process and format command outputs.

Parameters:
- `content`: Output content to filter
- `max_lines`: Maximum number of lines to include
- `important_patterns`: List of regex patterns to always include

## Setup

1. Install dependencies:
```bash
uv pip install -e ".[llm]"
```

2. Start the server:
```bash
mcp run llm_server.py
```

## Configuration

The server can be configured through environment variables:

- `MCP_LOG_LEVEL`: Logging level (default: "DEBUG")
- `ENABLE_TELEMETRY`: Enable OpenTelemetry tracing (default: "0")

## Integration

The LLM server can be used alongside the main MCP server:

```python
from mcp.client import MCPClient

# Main server client
main_client = MCPClient(port=7443)

# LLM server client
llm_client = MCPClient(port=7444)

# Use tools from both servers
main_client.call_tool("execute_command", command="ls")
llm_client.call_tool("generate_code", prompt="Write a function to sort a list")
```

## Dependencies

The LLM server requires additional dependencies that are not needed by the main server:

- `torch`: PyTorch for local model support
- `transformers`: Hugging Face Transformers
- `anthropic`: Claude API client
- `openai`: OpenAI API client

These dependencies are optional and can be installed using the `llm` extra:

```bash
uv pip install -e ".[llm]"
```

## Monitoring

The server includes OpenTelemetry integration for monitoring:

- Distributed tracing
- Metrics collection
- Error tracking
- Performance monitoring

Metrics are exported to the OpenTelemetry collector at `http://localhost:4317`. 