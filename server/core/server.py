"""
Core MCP Server - Provides core functionality and command execution.
"""

from typing import Any, Dict, Optional
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
        """Initialize Core MCP Server."""
        super().__init__("core_mcp")
        
        # Register routes
        self.register_routes()
        
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
            
    def register_routes(self) -> None:
        """Register API routes."""
        super().register_routes()
        
        @self.app.get("/sse")
        async def sse_endpoint(request: Request):
            """Server-Sent Events endpoint for real-time updates."""
            async def event_generator():
                try:
                    # Check rate limit for SSE connections
                    api_key = request.headers.get("X-API-Key")
                    if api_key and not self.security.check_rate_limit(api_key):
                        error_event = {
                            "type": "error",
                            "data": {
                                "code": "rate_limit_exceeded",
                                "message": "Rate limit exceeded"
                            }
                        }
                        yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
                        return

                    # Keep connection alive and send periodic updates
                    while True:
                        if await request.is_disconnected():
                            break
                            
                        update_event = {
                            "type": "update",
                            "data": {
                                "id": str(uuid.uuid4()),
                                "timestamp": int(time.time()),
                                "status": "ok"
                            }
                        }
                        yield f"event: update\ndata: {json.dumps(update_event)}\n\n"
                        await asyncio.sleep(1)  # Send updates every second
                        
                except Exception as e:
                    error_event = {
                        "type": "error",
                        "data": {
                            "code": "internal_error",
                            "message": str(e)
                        }
                    }
                    yield f"event: error\ndata: {json.dumps(error_event)}\n\n"
                    
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "Content-Type": "text/event-stream"
                }
            )
        
        @self.app.post("/api/v1/execute")
        @handle_exceptions()
        async def execute_command(
            request_body: ExecuteRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Execute a command.
            
            Args:
                request_body: Request body containing command details
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
                
            # Execute command using values from the request body
            with self.monitor.span_in_context(
                "execute_command",
                attributes={
                    "command": request_body.command,
                    "timeout": request_body.timeout,
                    "background": request_body.allow_background
                }
            ):
                return self.executor.execute(
                    request_body.command,
                    timeout=request_body.timeout,
                    allow_background=request_body.allow_background
                )
                
        @self.app.post("/api/v1/terminate/{pid}")
        @handle_exceptions()
        async def terminate_process(
            pid: int, # PID comes from path
            request_body: TerminateRequest, # Force comes from body
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Terminate a running process.
            
            Args:
                pid: Process ID to terminate
                request_body: Request body containing the force flag
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
            force_terminate = request_body.force # Get force from body
            with self.monitor.span_in_context(
                "terminate_process",
                attributes={
                    "pid": pid,
                    "force": force_terminate # Use value from body
                }
            ):
                return self.executor.terminate(pid, force=force_terminate) # Pass correct value
                
        @self.app.get("/api/v1/output/{pid}")
        @handle_exceptions()
        async def get_output(
            pid: int,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Get output from a running process.
            
            Args:
                pid: Process ID
                api_key: Validated API key
                
            Returns:
                Process output
            """
            # Check permissions
            if not self.security.check_permission(api_key, "read:output"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Get output
            with self.monitor.span_in_context(
                "get_output",
                attributes={"pid": pid}
            ):
                return self.executor.get_output(pid)
                
        @self.app.get("/api/v1/processes")
        @handle_exceptions()
        async def list_processes(
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """List all active processes.
            
            Args:
                api_key: Validated API key
                
            Returns:
                List of active processes
            """
            # Check permissions
            if not self.security.check_permission(api_key, "read:processes"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # List processes
            with self.monitor.span_in_context("list_processes"):
                return self.executor.list_processes()
                
        @self.app.post("/api/v1/block")
        @handle_exceptions()
        async def block_command(
            request_body: CommandManageRequest, # Command from body
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Add command to blacklist.
            
            Args:
                request_body: Request body containing the command pattern
                api_key: Validated API key
                
            Returns:
                Operation result
            """
            command_to_block = request_body.command
            # Check permissions
            if not self.security.check_permission(api_key, "manage:blacklist"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Add to blacklist
            with self.monitor.span_in_context(
                "block_command",
                attributes={"command": command_to_block}
            ):
                self.executor.blacklist.add(command_to_block)
                return {
                    "status": "success",
                    "message": f"Command pattern '{command_to_block}' blocked"
                }
                
        @self.app.post("/api/v1/unblock")
        @handle_exceptions()
        async def unblock_command(
            request_body: CommandManageRequest, # Command from body
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Remove command from blacklist.
            
            Args:
                request_body: Request body containing the command pattern
                api_key: Validated API key
                
            Returns:
                Operation result
            """
            command_to_unblock = request_body.command
            # Check permissions
            if not self.security.check_permission(api_key, "manage:blacklist"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Remove from blacklist
            with self.monitor.span_in_context(
                "unblock_command",
                attributes={"command": command_to_unblock}
            ):
                self.executor.blacklist.discard(command_to_unblock)
                return {
                    "status": "success",
                    "message": f"Command pattern '{command_to_unblock}' unblocked"
                }

# App Factory pattern
def create_app() -> FastAPI:
    """Factory function to create the CoreMCPServer FastAPI app."""
    server = CoreMCPServer()
    # Routes are registered in BaseServer init
    return server.app

# Remove direct instantiation
# server = CoreMCPServer()
# app = server.app 