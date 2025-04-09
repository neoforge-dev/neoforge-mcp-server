"""
Shared error handling utilities for MCP servers.
"""

from typing import Any, Dict, Optional, Type, Union
from functools import wraps
import traceback
import logging
import asyncio

# Configure logging
logger = logging.getLogger(__name__)

class MCPError(Exception):
    """Base exception class for MCP errors."""
    def __init__(self, message: str, error_code: str = "MCP_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)

class ValidationError(MCPError):
    """Raised when input validation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)

class SecurityError(MCPError):
    """Raised when a security check fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SECURITY_ERROR", details)

class ResourceError(MCPError):
    """Raised when there's an issue with system resources."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RESOURCE_ERROR", details)

class ToolError(MCPError):
    """Raised when a tool operation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "TOOL_ERROR", details)

def format_error_response(error: Union[Exception, str], error_code: str = "UNKNOWN_ERROR") -> Dict[str, Any]:
    """Format an error into a standardized response dictionary."""
    if isinstance(error, MCPError):
        return {
            "status": "error",
            "error_code": error.error_code,
            "error": error.message,
            "details": error.details
        }
    else:
        return {
            "status": "error",
            "error_code": error_code,
            "error": str(error)
        }

def handle_exceptions(error_code: str = "TOOL_ERROR", log_traceback: bool = True) -> Any:
    """Decorator to handle exceptions in tool functions."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Await the result if the original function is async
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except MCPError as e:
                if log_traceback:
                    logger.error(f"Tool error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
                return format_error_response(e)
            except Exception as e:
                if log_traceback:
                    logger.error(f"Unexpected error in {func.__name__}: {str(e)}\n{traceback.format_exc()}")
                return format_error_response(e, error_code)
        return wrapper
    return decorator

def validate_input(value: Any, validator: Type, field_name: str) -> None:
    """Validate input value against a type or validator."""
    try:
        if not isinstance(value, validator):
            raise ValidationError(
                f"Invalid type for {field_name}. Expected {validator.__name__}, got {type(value).__name__}",
                {"field": field_name, "expected_type": validator.__name__, "actual_type": type(value).__name__}
            )
    except Exception as e:
        raise ValidationError(f"Validation failed for {field_name}: {str(e)}")

def validate_command(command: str, blacklist: set[str]) -> None:
    """Validate a command against a blacklist."""
    if any(pattern in command for pattern in blacklist):
        raise SecurityError(
            "Command contains blacklisted patterns",
            {"command": command, "matched_patterns": [p for p in blacklist if p in command]}
        )

def check_resource_limits(
    cpu_percent: float = 90.0,
    memory_percent: float = 90.0,
    disk_percent: float = 90.0
) -> None:
    """Check if system resources are within acceptable limits."""
    import psutil
    
    current_cpu = psutil.cpu_percent()
    current_memory = psutil.virtual_memory().percent
    current_disk = psutil.disk_usage('/').percent
    
    if current_cpu > cpu_percent:
        raise ResourceError(
            f"CPU usage too high: {current_cpu}%",
            {"current": current_cpu, "limit": cpu_percent}
        )
    
    if current_memory > memory_percent:
        raise ResourceError(
            f"Memory usage too high: {current_memory}%",
            {"current": current_memory, "limit": memory_percent}
        )
    
    if current_disk > disk_percent:
        raise ResourceError(
            f"Disk usage too high: {current_disk}%",
            {"current": current_disk, "limit": disk_percent}
        ) 