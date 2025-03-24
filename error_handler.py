#!/usr/bin/env python3
"""
Error Handler Module for MCP Browser

This module provides standardized error handling for the MCP Browser application,
including error codes, retry mechanisms, and exception handling decorators.
"""

import enum
import logging
import asyncio
import functools
import traceback
import time
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, cast
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("error_handler")


class ErrorCode(enum.Enum):
    """Standardized error codes for the MCP Browser application."""
    
    # Authentication errors (1xx)
    INVALID_CREDENTIALS = 100
    TOKEN_EXPIRED = 101
    INVALID_TOKEN = 102
    INSUFFICIENT_PERMISSIONS = 103
    
    # Browser operation errors (2xx)
    NAVIGATION_FAILED = 200
    TIMEOUT = 201
    ELEMENT_NOT_FOUND = 202
    JAVASCRIPT_ERROR = 203
    PAGE_CRASH = 204
    
    # Resource management errors (3xx)
    RESOURCE_EXHAUSTED = 300
    BROWSER_LAUNCH_FAILED = 301
    CONTEXT_CREATION_FAILED = 302
    RESOURCE_NOT_FOUND = 303
    
    # Input validation errors (4xx)
    INVALID_URL = 400
    INVALID_SELECTOR = 401
    INVALID_PARAMETERS = 402
    INVALID_OPERATION = 403
    
    # System errors (5xx)
    INTERNAL_ERROR = 500
    DEPENDENCY_ERROR = 501
    NETWORK_ERROR = 502
    RATE_LIMITED = 503
    
    @classmethod
    def to_http_status(cls, error_code: "ErrorCode") -> int:
        """Map error code to HTTP status code."""
        error_to_status = {
            # Authentication errors -> 401/403
            cls.INVALID_CREDENTIALS: 401,
            cls.TOKEN_EXPIRED: 401,
            cls.INVALID_TOKEN: 401,
            cls.INSUFFICIENT_PERMISSIONS: 403,
            
            # Browser operation errors -> 400/504
            cls.NAVIGATION_FAILED: 400,
            cls.TIMEOUT: 504,
            cls.ELEMENT_NOT_FOUND: 404,
            cls.JAVASCRIPT_ERROR: 400,
            cls.PAGE_CRASH: 500,
            
            # Resource management errors -> 429/500
            cls.RESOURCE_EXHAUSTED: 429,
            cls.BROWSER_LAUNCH_FAILED: 500,
            cls.CONTEXT_CREATION_FAILED: 500,
            cls.RESOURCE_NOT_FOUND: 404,
            
            # Input validation errors -> 400
            cls.INVALID_URL: 400,
            cls.INVALID_SELECTOR: 400,
            cls.INVALID_PARAMETERS: 400,
            cls.INVALID_OPERATION: 400,
            
            # System errors -> 500
            cls.INTERNAL_ERROR: 500,
            cls.DEPENDENCY_ERROR: 500,
            cls.NETWORK_ERROR: 502,
            cls.RATE_LIMITED: 429
        }
        return error_to_status.get(error_code, 500)


class ErrorDetail(BaseModel):
    """Detailed information about an error."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standardized error response."""
    success: bool = False
    error: ErrorDetail


class MCPBrowserException(Exception):
    """Base exception class for MCP Browser errors."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(message)
    
    def to_error_response(self) -> ErrorResponse:
        """Convert exception to standardized error response."""
        return ErrorResponse(
            error=ErrorDetail(
                code=self.error_code.name,
                message=self.message,
                details=self.details
            )
        )
    
    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR
    ) -> "MCPBrowserException":
        """Convert a generic exception to MCPBrowserException."""
        message = str(exception) or f"An error of type {type(exception).__name__} occurred"
        return cls(
            error_code=error_code,
            message=message,
            details={"exception_type": type(exception).__name__},
            cause=exception
        )
    
    def to_http_exception(self) -> Dict[str, Any]:
        """Convert to HTTP exception format."""
        status_code = ErrorCode.to_http_status(self.error_code)
        return {
            "status_code": status_code,
            "detail": self.to_error_response().dict()
        }


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 0.5
    max_delay: float = 5.0
    backoff_factor: float = 2.0
    retryable_errors: List[Type[Exception]] = []
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if retry should be attempted based on exception and attempt count."""
        if attempt >= self.max_attempts:
            return False
            
        # Check if exception type is in retryable errors
        for error_type in self.retryable_errors:
            if isinstance(exception, error_type):
                return True
                
        # Special handling for MCPBrowserException
        if isinstance(exception, MCPBrowserException):
            # Retry timeouts, network errors, and rate limiting
            retryable_codes = [
                ErrorCode.TIMEOUT,
                ErrorCode.NETWORK_ERROR,
                ErrorCode.RATE_LIMITED
            ]
            return exception.error_code in retryable_codes
            
        return False
    
    def get_delay(self, attempt: int) -> float:
        """Calculate the delay before the next retry attempt."""
        delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)


F = TypeVar('F', bound=Callable[..., Any])

def with_retry(config: Optional[RetryConfig] = None) -> Callable[[F], F]:
    """
    Decorator to add retry behavior to functions.
    
    Args:
        config: Retry configuration to use
        
    Returns:
        Decorated function with retry capability
    """
    retry_config = config or RetryConfig()
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            
            while True:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if not retry_config.should_retry(e, attempt):
                        logger.error(
                            f"Function {func.__name__} failed after {attempt} attempts: {str(e)}"
                        )
                        raise
                    
                    delay = retry_config.get_delay(attempt)
                    logger.warning(
                        f"Retry {attempt}/{retry_config.max_attempts} for {func.__name__} "
                        f"after {delay}s due to: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
                    attempt += 1
                    
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 1
            
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if not retry_config.should_retry(e, attempt):
                        logger.error(
                            f"Function {func.__name__} failed after {attempt} attempts: {str(e)}"
                        )
                        raise
                    
                    delay = retry_config.get_delay(attempt)
                    logger.warning(
                        f"Retry {attempt}/{retry_config.max_attempts} for {func.__name__} "
                        f"after {delay}s due to: {str(e)}"
                    )
                    
                    time.sleep(delay)
                    attempt += 1
        
        # Choose the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)
            
    return decorator


def handle_exceptions(func: F) -> F:
    """
    Decorator to handle exceptions in async functions.
    
    This decorator catches exceptions, logs them, and converts them
    to standardized error responses.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function that handles exceptions
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except MCPBrowserException as e:
            logger.error(
                f"MCPBrowserException in {func.__name__}: {e.message}",
                exc_info=True
            )
            return e.to_error_response()
        except Exception as e:
            logger.error(
                f"Unhandled exception in {func.__name__}: {str(e)}",
                exc_info=True
            )
            tb = traceback.format_exc()
            logger.debug(f"Traceback: {tb}")
            
            browser_ex = MCPBrowserException.from_exception(e)
            return browser_ex.to_error_response()
            
    return cast(F, wrapper) 