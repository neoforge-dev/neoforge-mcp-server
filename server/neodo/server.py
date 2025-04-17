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
        """Initialize Neo DO MCP Server (Managers only)."""
        super().__init__("neodo_mcp")
        self._init_do_client()
        
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
        
    def register_routes(self, app: FastAPI) -> None:
        """Register API routes on the provided app instance."""
        # Register base routes first
        super().register_routes(app)
        
        # Register DO specific routes using the passed app instance
        # Ensure the prefix is handled correctly - maybe BaseServer needs api_prefix?
        # Or define prefix here within NeoDOServer
        prefix = self.config.api_prefix # Get prefix from config

        @app.post(f"{prefix}/operations") # Use f-string for prefix
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
                    
        @app.post(f"{prefix}/management") # Use f-string for prefix
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
                                details={"resource_type": request_body.resource_type, "resource_id": request_body.resource_id}
                            )
                    else:
                        raise ValidationError(f"Unsupported resource type: {request_body.resource_type}")

                    self.logger.info(
                        "Managed resource successfully",
                        extra={
                            "action": request_body.action,
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id
                        }
                    )
                    return {"status": "success"}

                except Exception as e:
                    self.logger.error(
                        "Failed to manage resource",
                        extra={
                            "error": str(e),
                            "action": request_body.action,
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id
                        }
                    )
                    # Re-raise specific handled exceptions or a generic one
                    if isinstance(e, (MCPError, ValidationError, digitalocean.Error)):
                        raise
                    raise MCPError(f"Failed to manage resource: {e}")
                    
        @app.get(f"{prefix}/monitoring") # Use f-string for prefix
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
                raise AuthorizationError(message="Insufficient permissions")
                
            # Check if DO monitoring is enabled
            if not self.config.enable_do_monitoring:
                raise MCPError(
                    status_code=503,
                    error_code="SERVICE_DISABLED",
                    message="DO monitoring is disabled"
                )
                
            # Monitor resources
            with self.monitor.span_in_context(
                "monitor_resources",
                attributes={
                    "resource_type": resource_type,
                    "resource_id": str(resource_id) if resource_id else None
                }
            ):
                try:
                    # TODO: Implement actual DO monitoring logic
                    metrics = {"cpu": "50%", "memory": "60%"}
                    
                    self.logger.info(
                        "Retrieved monitoring data",
                        extra={
                            "resource_type": resource_type,
                            "resource_id": resource_id
                        }
                    )
                    return {"status": "success", "metrics": metrics}
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to monitor resources",
                        extra={
                            "error": str(e),
                            "resource_type": resource_type,
                            "resource_id": resource_id
                        }
                    )
                    raise MCPError(f"Failed to monitor resources: {e}")
                    
        @app.post(f"{prefix}/backup") # Use f-string for prefix
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

                    snapshot = None
                    if request_body.resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(request_body.resource_id)
                        # TODO: Consider power_off=True based on config or request?
                        snapshot = droplet.take_snapshot(name=request_body.backup_name, power_off=False)
                        # Wait for snapshot to complete (optional, can be long)
                        # snapshot.load()
                        # while snapshot.status != 'completed':
                        #     time.sleep(10)
                        #     snapshot.load()
                    else:
                        raise ValidationError(f"Backup not supported for resource type: {request_body.resource_type}")

                    self.logger.info(
                        "Resource backup initiated successfully",
                        extra={
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id,
                            "backup_name": request_body.backup_name,
                            "snapshot_id": snapshot.id if snapshot else None
                        }
                    )
                    return {
                        "status": "success",
                        "message": "Snapshot created successfully",
                        "snapshot_id": snapshot.id if snapshot else None
                    }

                except Exception as e:
                    self.logger.error(
                        "Failed to backup resource",
                        extra={
                            "error": str(e),
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id,
                            "backup_name": request_body.backup_name
                        }
                    )
                    # Re-raise specific handled exceptions or a generic one
                    if isinstance(e, (MCPError, ValidationError, digitalocean.Error)):
                        raise
                    raise MCPError(f"Failed to backup resource: {e}")
                    
        @app.post(f"{prefix}/restore") # Use f-string for prefix
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
                raise AuthorizationError(message="Insufficient permissions")
                
            # Check if DO restore is enabled
            if not self.config.enable_do_restore:
                raise MCPError(
                    status_code=503,
                    error_code="SERVICE_DISABLED",
                    message="DO restore is disabled"
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
                    # TODO: Implement actual DO restore logic
                    # e.g., find snapshot, call restore action on droplet
                    self.logger.info(
                        "Resource restore initiated successfully",
                        extra={
                            "backup_id": request_body.backup_id,
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id
                        }
                    )
                    return {"status": "success", "message": "Restore initiated"}

                except Exception as e:
                    self.logger.error(
                        "Failed to restore resource",
                        extra={
                            "error": str(e),
                            "backup_id": request_body.backup_id,
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id
                        }
                    )
                    raise MCPError(f"Failed to restore resource: {e}")
                    
        @app.post(f"{prefix}/scale") # Use f-string for prefix
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
                raise AuthorizationError(message="Insufficient permissions")
                
            # Check if DO scaling is enabled
            if not self.config.enable_do_scaling:
                raise MCPError(
                    status_code=503,
                    error_code="SERVICE_DISABLED",
                    message="DO scaling is disabled"
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
                    # TODO: Implement actual DO scaling logic
                    # e.g., resize droplet
                    self.logger.info(
                        "Resource scaling initiated successfully",
                        extra={
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id,
                            "scale_factor": request_body.scale_factor
                        }
                    )
                    return {"status": "success", "message": "Scaling initiated"}

                except Exception as e:
                    self.logger.error(
                        "Failed to scale resource",
                        extra={
                            "error": str(e),
                            "resource_type": request_body.resource_type,
                            "resource_id": request_body.resource_id,
                            "scale_factor": request_body.scale_factor
                        }
                    )
                    raise MCPError(f"Failed to scale resource: {e}")

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