"""
Core MCP Server - Provides core functionality and command execution.
"""

from typing import Any, Dict, Optional, Tuple
from fastapi import Depends, HTTPException, Security, Request, FastAPI, Body
from fastapi.security import APIKeyHeader
from fastapi.responses import StreamingResponse
import json
import time
import asyncio
import uuid
import os
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..utils.base_server import BaseServer
from ..utils.error_handling import handle_exceptions, MCPError
from ..utils.security import ApiKey
# Import CommandExecutor and SecurityManager for type hinting and dependency functions
from ..utils.command_execution import CommandExecutor
from ..utils.security import SecurityManager

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

# Pydantic model for /execute request body
class ExecuteRequest(BaseModel):
    command: str
    timeout: Optional[int] = None
    allow_background: bool = False

class TerminateRequest(BaseModel):
    """Request model for terminating a process."""
    force: bool = Field(False, description="Whether to forcefully terminate the process")

class CommandManageRequest(BaseModel):
    """Request model for blocking/unblocking a command pattern."""
    command: str = Field(..., description="The command pattern to manage")

class CoreMCPServer(BaseServer):
    """Core MCP Server implementation."""
    
    def __init__(self):
        """Initialize Core MCP Server (Managers only)."""
        super().__init__("core_mcp")
        # Initialize any Core specific managers if needed
        
    def register_routes(self, app: FastAPI) -> None: # Accept app
        """Register core API routes."""
        # Register base routes (like /health)
        super().register_routes(app) # Pass app to super
        
        # Add core specific routes using the passed app instance
        prefix = self.config.api_prefix # Assuming config has api_prefix

        @app.post(f"{prefix}/execute_command", tags=["Core Tools"]) # Use app decorator
        @handle_exceptions()
        # @limiter.limit("10/minute") # Apply rate limiting if needed
        async def execute_command(
            request: Request,
            cmd_request: ExecuteRequest, # Use Pydantic model for request body
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Execute a command.
            
            Args:
                request: FastAPI request object
                cmd_request: Command request body
                api_key: Validated API key
                
            Returns:
                Command execution result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "execute:command"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Validate command
            if cmd_request.command in self.config.command_blacklist:
                raise HTTPException(
                    status_code=400,
                    detail="Command is blacklisted"
                )
                
            # Execute command asynchronously
            result = await self.executor.execute_async(
                cmd_request.command,
                timeout=cmd_request.timeout,
                allow_background=cmd_request.allow_background
            )
            return result

        @app.post(f"{prefix}/manage_process", tags=["Core Tools"]) # Use app decorator
        @handle_exceptions()
        async def manage_process(
            request: Request,
            proc_request: TerminateRequest, # Use Pydantic model
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Terminate a running process.
            
            Args:
                request: FastAPI request object
                proc_request: Process request body
                api_key: Validated API key
                
            Returns:
                Termination result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "terminate:process"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Terminate process
            force_terminate = proc_request.force # Get force from body
            with self.monitor.span_in_context(
                "terminate_process",
                attributes={
                    "pid": proc_request.pid,
                    "force": force_terminate # Use value from body
                }
            ):
                return self.executor.terminate(proc_request.pid, force=force_terminate) # Pass correct value

        @app.post(f"{prefix}/file_operation", tags=["Core Tools"]) # Use app decorator
        @handle_exceptions()
        async def file_operation(
            request: Request,
            file_request: CommandManageRequest, # Use Pydantic model
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Add command to blacklist.
            
            Args:
                request: FastAPI request object
                file_request: File operation request body
                api_key: Validated API key
                
            Returns:
                Operation result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "manage:blacklist"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Add to blacklist
            with self.monitor.span_in_context(
                "block_command",
                attributes={"command": file_request.command}
            ):
                self.executor.blacklist.add(file_request.command)
                return {
                    "status": "success",
                    "message": f"Command pattern '{file_request.command}' blocked"
                }

        @app.get(f"{prefix}/system_info", tags=["Core Info"]) # Use app decorator
        @handle_exceptions()
        async def get_system_info(
            request: Request,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            self.security.check_permission(api_key, "read:system_info")
            # Replace with actual system info gathering logic
            return {
                "cpu_usage": 50.0,
                "memory_usage": 60.5,
                "disk_usage": 70.2,
                "os": "Linux"
            }

# Dependency provider functions (needed for testing overrides)
def get_command_executor() -> CommandExecutor:
    # This function is primarily for dependency injection in tests.
    # In the actual app, the executor is accessed via self.executor.
    # Raise an error if called outside of a test override context.
    # It's okay for this to be simple as tests override it.
    raise NotImplementedError("This dependency provider is intended for test overrides.")

def get_security_manager() -> SecurityManager:
    # This function is primarily for dependency injection in tests.
    # In the actual app, the manager is accessed via self.security.
    # Raise an error if called outside of a test override context.
    # It's okay for this to be simple as tests override it.
    raise NotImplementedError("This dependency provider is intended for test overrides.")

# Factory function remains separate
def create_app(config=None, env=None) -> Tuple[FastAPI, CoreMCPServer]: # Return tuple
    """Factory function to create the FastAPI application."""
    server = CoreMCPServer() # Creates server, loads config via BaseServer init
    
    # Create the FastAPI app
    app = FastAPI(title=server.config.name, version=server.config.version)
    
    # Use the server instance to set up the app
    server.setup_app_state(app) # Setup state
    server.setup_middleware(app) # Setup middleware
    server.register_routes(app)  # Register routes

    # Return both the app and the server instance
    return app, server

# Remove direct instantiation
# server = CoreMCPServer()
# app = server.app 