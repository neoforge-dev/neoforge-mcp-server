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

# Configure logging
logger = logging.getLogger(__name__)

class MCPError(Exception):
    """Base exception for MCP errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "INTERNAL_ERROR"
        self.details = details or {}
        super().__init__(message)

class ValidationError(MCPError):
    """Validation error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=400,
            error_code="VALIDATION_ERROR",
            details=details
        )

class AuthenticationError(MCPError):
    """Authentication error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )

class AuthorizationError(MCPError):
    """Authorization error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )

class NotFoundError(MCPError):
    """Resource not found error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details
        )

class ConflictError(MCPError):
    """Resource conflict error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details
        )

class ConfigurationError(MCPError):
    """Configuration error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=500, # Configuration issues are internal server errors
            error_code="CONFIGURATION_ERROR",
            details=details
        )

class SecurityError(MCPError):
    """Security violation error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403, # Forbidden
            error_code="SECURITY_VIOLATION",
            details=details
        )

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

def handle_exceptions(error_code: str = "INTERNAL_ERROR", log_traceback: bool = True):
    """Decorator for handling exceptions in route handlers or other functions."""
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Assume request is the first argument if present and is a Request object
            request: Request | None = None
            if args and isinstance(args[0], Request):
                request = args[0]

            # Get logger from request state if available
            logger_instance = getattr(request.state, 'log_manager', None) if request and hasattr(request, 'state') else None
            if logger_instance is None or not hasattr(logger_instance, 'bind'):
                print("Warning: Logger not found or invalid in request state for @handle_exceptions")
                bound_logger = logging.getLogger("fallback_logger")
            else:
                request_id = getattr(request.state, 'request_id', 'N/A') if request and hasattr(request, 'state') else 'N/A'
                try:
                    bound_logger = logger_instance.bind(request_id=request_id, function_name=func.__name__)
                except Exception as bind_error:
                    print(f"Error binding logger context: {bind_error}")
                    bound_logger = logger_instance

            try:
                # Directly call the function, letting FastAPI handle dependency injection
                result = await func(*args, **kwargs)
                return result
            except HTTPException as e:
                raise e
            except MCPError as e:
                log_method = getattr(bound_logger, 'error', print)
                if log_traceback:
                    # Wrap custom fields in 'extra' dictionary
                    extra_data = {
                        "error_code": e.error_code,
                        "status_code": e.status_code,
                        "details": e.details,
                    }
                    log_method(
                        f"MCPError in {func.__name__}",
                        extra=extra_data,
                        exc_info=True
                    )
                raise e
            except Exception as e:
                log_method = getattr(bound_logger, 'exception', print)
                if log_traceback:
                    log_method(f"Unexpected error in {func.__name__}")

                # Create a generic MCPError for unhandled exceptions
                raise MCPError(
                    message=f"An unexpected error occurred: {str(e)}",
                    status_code=500,
                    error_code=error_code,
                    details={"exception_type": type(e).__name__}
                ) from e

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
    """Middleware for handling errors and adding request context."""
    
    def __init__(self, app, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger
        
    async def dispatch(self, request: Request, call_next):
        """Process request and handle errors."""
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request context to logger
        self.logger = self.logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None
        )
        
        try:
            # Process request
            response = await call_next(request)
            return response
            
        except MCPError as e:
            # Handle known MCP errors
            # Wrap custom fields in 'extra' dictionary for logging
            extra_data = {
                 "error_code": e.error_code,
                 "status_code": e.status_code,
                 "details": e.details,
            }
            self.logger.error(
                "MCP error occurred",
                extra=extra_data # Pass as extra
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "code": e.error_code,
                        "message": e.message,
                        "details": e.details,
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
            
        except Exception as e:
            # Handle unexpected errors
            self.logger.exception("Unexpected error occurred")
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred",
                        "request_id": request_id,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            ) 