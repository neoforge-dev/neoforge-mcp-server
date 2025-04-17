"""
Shared error handling utilities for MCP servers.
"""

from typing import Any, Dict, Optional, Type, Union, Callable, Coroutine
from functools import wraps
import traceback
import logging
import asyncio
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from datetime import datetime
import inspect
from fastapi import HTTPException
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

class ErrorCode(Enum):
    """Error codes for different types of errors."""
    
    # Server Errors (5xx)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    GATEWAY_ERROR = "GATEWAY_ERROR"
    
    # Client Errors (4xx)
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    CONFLICT = "CONFLICT"
    
    # Resource Errors
    RESOURCE_ERROR = "RESOURCE_ERROR"
    MEMORY_ERROR = "MEMORY_ERROR"
    DISK_ERROR = "DISK_ERROR"
    CPU_ERROR = "CPU_ERROR"
    
    # Security Errors
    SECURITY_ERROR = "SECURITY_ERROR"
    API_KEY_ERROR = "API_KEY_ERROR"
    TOKEN_ERROR = "TOKEN_ERROR"
    
    # Process Errors
    PROCESS_ERROR = "PROCESS_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    COMMAND_ERROR = "COMMAND_ERROR"

class MCPError(Exception):
    """Base exception for all MCP errors."""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary format."""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "status_code": self.status_code,
                "details": self.details
            }
        }

class ValidationError(MCPError):
    """Validation error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details
        )

class AuthenticationError(MCPError):
    """Authentication error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.UNAUTHORIZED,
            status_code=401,
            details=details
        )

class AuthorizationError(MCPError):
    """Authorization error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.FORBIDDEN,
            status_code=403,
            details=details
        )

class NotFoundError(MCPError):
    """Resource not found error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            status_code=404,
            details=details
        )

class ConflictError(MCPError):
    """Resource conflict error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.CONFLICT,
            status_code=409,
            details=details
        )

class ConfigurationError(MCPError):
    """Configuration error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.INTERNAL_ERROR,
            status_code=500, # Configuration issues are internal server errors
            details=details
        )

class SecurityError(MCPError):
    """Security-related error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.SECURITY_ERROR,
            status_code=403,
            details=details
        )

class ResourceError(MCPError):
    """Resource limit error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code=ErrorCode.RESOURCE_ERROR,
            status_code=503,
            details=details
        )

class ToolError(MCPError):
    """Raised when a tool operation fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCode.INTERNAL_ERROR, 500, details)

def format_error_response(error: Union[Exception, str], error_code: ErrorCode = ErrorCode.INTERNAL_ERROR) -> Dict[str, Any]:
    """Format an error into a standardized response dictionary."""
    if isinstance(error, MCPError):
        return {
            "status": "error",
            "error_code": error.code.value,
            "error": error.message,
            "details": error.details
        }
    else:
        return {
            "status": "error",
            "error_code": error_code.value,
            "error": str(error)
        }

def handle_exceptions(*error_classes: Type[Exception], error_code: ErrorCode = ErrorCode.INTERNAL_ERROR):
    """Decorator for handling exceptions in route handlers."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                # Await the result if the wrapped function is async
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                if error_classes and not isinstance(e, error_classes):
                    raise
                
                # Re-raise MCPError subclasses and FastAPI's HTTPException directly
                if isinstance(e, MCPError) or isinstance(e, HTTPException):
                    raise e # Let MCPError middleware or FastAPI handle these
                    
                # Convert other specified or unexpected exceptions to MCPError
                logger.error(f"Unhandled exception in route handler '{func.__name__}': {e}", exc_info=True)
                raise MCPError(
                    message=str(e),
                    code=error_code,
                    status_code=500,
                    details={
                        "type": type(e).__name__,
                        # Optionally include traceback in details if needed for debugging
                        # "traceback": traceback.format_exc()
                    }
                )
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

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling errors."""
    
    def __init__(self, app, logger):
        super().__init__(app)
        self.logger = logger
        
    async def dispatch(self, request: Request, call_next) -> Response:
        """Handle errors in the request/response cycle."""
        try:
            return await call_next(request)
            
        except MCPError as e:
            # Log error with appropriate level based on status code
            if e.status_code >= 500:
                self.logger.error(
                    f"Server error: {str(e)}",
                    extra={
                        "error_code": e.code.value,
                        "details": e.details,
                        "traceback": traceback.format_exc()
                    }
                )
            else:
                self.logger.warning(
                    f"Client error: {str(e)}",
                    extra={
                        "error_code": e.code.value,
                        "details": e.details
                    }
                )
            
            return JSONResponse(
                status_code=e.status_code,
                content=e.to_dict()
            )
            
        except Exception as e:
            # Log unexpected errors
            self.logger.error(
                f"Unexpected error: {str(e)}",
                extra={
                    "error_code": ErrorCode.INTERNAL_ERROR.value,
                    "traceback": traceback.format_exc()
                }
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": ErrorCode.INTERNAL_ERROR.value,
                        "message": "An unexpected error occurred",
                        "status_code": 500,
                        "details": {
                            "type": type(e).__name__,
                            "message": str(e)
                        }
                    }
                }
            ) 