"""
Core MCP Server - Provides core functionality and command execution.
"""

from typing import Any, Dict, Optional
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from ..utils.base_server import BaseServer
from ..utils.error_handling import handle_exceptions, MCPError
from ..utils.security import ApiKey

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

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
        
        @self.app.post("/api/v1/execute")
        @handle_exceptions()
        async def execute_command(
            command: str,
            timeout: Optional[int] = None,
            allow_background: bool = False,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Execute a command.
            
            Args:
                command: Command to execute
                timeout: Command timeout in seconds
                allow_background: Whether to allow background execution
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
                
            # Execute command
            with self.monitor.span_in_context(
                "execute_command",
                attributes={
                    "command": command,
                    "timeout": timeout,
                    "background": allow_background
                }
            ):
                return self.executor.execute(
                    command,
                    timeout=timeout,
                    allow_background=allow_background
                )
                
        @self.app.post("/api/v1/terminate/{pid}")
        @handle_exceptions()
        async def terminate_process(
            pid: int,
            force: bool = False,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Terminate a running process.
            
            Args:
                pid: Process ID to terminate
                force: Whether to force kill
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
            with self.monitor.span_in_context(
                "terminate_process",
                attributes={
                    "pid": pid,
                    "force": force
                }
            ):
                return self.executor.terminate(pid, force=force)
                
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
            command: str,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Add command to blacklist.
            
            Args:
                command: Command pattern to block
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
                attributes={"command": command}
            ):
                self.executor.blacklist.add(command)
                return {
                    "status": "success",
                    "message": f"Command pattern '{command}' blocked"
                }
                
        @self.app.post("/api/v1/unblock")
        @handle_exceptions()
        async def unblock_command(
            command: str,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Remove command from blacklist.
            
            Args:
                command: Command pattern to unblock
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
                
            # Remove from blacklist
            with self.monitor.span_in_context(
                "unblock_command",
                attributes={"command": command}
            ):
                self.executor.blacklist.discard(command)
                return {
                    "status": "success",
                    "message": f"Command pattern '{command}' unblocked"
                }

# Create server instance
server = CoreMCPServer()
app = server.app 