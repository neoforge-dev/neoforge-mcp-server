# MCP Server Shared Utilities

This directory contains shared utility modules used across all MCP servers to standardize common functionality and reduce code duplication.

## Modules

### Error Handling (`error_handling.py`)
- Base exception class `MCPError` for standardized error handling
- Specialized error types: `ValidationError`, `SecurityError`, `ResourceError`, `ToolError`
- Error response formatting and exception handling decorator
- Resource limit validation

### Command Execution (`command_execution.py`)
- Safe command execution with isolation via `CommandExecutor` class
- Process management and monitoring
- Output streaming and collection
- Resource usage checks
- Security validations

### Configuration (`config.py`)
- Configuration management via `ServerConfig` and `ConfigManager` classes
- Support for YAML and JSON formats
- Environment variable overrides
- Configuration validation
- Multi-server config management

### Logging (`logging.py`)
- Structured logging with JSON formatting
- Log rotation and management
- Context-aware logging
- Multiple output handlers (file, console)
- Custom log formatters

### Monitoring (`monitoring.py`)
- OpenTelemetry integration for tracing and metrics
- Request tracking
- Resource usage monitoring
- Performance metrics
- Distributed tracing support

### Validation (`validation.py`)
- Schema-based validation
- Built-in validators for common types
- Custom validation rules
- Field and schema validation
- Type checking and conversion

### Security (`security.py`)
- API key management
- Role-based access control
- Permission scopes
- Secure key generation and validation
- Authorization decorators

## Usage

Each module is designed to be used independently or in combination with others. Here are some common usage patterns:

### Error Handling
```python
from utils.error_handling import handle_exceptions, ValidationError

@handle_exceptions(error_code="CUSTOM_ERROR")
def my_function():
    # Function code here
    pass
```

### Command Execution
```python
from utils.command_execution import CommandExecutor

executor = CommandExecutor()
result = executor.execute("ls -l", timeout=30)
```

### Configuration
```python
from utils.config import ConfigManager

config_manager = ConfigManager()
config = config_manager.load_config("my_server")
```

### Logging
```python
from utils.logging import LogManager

log_manager = LogManager("my_server")
logger = log_manager.get_logger()
logger.info("Message", extra_fields={"key": "value"})
```

### Monitoring
```python
from utils.monitoring import MonitoringManager

monitor = MonitoringManager(
    service_name="my_server",
    enable_tracing=True,
    enable_metrics=True
)
```

### Validation
```python
from utils.validation import SchemaValidator, ValidationRule

schema = SchemaValidator()
schema.add_field("name", str, [
    ValidationRule("length", {"min": 2, "max": 50})
])
```

### Security
```python
from utils.security import SecurityManager

security = SecurityManager()
key, api_key = security.create_api_key(
    name="test",
    roles={"user"},
    scopes={"read:*"}
)
```

## Integration

To use these utilities in your server:

1. Import the required modules
2. Initialize the necessary managers/classes
3. Use the provided functionality in your server code

Example:
```python
from utils import (
    ConfigManager,
    LogManager,
    MonitoringManager,
    SecurityManager,
    CommandExecutor
)

class MyServer:
    def __init__(self):
        # Initialize utilities
        self.config = ConfigManager().load_config("my_server")
        self.logger = LogManager("my_server").get_logger()
        self.monitor = MonitoringManager("my_server")
        self.security = SecurityManager()
        self.executor = CommandExecutor()
```

## Best Practices

1. Always use the error handling decorator for functions that can fail
2. Configure proper logging for production environments
3. Set up monitoring for critical endpoints
4. Validate all user inputs using the validation module
5. Use the security module for any authenticated endpoints
6. Keep configuration in standard locations
7. Monitor resource usage in long-running processes 