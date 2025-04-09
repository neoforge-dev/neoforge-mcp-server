"""Base server class for all server implementations."""

from typing import Any, Dict, Optional, List
from fastapi import FastAPI, Request, Response, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
import time
import uuid

from .config import ConfigManager, ServerConfig
from .logging import LogManager
from .monitoring import MonitoringManager
from .security import SecurityManager, ApiKey
from .error_handling import handle_exceptions, MCPError

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

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
        """Initialize the server.
        
        Args:
            app_name: Name of the application
        """
        # Create FastAPI app
        self.app = FastAPI(
            title=app_name,
            docs_url=None,  # Will be set based on config
            redoc_url=None  # Will be set based on config
        )
        
        # Initialize managers
        self._init_managers(app_name)
        
        # Add state to app
        self.app.state.config = self.config
        self.app.state.logger = self.logger
        self.app.state.monitor = self.monitor
        self.app.state.security = self.security
        
        # Setup middleware
        self._setup_middleware()
        
        # Initialize routes
        self.register_routes()
        
    def _init_managers(self, app_name: str) -> None:
        """Initialize server managers.
        
        Args:
            app_name: Name of the application
        """
        # Initialize config
        self.config_manager = ConfigManager()
        self.config: ServerConfig = self.config_manager.load_config(app_name)
        
        # Initialize logger
        self.log_manager = LogManager(
            app_name,
            log_dir=self.config.log_file,
            log_level=self.config.log_level
        )
        self.logger = self.log_manager.get_logger()
        
        # Initialize monitoring if enabled
        if self.config.enable_metrics or self.config.enable_tracing:
            self.monitor = MonitoringManager(
                service_name=app_name,
                service_version=self.config.version,
                tracing_endpoint=self.config.tracing_endpoint if self.config.enable_tracing else None,
                enable_tracing=self.config.enable_tracing,
                enable_metrics=self.config.enable_metrics
            )
        else:
            self.monitor = None
            
        # Initialize security
        self.security = SecurityManager(
            secret_key=self.config.auth_token,
            config_api_keys=self.config.api_keys
        )
        
    def _setup_middleware(self) -> None:
        """Setup server middleware."""
        # Add CORS middleware
        if self.config.allowed_origins:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.allowed_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"]
            )
            
        # Add compression middleware if enabled
        if self.config.enable_compression:
            self.app.add_middleware(
                GZipMiddleware,
                minimum_size=1000,
                compresslevel=self.config.compression_level
            )
            
        # Add trusted host middleware if proxy settings configured
        if self.config.enable_proxy and self.config.trusted_proxies:
            self.app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=self.config.trusted_proxies
            )
            
        # Add session middleware if auth enabled
        if self.config.enable_auth:
            self.app.add_middleware(
                SessionMiddleware,
                secret_key=self.config.auth_token or str(uuid.uuid4())
            )
            
        # Add request logging middleware
        self.app.add_middleware(RequestLoggingMiddleware)
        
        # Add rate limiting middleware
        if self.config.enable_rate_limiting:
            self.app.add_middleware(RateLimitingMiddleware)
            
        # Add state middleware
        @self.app.middleware("http")
        async def add_state(request: Request, call_next):
            """Add state to request.
            
            Args:
                request: The incoming request
                call_next: The next middleware in the chain
                
            Returns:
                The response
            """
            # Add state
            request.state.log_manager = self.logger
            request.state.security_manager = self.security
            request.state.monitor_manager = self.monitor
            request.state.config_manager = self.config
            
            # Process request
            return await call_next(request)
            
    def register_routes(self) -> None:
        """Register API routes."""
        # Enable API docs if configured
        if self.config.enable_docs:
            self.app.docs_url = self.config.docs_url
            self.app.redoc_url = self.config.redoc_url
            self.app.openapi_url = self.config.openapi_url
            
        @self.app.get("/health")
        @handle_exceptions()
        async def health_check() -> Dict[str, Any]:
            """Health check endpoint."""
            if not self.config.enable_health_checks:
                return {"status": "disabled"}
                
            # Record resource metrics if monitoring enabled
            if self.monitor:
                self.monitor.record_resource_usage()
                
            return {
                "status": "healthy",
                "service": self.app.title,
                "version": self.config.version,
                "monitoring": {
                    "metrics": self.config.enable_metrics,
                    "tracing": self.config.enable_tracing
                }
            }
            
    async def get_api_key(self, api_key: str = Security(api_key_header)) -> ApiKey:
        """Validate API key and return key info.
        
        Args:
            api_key: API key from request header
            
        Returns:
            ApiKey object
            
        Raises:
            HTTPException if key is invalid
        """
        try:
            return self.security.validate_api_key(api_key)
        except MCPError as e:
            raise HTTPException(
                status_code=401,
                detail=str(e)
            )
            
    def get_app(self) -> FastAPI:
        """Get the FastAPI application.
        
        Returns:
            FastAPI application
        """
        return self.app 