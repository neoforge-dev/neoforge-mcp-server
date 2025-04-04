"""
Neo DO MCP Server - Provides DigitalOcean operations and management.
"""

from typing import Any, Dict, Optional, List
from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
import os
import json
import time
import subprocess
import shutil
import digitalocean

from ..utils.base_server import BaseServer
from ..utils.error_handling import handle_exceptions, MCPError
from ..utils.security import ApiKey

# API key header
api_key_header = APIKeyHeader(name="X-API-Key")

class NeoDOServer(BaseServer):
    """Neo DO MCP Server implementation."""
    
    def __init__(self):
        """Initialize Neo DO MCP Server."""
        super().__init__("neodo_mcp")
        
        # Initialize DO client
        self._init_do_client()
        
        # Register routes
        self.register_routes()
        
    def _init_do_client(self) -> None:
        """Initialize DigitalOcean client."""
        try:
            # Get DO token from environment
            do_token = os.getenv("DO_TOKEN")
            if not do_token:
                raise MCPError("DO_TOKEN environment variable not set")
                
            # Initialize manager
            self.do_manager = digitalocean.Manager(token=do_token)
            
            self.logger.info("DigitalOcean client initialized")
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize DigitalOcean client",
                error=str(e)
            )
            raise MCPError(f"Failed to initialize DO client: {e}")
        
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
        
        @self.app.post("/api/v1/do/operations")
        @handle_exceptions()
        async def perform_operation(
            operation: str,
            parameters: Dict[str, Any],
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Perform a DigitalOcean operation.
            
            Args:
                operation: Operation to perform
                parameters: Operation parameters
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
                    "operation": operation,
                    "parameters": parameters
                }
            ):
                try:
                    # TODO: Implement DO operations
                    return {
                        "status": "success",
                        "operation": operation,
                        "parameters": parameters,
                        "result": {}
                    }
                    
                except Exception as e:
                    self.logger.error(
                        "DO operation failed",
                        error=str(e),
                        operation=operation,
                        parameters=parameters
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.post("/api/v1/do/management")
        @handle_exceptions()
        async def manage_resources(
            action: str,
            resource_type: str,
            resource_id: str,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Manage DigitalOcean resources.
            
            Args:
                action: Action to perform
                resource_type: Type of resource
                resource_id: Resource ID
                api_key: Validated API key
                
            Returns:
                Management result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "manage:resources"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Check if DO management is enabled
            if not self.config.enable_do_management:
                raise HTTPException(
                    status_code=503,
                    detail="DO management is disabled"
                )
                
            # Manage resources
            with self.monitor.span_in_context(
                "manage_resources",
                attributes={
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id
                }
            ):
                try:
                    if resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(resource_id)
                        
                        if action == "power_on":
                            droplet.power_on()
                        elif action == "power_off":
                            droplet.power_off()
                        elif action == "reboot":
                            droplet.reboot()
                        elif action == "shutdown":
                            droplet.shutdown()
                        else:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Unsupported action for droplets: {action}"
                            )
                            
                        return {
                            "status": "success",
                            "action": action,
                            "resource_type": resource_type,
                            "resource_id": resource_id
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported resource type: {resource_type}"
                        )
                    
                except Exception as e:
                    self.logger.error(
                        "Resource management failed",
                        error=str(e),
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.get("/api/v1/do/monitoring")
        @handle_exceptions()
        async def monitor_resources(
            resource_type: Optional[str] = None,
            resource_id: Optional[str] = None,
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
                    "resource_id": resource_id
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
                        error=str(e),
                        resource_type=resource_type,
                        resource_id=resource_id
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.post("/api/v1/do/backup")
        @handle_exceptions()
        async def backup_resources(
            resource_type: str,
            resource_id: str,
            backup_name: str,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Backup DigitalOcean resources.
            
            Args:
                resource_type: Type of resource to backup
                resource_id: Resource ID to backup
                backup_name: Name for the backup
                api_key: Validated API key
                
            Returns:
                Backup result
            """
            # Check permissions
            if not self.security.check_permission(api_key, "backup:resources"):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions"
                )
                
            # Check if DO backup is enabled
            if not self.config.enable_do_backup:
                raise HTTPException(
                    status_code=503,
                    detail="DO backup is disabled"
                )
                
            # Backup resources
            with self.monitor.span_in_context(
                "backup_resources",
                attributes={
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "backup_name": backup_name
                }
            ):
                try:
                    if resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(resource_id)
                        snapshot = droplet.take_snapshot(backup_name)
                        
                        return {
                            "status": "success",
                            "resource_type": resource_type,
                            "resource_id": resource_id,
                            "backup_name": backup_name,
                            "snapshot_id": snapshot.id
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported resource type: {resource_type}"
                        )
                    
                except Exception as e:
                    self.logger.error(
                        "Resource backup failed",
                        error=str(e),
                        resource_type=resource_type,
                        resource_id=resource_id,
                        backup_name=backup_name
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.post("/api/v1/do/restore")
        @handle_exceptions()
        async def restore_resources(
            backup_id: str,
            resource_type: str,
            resource_id: str,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Restore DigitalOcean resources from backup.
            
            Args:
                backup_id: ID of backup to restore
                resource_type: Type of resource to restore
                resource_id: Resource ID to restore to
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
                    "backup_id": backup_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id
                }
            ):
                try:
                    if resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(resource_id)
                        snapshot = self.do_manager.get_snapshot(backup_id)
                        
                        # Restore from snapshot
                        droplet.restore(snapshot.id)
                        
                        return {
                            "status": "success",
                            "backup_id": backup_id,
                            "resource_type": resource_type,
                            "resource_id": resource_id
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported resource type: {resource_type}"
                        )
                    
                except Exception as e:
                    self.logger.error(
                        "Resource restore failed",
                        error=str(e),
                        backup_id=backup_id,
                        resource_type=resource_type,
                        resource_id=resource_id
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )
                    
        @self.app.post("/api/v1/do/scale")
        @handle_exceptions()
        async def scale_resources(
            resource_type: str,
            resource_id: str,
            scale_factor: float,
            api_key: ApiKey = Depends(self.get_api_key)
        ) -> Dict[str, Any]:
            """Scale DigitalOcean resources.
            
            Args:
                resource_type: Type of resource to scale
                resource_id: Resource ID to scale
                scale_factor: Scaling factor
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
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "scale_factor": scale_factor
                }
            ):
                try:
                    if resource_type == "droplet":
                        droplet = self.do_manager.get_droplet(resource_id)
                        
                        # Get current size
                        current_size = droplet.size_slug
                        
                        # Determine new size based on scale factor
                        sizes = self.do_manager.get_all_sizes()
                        size_slugs = [size.slug for size in sizes]
                        current_index = size_slugs.index(current_size)
                        new_index = min(
                            len(size_slugs) - 1,
                            max(0, int(current_index * scale_factor))
                        )
                        new_size = size_slugs[new_index]
                        
                        # Resize droplet
                        droplet.resize(new_size)
                        
                        return {
                            "status": "success",
                            "resource_type": resource_type,
                            "resource_id": resource_id,
                            "scale_factor": scale_factor,
                            "old_size": current_size,
                            "new_size": new_size
                        }
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Unsupported resource type: {resource_type}"
                        )
                    
                except Exception as e:
                    self.logger.error(
                        "Resource scaling failed",
                        error=str(e),
                        resource_type=resource_type,
                        resource_id=resource_id,
                        scale_factor=scale_factor
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=str(e)
                    )

# Create server instance
server = NeoDOServer()
app = server.get_app() 