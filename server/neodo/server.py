"""
Neo DO MCP Server - Provides DigitalOcean operations and management.
"""

from typing import Any, Dict, Optional, List
from fastapi import Depends, HTTPException, Security, Body
from fastapi.security import APIKeyHeader
import os
import json
import time
import subprocess
import shutil
import digitalocean
from fastapi import FastAPI
from pydantic import BaseModel

from ..utils.base_server import BaseServer
from ..utils.error_handling import handle_exceptions, MCPError, AuthorizationError, ValidationError
from ..utils.security import ApiKey

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

# --- Pydantic Request Models ---

class OperationRequest(BaseModel):
    operation: str
    parameters: Dict[str, Any]

class ManageRequest(BaseModel):
    action: str
    resource_type: str
    resource_id: int

class MonitorRequest(BaseModel):
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None

class BackupRequest(BaseModel):
    resource_type: str
    resource_id: int
    backup_name: str

class RestoreRequest(BaseModel):
    backup_id: str
    resource_type: str
    resource_id: int

class ScaleRequest(BaseModel):
    resource_type: str
    resource_id: int
    scale_factor: float

# --- Server Class ---

class NeoDOServer(BaseServer):
    """Neo DO MCP Server implementation."""
    
    def __init__(self):
        """Initialize Neo DO MCP Server."""
        super().__init__("neodo_mcp")
        
        # Initialize DO client
        self._init_do_client()
        
        # Register routes - This is done by BaseServer.__init__
        # self.register_routes()
        
    def _init_do_client(self) -> None:
        """Initialize DigitalOcean client."""
        try:
            # Get DO token from config
            do_token = self.config.do_token
            if not do_token:
                raise MCPError("DO Token not configured (do_token field in config)")
                
            # Initialize manager
            self.do_manager = digitalocean.Manager(token=do_token)
            
            self.logger.info("DigitalOcean client initialized")
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize DigitalOcean client",
                error=str(e)
            )
            raise MCPError(f"Failed to initialize DO client: {e}")
        
    def register_routes(self) -> None:
        """Register API routes."""
        super().register_routes()
        
        @self.app.post("/api/v1/do/operations")
        @handle_exceptions()
        async def perform_operation(
            request_body: OperationRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Perform a DigitalOcean operation.
            
            Args:
                request_body: Operation request body
                api_key: Validated API key
                
            Returns:
                Operation result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "perform:operation"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Check if DO operations are enabled
            if not self.config.enable_do_operations:
                raise HTTPException(
                    status_code=503,
                    detail="DO operations are disabled"
                )
                
            # Handle operation
            with self.monitor.span_in_context(
                "do_operation",
                attributes={
                    "operation": request_body.operation,
                    "parameters": request_body.parameters
                }
            ):
                try:
                    # TODO: Implement DO operations
                    return {
                        "status": "success",
                        "operation": request_body.operation,
                        "parameters": request_body.parameters,
                        "result": {}
                    }
                    
                except Exception as e:
                    self.logger.error(
                        "DO operation failed",
                        extra={
                            "error": str(e),
                            "operation": request_body.operation,
                            "parameters": request_body.parameters
                        }
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.post("/api/v1/do/management")
        @handle_exceptions()
        async def manage_resources(
            request_body: ManageRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Manage DigitalOcean resources.
            
            Args:
                request_body: Manage request body
                api_key: Validated API key
                
            Returns:
                Management result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "manage:resources"):
                raise AuthorizationError(message="Insufficient permissions")
                
            # Check if DO management is enabled
            if not self.config.enable_do_management:
                raise MCPError(
                    status_code=503,
                    error_code="SERVICE_DISABLED",
                    message="DO management is disabled"
                )
                
            # Manage resources
            with self.monitor.span_in_context(
                "manage_resources",
                attributes={
                    "action": request_body.action,
                    "resource_type": request_body.resource_type,
                    "resource_id": str(request_body.resource_id)
                }
            ):
                try:
                    if not self.do_manager:
                        raise MCPError(status_code=503, error_code="DO_CLIENT_UNAVAILABLE", message="DigitalOcean client not initialized")

                    if request_body.resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(request_body.resource_id)
                        action = getattr(droplet, request_body.action, None)
                        if action and callable(action):
                            action()
                        else:
                            raise ValidationError(
                                message=f"Invalid action: {request_body.action}",
                                details={"action": request_body.action, "resource_type": "droplet"}
                            )
                    else:
                        raise ValidationError(
                            message=f"Unsupported resource type: {request_body.resource_type}",
                            details={"resource_type": request_body.resource_type}
                        )
                    
                    return {"status": "success", "message": f"Action '{request_body.action}' completed successfully."}
                    
                except digitalocean.Error as e:
                    self.logger.error(
                        "DigitalOcean API error during management",
                        extra={
                            "error": str(e),
                            "resource_type": request_body.resource_type,
                            "resource_id": str(request_body.resource_id),
                            "action": request_body.action
                        }
                    )
                    raise MCPError(message=str(e), status_code=500, error_code="DO_API_ERROR")
                except Exception as e:
                    self.logger.error(
                        "Resource management failed",
                        extra={
                            "error": str(e),
                            "action": request_body.action,
                            "resource_type": request_body.resource_type,
                            "resource_id": str(request_body.resource_id)
                        }
                    )
                    raise MCPError(message=str(e), status_code=500, error_code="DO_MANAGEMENT_FAILED")
                    
        @self.app.get("/api/v1/do/monitoring")
        @handle_exceptions()
        async def monitor_resources(
            resource_type: Optional[str] = None,
            resource_id: Optional[int] = None,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Monitor DigitalOcean resources.
            
            Args:
                resource_type: Type of resource to monitor
                resource_id: Specific resource ID to monitor
                api_key: Validated API key
                
            Returns:
                Monitoring results
            """
            # Check permissions
            if not self.security.check_permission(api_key, "monitor:resources"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Check if DO monitoring is enabled
            if not self.config.enable_do_monitoring:
                raise HTTPException(
                    status_code=503,
                    detail="DO monitoring is disabled"
                )
                
            # Monitor resources
            with self.monitor.span_in_context(
                "monitor_resources",
                attributes={
                    "resource_type": resource_type,
                    "resource_id": str(resource_id) if resource_id is not None else None
                }
            ):
                try:
                    # TODO: Implement resource monitoring
                    return {
                        "status": "success",
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "metrics": {}
                    }
                    
                except Exception as e:
                    self.logger.error(
                        "Resource monitoring failed",
                        extra={
                            "error": str(e),
                            "resource_type": resource_type,
                            "resource_id": str(resource_id) if resource_id is not None else None
                        }
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.post("/api/v1/do/backup")
        @handle_exceptions()
        async def backup_resources(
            request_body: BackupRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Backup DigitalOcean resources.
            
            Args:
                request_body: Backup request body
                api_key: Validated API key
                
            Returns:
                Backup result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "backup:resources"):
                raise AuthorizationError(message="Insufficient permissions")
                
            # Check if DO backup is enabled
            if not self.config.enable_do_backup:
                raise MCPError(
                    status_code=503,
                    error_code="SERVICE_DISABLED",
                    message="DO backup is disabled"
                )
                
            # Backup resources
            with self.monitor.span_in_context(
                "backup_resources",
                attributes={
                    "resource_type": request_body.resource_type,
                    "resource_id": str(request_body.resource_id),
                    "backup_name": request_body.backup_name
                }
            ):
                try:
                    if not self.do_manager:
                        raise MCPError(status_code=503, error_code="DO_CLIENT_UNAVAILABLE", message="DigitalOcean client not initialized")

                    if request_body.resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(request_body.resource_id)
                        snapshot = droplet.take_snapshot(name=request_body.backup_name, power_off=False)
                        
                        return {
                            "status": "success",
                            "message": "Snapshot created successfully",
                            "snapshot_id": snapshot.id,
                            "resource_type": request_body.resource_type,
                            "resource_id": str(request_body.resource_id)
                        }
                    else:
                        raise ValidationError(
                            message=f"Unsupported resource type for backup: {request_body.resource_type}",
                            details={"resource_type": request_body.resource_type}
                        )
                    
                except digitalocean.Error as e:
                    self.logger.error(
                        "DigitalOcean API error during backup",
                        extra={
                            "error": str(e),
                            "resource_type": request_body.resource_type,
                            "resource_id": str(request_body.resource_id),
                            "backup_name": request_body.backup_name
                        }
                    )
                    raise MCPError(message=str(e), status_code=500, error_code="DO_API_ERROR")
                except Exception as e:
                    self.logger.error(
                        "Resource backup failed",
                        extra={
                            "error": str(e),
                            "resource_type": request_body.resource_type,
                            "resource_id": str(request_body.resource_id),
                            "backup_name": request_body.backup_name
                        }
                    )
                    raise MCPError(message=str(e), status_code=500, error_code="DO_BACKUP_FAILED")
                    
        @self.app.post("/api/v1/do/restore")
        @handle_exceptions()
        async def restore_resources(
            request_body: RestoreRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Restore DigitalOcean resources from backup.
            
            Args:
                request_body: Restore request body
                api_key: Validated API key
                
            Returns:
                Restore result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "restore:resources"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Check if DO restore is enabled
            if not self.config.enable_do_restore:
                raise HTTPException(
                    status_code=503,
                    detail="DO restore is disabled"
                )
                
            # Restore resources
            with self.monitor.span_in_context(
                "restore_resources",
                attributes={
                    "backup_id": request_body.backup_id,
                    "resource_type": request_body.resource_type,
                    "resource_id": str(request_body.resource_id)
                }
            ):
                try:
                    if request_body.resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(request_body.resource_id)
                        snapshot = self.do_manager.get_snapshot(request_body.backup_id)
                        
                        # Restore from snapshot
                        droplet.restore(snapshot.id)
                        
                        return {
                            "status": "success",
                            "backup_id": request_body.backup_id,
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported resource type: {request_body.resource_type}"
                        )
                    
                except Exception as e:
                    self.logger.error(
                        "Resource restore failed",
                        extra={
                            "error": str(e),
                            "backup_id": request_body.backup_id,
                            "resource_type": request_body.resource_type,
                            "resource_id": str(request_body.resource_id)
                        }
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.post("/api/v1/do/scale")
        @handle_exceptions()
        async def scale_resources(
            request_body: ScaleRequest,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Scale DigitalOcean resources.
            
            Args:
                request_body: Scale request body
                api_key: Validated API key
                
            Returns:
                Scaling result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "scale:resources"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Check if DO scaling is enabled
            if not self.config.enable_do_scaling:
                raise HTTPException(
                    status_code=503,
                    detail="DO scaling is disabled"
                )
                
            # Scale resources
            with self.monitor.span_in_context(
                "scale_resources",
                attributes={
                    "resource_type": request_body.resource_type,
                    "resource_id": str(request_body.resource_id),
                    "scale_factor": request_body.scale_factor
                }
            ):
                try:
                    if request_body.resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(request_body.resource_id)
                        
                        # Get current size
                        current_size = droplet.size_slug
                        
                        # Determine new size based on scale factor
                        sizes = self.do_manager.get_all_sizes()
                        size_slugs = [size.slug for size in sizes]
                        current_index = size_slugs.index(current_size)
                        new_index = min(
                            len(size_slugs) - 1,
                            max(0, int(current_index * request_body.scale_factor))
                        )
                        new_size = size_slugs[new_index]
                        
                        # Resize droplet
                        droplet.resize(new_size)
                        
                        return {
                            "status": "success",
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id,
                            "scale_factor": request_body.scale_factor,
                            "old_size": current_size,
                            "new_size": new_size
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported resource type: {request_body.resource_type}"
                        )
                    
                except Exception as e:
                    self.logger.error(
                        "Resource scaling failed",
                        extra={
                            "error": str(e),
                            "resource_type": request_body.resource_type,
                            "resource_id": str(request_body.resource_id),
                            "scale_factor": request_body.scale_factor
                        }
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )

# App Factory pattern
def create_app(config=None, env=None) -> FastAPI:
    """Factory function to create the NeoDOServer FastAPI app.
    
    Args:
        config: Optional server configuration
        env: Optional environment name
        
    Returns:
        FastAPI application instance
    """
    server = NeoDOServer()
    if config:
        server.config = config
    if env:
        server.env = env
    # Routes are registered in BaseServer init
    return server.app

# Remove direct instantiation
# server = NeoDOServer()
# app = server.get_app() 