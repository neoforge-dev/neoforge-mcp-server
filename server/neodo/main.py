"""
Neo DO Server - Handles direct operations
"""

from mcp.server.fastmcp import FastMCP
import os
import sys
import subprocess
import signal
import psutil
import time
import shutil  # Added import
import stat    # Added import
from typing import Dict, Any, Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
import threading
import queue
import glob
import ast # Added import for calculate tool
import asyncio
import json
import logging
from pathlib import Path # Added import
from contextlib import nullcontext # Add import for nullcontext
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.security.api_key import APIKey, APIKeyHeader
from ..utils.config import ConfigManager, ServerConfig # Remove load_config, MCPConfig
from ..utils.monitoring import MonitoringManager # Restore relative import
from ..utils.security import SecurityManager # Restore relative import
from ..utils.error_handling import MCPError, ErrorCode, handle_exceptions # Changed error_handler to handle_exceptions
from ..utils.logging import LogManager
from mcp.common.neodo_common import (
    ExecuteCommandRequest, ExecuteCommandResponse, CheckFileExistenceRequest,
    CheckFileExistenceResponse, CreateFileRequest, CreateFileResponse,
    ReadFileRequest, ReadFileResponse, UpdateFileRequest, UpdateFileResponse,
    DeleteFileRequest, DeleteFileResponse, ListDirectoryRequest, ListDirectoryResponse,
    GetFileMetadataRequest, GetFileMetadataResponse, ChangePermissionsRequest,
    ChangePermissionsResponse, CreateDirectoryRequest, CreateDirectoryResponse,
    SearchFilesRequest, SearchFilesResponse, ExecuteScriptRequest, ExecuteScriptResponse
)
from mcp.common.monitoring import Monitor
from mcp.common.decorators import mcp_tool
from dependency_injector import containers, providers # Import containers, providers
from dependency_injector.wiring import Provide, inject # Import Provide and inject
# from mcp.server.models import BaseMCPModel # Removed unused import
from mcp.server.server import MCPServer

# Adjusted relative imports - Change to absolute
# from ...decorators import trace_tool, metrics_tool
from decorators import trace_tool, metrics_tool

# MCP specific imports
# from mcp.common.config import Config as MCPConfig # Remove this unused/incorrect import
# from mcp.common.data_models.command import CommandOutput, CommandResult, CommandStatus # Remove
# from mcp.common.data_models.file_io import FileData, FileInfo, FileList # Remove
# from mcp.common.data_models.process import ProcessInfo, ProcessList # Remove
# from mcp.common.data_models.session import SessionInfo, SessionList # Remove
# from mcp.common.monitoring import MonitorEntry # Remove
# from mcp.common.permissions import PermissionLevel # Remove
from mcp.server.fastmcp.server import FastMCP
# from mcp.server.fastmcp.tool_arguments import Arg, ArgSource # Assuming unused, remove
# from mcp.server.server_config import ServerConfig # Assuming unused, remove
# from mcp.utils.api_key import get_api_key_dependency # Assuming unused, remove
# from mcp.utils.decorators import mcp_tool # Assuming unused, remove
# from mcp.utils.dependency_injection import common_dependencies # Assuming unused, remove
# from mcp.utils.error_handling import ErrorHandlingLogger # Assuming unused, remove
from ..utils.monitoring import MonitoringManager # Restore relative import
from ..utils.security import SecurityManager # Restore relative import
# from mcp.utils.security import SecurityManager # Assuming unused, remove

# Dependencies specific to this server (if any)
# Assuming a hypothetical DOManager for DigitalOcean operations
# from .do_manager import DOManager

# Constants
NEODO_API_KEY_NAME = "X-NEODO-API-KEY"

# Initialize tracer
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "neo-do-server",
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
})

# Global variables for process management
session_lock = threading.Lock()
active_sessions = {}
output_queues = {}
blacklisted_commands = set(['rm -rf /', 'mkfs'])

# Initialize tracing if not in test mode
is_test_mode = "pytest" in sys.modules
if not is_test_mode:
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)
else:
    # Mock tracer if in test mode
    class MockTracer:
        def start_as_current_span(self, *args, **kwargs):
            class MockSpan:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def set_attribute(self, *args): pass
                def record_exception(self, *args): pass
            return MockSpan()
    tracer = MockTracer()

def is_command_safe(command: str) -> bool:
    """Check if a command is safe to execute."""
    # Check against blacklisted commands
    if any(cmd in command for cmd in blacklisted_commands):
        return False

    # Add more safety checks as needed
    return True

# --- Configuration Loading (MUST be before AppContainer) ---
config_manager = ConfigManager()
try:
    global_config: ServerConfig = config_manager.load_config("neodo")
except MCPError as e:
    logging.error(f"Failed to load 'neodo' config: {e}. Using default ServerConfig.")
    global_config = ServerConfig(name="neodo", port=8002)

# --- Logging Setup (AFTER Config Loading) ---
log_manager = LogManager(
    name=global_config.name or "neodo_mcp",
    log_level=global_config.log_level or "INFO",
    log_dir=getattr(global_config, 'log_directory', None),
    enable_json=getattr(global_config, 'log_enable_json', True),
    enable_console=getattr(global_config, 'log_enable_console', True),
    enable_file=getattr(global_config, 'log_enable_file', True),
    enable_structlog=getattr(global_config, 'log_enable_structlog', True)
)
logger = log_manager.get_logger()

# --- Server Definition (BEFORE AppContainer) ---
class NeoDOServer(MCPServer):
    """
    Neo Development Operations MCP Server.

    Handles file system operations, command execution, and script running
    within the defined workspace.
    """
    # Modify __init__ to accept dependencies directly, not via Depends
    def __init__(
        self,
        config: ServerConfig,
        monitoring_manager: Monitor,
        security_manager: SecurityManager,
        logger_instance: logging.Logger
    ):
        super().__init__(config.name, config.version)
        self.config = config
        self.logger = logger_instance # Store logger instance
        neodo_config = getattr(config, 'neodo_config', None)
        if neodo_config and hasattr(neodo_config, 'workspace_root'):
            self.workspace = Path(neodo_config.workspace_root).resolve()
        else:
            self.logger.warning("neodo_config or workspace_root not found... Using default...")
            self.workspace = Path("./neodo_workspace").resolve()
        self.monitoring = monitoring_manager
        self.security = security_manager
        self._ensure_workspace()
        self.logger.info(f"NeoDO server initialized. Workspace: {self.workspace}")

    def _ensure_workspace(self):
        """Ensure the workspace directory exists."""
        try:
            self.workspace.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Workspace directory ensured: {self.workspace}")
        except OSError as e:
            self.logger.error(f"Failed to create workspace directory {self.workspace}: {e}")
            raise MCPError(ErrorCode.WORKSPACE_ERROR, f"Failed to create workspace: {e}")

    def _resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative path against the workspace root and ensure it's within the workspace."""
        if not relative_path:
             raise MCPError(ErrorCode.INVALID_INPUT, "Path cannot be empty.")

        # Clean the path (handle '..' etc.)
        try:
            resolved_path = (self.workspace / relative_path).resolve()
        except Exception as e: # Catch potential resolution errors
             raise MCPError(ErrorCode.INVALID_PATH, f"Invalid path format '{relative_path}': {e}")

        # Security check: Ensure the resolved path is still within the workspace
        if self.workspace not in resolved_path.parents and resolved_path != self.workspace:
            self.logger.warning(f"Attempt to access path outside workspace: {resolved_path} (relative: {relative_path})")
            raise MCPError(ErrorCode.ACCESS_DENIED, f"Path '{relative_path}' is outside the allowed workspace.")

        return resolved_path

    # --- Tool Methods ---

    @mcp_tool(description="Executes a shell command within the defined workspace.")
    @handle_exceptions()
    @Monitor.monitored_call # Assuming decorator works like this
    async def execute_command(self, request: ExecuteCommandRequest) -> ExecuteCommandResponse:
        # Implementation of execute_command method
        pass

    @mcp_tool(description="Checks if a file or directory exists within the workspace.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def check_file_existence(self, request: CheckFileExistenceRequest) -> CheckFileExistenceResponse:
        # Implementation
        pass

    @mcp_tool(description="Creates a new file with optional content.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def create_file(self, request: CreateFileRequest) -> CreateFileResponse:
        # Implementation
        pass

    @mcp_tool(description="Reads the content of a file.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def read_file(self, request: ReadFileRequest) -> ReadFileResponse:
        # Implementation
        pass

    @mcp_tool(description="Updates the content of an existing file.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def update_file(self, request: UpdateFileRequest) -> UpdateFileResponse:
        # Implementation
        pass

    @mcp_tool(description="Deletes a file within the workspace.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def delete_file(self, request: DeleteFileRequest) -> DeleteFileResponse:
        # Implementation of delete_file method
        pass

    @mcp_tool(description="Lists the contents of a directory within the workspace.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def list_directory(self, request: ListDirectoryRequest) -> ListDirectoryResponse:
        # Implementation of list_directory method
        pass

    @mcp_tool(description="Gets metadata for a file or directory within the workspace.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def get_file_metadata(self, request: GetFileMetadataRequest) -> GetFileMetadataResponse:
        # Implementation of get_file_metadata method
        pass

    @mcp_tool(description="Changes the permissions of a file or directory.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def change_permissions(self, request: ChangePermissionsRequest) -> ChangePermissionsResponse:
        # Implementation of change_permissions method
        pass

    @mcp_tool(description="Creates a new directory within the workspace.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def create_directory(self, request: CreateDirectoryRequest) -> CreateDirectoryResponse:
        # Implementation of create_directory method
        pass

    @mcp_tool(description="Searches for files within the workspace based on a pattern.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def search_files(self, request: SearchFilesRequest) -> SearchFilesResponse:
        # Implementation of search_files method
        pass

    @mcp_tool(description="Executes a script within the workspace.")
    @handle_exceptions()
    @Monitor.monitored_call
    async def execute_script(self, request: ExecuteScriptRequest) -> ExecuteScriptResponse:
        # Implementation of execute_script method
        pass


# --- Dependency Injection Container (AFTER Server Definition) ---
class AppContainer(containers.DeclarativeContainer):
    config = providers.Object(global_config) # Use loaded global_config
    logger = providers.Object(logger) # Use instantiated logger

    monitoring_manager = providers.Factory(
        Monitor,
        enabled=providers.Callable(
            lambda config: getattr(getattr(config, 'monitoring_config', None), 'enabled', False),
            config=config
        )
    )
    security_manager = providers.Factory(
        SecurityManager,
        redis_url=providers.Callable(
             lambda config: getattr(config, 'redis_url', "redis://localhost:6379/0"),
             config=config
        ),
        jwt_secret=providers.Callable(
             lambda config: getattr(config, 'jwt_secret', None),
             config=config
        ),
        api_keys=providers.Callable(
             lambda config: getattr(config, 'api_keys', None),
             config=config
        ),
        enable_auth=providers.Callable(
            lambda config: getattr(getattr(config, 'security_config', getattr(config, 'auth_config', None)), 'enabled', getattr(config, 'enable_auth', True)),
            config=config
        ),
        auth_token=providers.Callable(
             lambda config: getattr(config, 'auth_token', None),
             config=config
        ),
        rate_limit_window=providers.Callable(
             lambda config: getattr(config, 'rate_limit_window', 60),
             config=config
        ),
        rate_limit_max_requests=providers.Callable(
             lambda config: getattr(config, 'rate_limit_max_requests', 100),
             config=config
        ),
        blocked_ips=providers.Callable(
             lambda config: getattr(getattr(config, 'security_config', getattr(config, 'auth_config', None)), 'blocked_ips', None),
             config=config
        )
    )
    neodo_server = providers.Factory(
        NeoDOServer,
        config=config,
        monitoring_manager=monitoring_manager,
        security_manager=security_manager,
        logger_instance=logger
    )

container = AppContainer()

# --- Dependency Injection Setup (Overrides/Wiring happen in create_app) ---

# --- FastAPI App Creation ---
@inject
def create_app(
    app_config: Optional[ServerConfig] = None,
) -> FastAPI:
    """Factory function to create the FastAPI application."""

    # Override the container's config if a specific one is passed
    # Check if app_config is provided, otherwise use the globally loaded one (already in container)
    config_override = app_config # Use the specific config if passed

    # Use a context manager for overriding to ensure it's reset
    # Only override if a specific app_config was passed to the factory
    config_context = container.config.override(config_override) if config_override else nullcontext()

    with config_context:
        # Wire container - Use the CLASS name
        # Do this *before* creating the app or server instance that might use injected routes
        container.wire(modules=[sys.modules[__name__]])

        # Get server instance from the container
        # This now uses the potentially overridden config
        server = container.neodo_server()

        # Create FastAPI app instance using the correct config from the container
        # Ensure the config is accessed correctly after potential override
        current_app_config = container.config() # Get the potentially overridden config
        app = FastAPI(title=current_app_config.name, version=current_app_config.version)

        # --- Add Middleware ---
        # ... (add middleware as needed) ...

        # --- Register Routes/Tools --- #
        # Routes can now potentially use @inject
        app.add_api_route("/tools/execute_command", server.execute_command, methods=["POST"])
        app.add_api_route("/tools/check_file_existence", server.check_file_existence, methods=["POST"])
        # ... (add other routes) ...
        app.add_api_route("/tools/search_files", server.search_files, methods=["POST"])
        app.add_api_route("/tools/execute_script", server.execute_script, methods=["POST"])

        # Use the correct logger instance (it's provided globally or could be injected)
        container.logger().info(f"FastAPI app created for {current_app_config.name} v{current_app_config.version}")
        # Override is automatically reset when exiting the 'with' block if context manager was used

    return app

# --- App Instantiation ---
app = create_app()

# --- Main Execution Block (for standalone running) ---
# Kept for potential direct execution, but primary use is via run_servers.py
if __name__ == "__main__":
    # Ensure config is loaded if running standalone
    # (The global config load at the top should handle this)
    if not global_config:
         print("Error: Configuration could not be loaded.")
         exit(1)

    print(f"Starting {global_config.name} v{global_config.version} on port {global_config.port}")
    uvicorn.run(
        "server.neodo.main:app", # Point to the app object created by the factory
        host="0.0.0.0",
        port=global_config.port,
        log_level=global_config.log_level.lower(),
        reload=global_config.reload,
        workers=global_config.max_processes if not global_config.reload else 1 # Uvicorn manages workers
        # Add other uvicorn settings from config if needed (e.g., ssl)
    ) 