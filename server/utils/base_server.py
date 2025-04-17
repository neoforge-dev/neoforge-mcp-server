"""Base server class for all server implementations."""

from typing import Any, Dict, Optional, List
from fastapi import FastAPI, Request, Response, HTTPException, Security, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import time
import uuid

# Rate Limiting imports
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .config import ConfigManager, ServerConfig
from .logging import LogManager
from .monitoring import MonitoringManager
from .security import SecurityManager, ApiKey
from .error_handling import (
    MCPError, ValidationError, AuthenticationError, AuthorizationError,
    NotFoundError, ConflictError, ErrorHandlerMiddleware, handle_exceptions
)

# Initialize Rate Limiter
# Use IP address as the key function
limiter = Limiter(key_func=get_remote_address)

# API key header
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging request details."""
    
    async def dispatch(
        self, request: Request, call_next
    ) -> Response:
        """Process request and log details.
        
        Args:
            request: The incoming request
            call_next: The next middleware in the chain
            
        Returns:
            The response
        """
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Skip logging for SSE connections
        if request.url.path == "/sse":
            return response
        
        # Prepare log data
        log_data = {
            "extra": {
                "client": request.client.host if request.client else "unknown",
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time
            }
        }
        
        # Get logger from request state since response might not have state
        log_manager = request.state.log_manager
        
        # Log based on status code
        if response.status_code >= 500:
            log_manager.error("Server error", extra=log_data["extra"])
        elif response.status_code >= 400:
            log_manager.warning("Client error", extra=log_data["extra"])
        else:
            log_manager.info("Request processed", extra=log_data["extra"])
            
        return response

class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting requests."""
    
    async def dispatch(
        self, request: Request, call_next
    ) -> Response:
        """Process request and apply rate limits.
        
        Args:
            request: The incoming request
            call_next: The next middleware in the chain
            
        Returns:
            The response or rate limit exceeded error
        """
        # Skip rate limiting for non-API routes
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)
            
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return await call_next(request)
            
        # Check rate limit
        security_manager = request.state.security_manager
        if not security_manager.check_rate_limit(api_key):
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={"Retry-After": "60"}
            )
            
        return await call_next(request)

class BaseServer:
    """Base server class for all server implementations."""

    def __init__(self, app_name: str):
        """Initialize the server managers and config ONLY."""
        
        # Remove app creation and configuration from __init__
        # self.app = FastAPI(
        #     title=app_name,
        #     docs_url=None,
        #     redoc_url=None
        # )
        # self.app.state.limiter = limiter
        # self.app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        
        # Initialize managers ONLY
        self._init_managers(app_name)
        
        # Defer app state setup, middleware, and routes to explicit calls
        # self.app.state.config = self.config
        # self.app.state.logger = self.logger
        # self.app.state.monitor = self.monitor
        # self.app.state.security = self.security
        # self._setup_middleware()
        # self.register_routes()
        
    def _init_managers(self, app_name: str) -> None:
        """Initialize server managers."""
        # Load config
        config_manager = ConfigManager()  # Instantiate ConfigManager
        self.config = config_manager.load_config(server_name=app_name)
        
        # Initialize logging
        self.logger = LogManager(
            name=app_name,
            log_level=self.config.log_level,
            log_dir=self.config.log_file
        ).get_logger()
        
        # Initialize monitoring if enabled
        if self.config.enable_metrics or self.config.enable_tracing:
            self.monitor = MonitoringManager(
                app_name=app_name,
                metrics_port=self.config.metrics_port,
                enable_tracing=self.config.enable_tracing
            )
        else:
            self.monitor = None
            
        # Restore SecurityManager initialization
        self.security = SecurityManager(
            api_keys=self.config.api_keys,
            enable_auth=self.config.enable_auth,
            auth_token=self.config.auth_token
        )
        
    def setup_app_state(self, app: FastAPI) -> None:
        """Add server managers and config to the FastAPI app state."""
        app.state.limiter = limiter
        app.state.config = self.config
        app.state.logger = self.logger
        app.state.monitor = self.monitor
        app.state.security = self.security

    def setup_middleware(self, app: FastAPI) -> None:
        """Setup server middleware on the provided app instance."""
        # Add error handling middleware
        app.add_middleware(
            ErrorHandlerMiddleware,
            logger=self.logger
        )
        
        # Add CORS middleware if origins are configured
        if self.config.allowed_origins:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.allowed_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"]
            )
            
        # Add GZip compression if enabled
        if self.config.enable_compression:
            app.add_middleware(
                GZipMiddleware,
                minimum_size=1000
            )
            
        # Add trusted host middleware
        if self.config.trusted_proxies:
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=self.config.trusted_proxies
            )
            
        # Add session middleware if enabled
        if self.config.enable_sessions:
            app.add_middleware(
                SessionMiddleware,
                secret_key=self.config.session_secret,
                session_cookie="session",
                max_age=3600
            )
        
        # Add state middleware (needed by rate limiter key func if custom logic used)
        @app.middleware("http")
        async def add_state(request: Request, call_next):
            """Add state to request."""
            # Add state
            request.state.log_manager = self.logger
            request.state.security_manager = self.security
            request.state.monitor_manager = self.monitor
            request.state.config_manager = self.config
            
            # Process request
            return await call_next(request)
            
    def register_routes(self, app: FastAPI) -> None:
        """Register API routes on the provided app instance."""
        # Enable API docs if configured
        if self.config.enable_docs:
            # Assign docs attributes directly to the app
            app.docs_url = self.config.docs_url
            app.redoc_url = self.config.redoc_url
            app.openapi_url = self.config.openapi_url
            
        @app.get("/health")
        @handle_exceptions()
        # @limiter.limit("10/second") # Temporarily removed for debugging 422 error
        async def health_check(request: Request) -> Dict[str, Any]:
            """Provide a basic health check endpoint."""
            # Access config and managers via self, not request.state
            # as state might not be fully set during this route definition
            return {
                "status": "healthy",
                "service": self.config.name,
                "version": self.config.version,
                "monitoring": {
                    "metrics": self.config.enable_metrics,
                    "tracing": self.config.enable_tracing
                }
            }
            
    async def get_api_key(
        self,
        api_key: str | None = Security(api_key_header)
    ) -> ApiKey:
        """Dependency to validate the API key."""
        if api_key is None:
            # Explicitly raise AuthenticationError (maps to 401) if header is missing
            raise AuthenticationError("API key header missing")

        try:
            validated_key = self.security.validate_api_key(api_key)
            return validated_key
        except AuthenticationError as e:
            # Re-raise specific auth errors
            raise e
        except Exception as e:
            # Catch any other validation errors (e.g., internal issues) and map to generic auth error
            self.logger.error(f"API key validation failed unexpectedly: {e}", exc_info=True)
            raise AuthenticationError("Invalid API key") # Keep response generic

    def get_app(self) -> FastAPI:
        """Get the FastAPI application.
        
        Returns:
            FastAPI application
        """
        return self.app 