"""
Neo Operations MCP Server - Provides operations-related tools.
"""

from typing import Dict, Any, Optional, List
from fastapi import Depends, Request, FastAPI
from pydantic import BaseModel
import os

# Import BaseServer and utilities
from server.utils.base_server import BaseServer
from server.utils.error_handling import handle_exceptions, MCPError
# Security handled by BaseServer

# --- Pydantic Models (if any specific to NeoOps) ---
class ProcessInfo(BaseModel):
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float

class ListProcessesResponse(BaseModel):
    processes: List[ProcessInfo]

class ResourceUsage(BaseModel):
    cpu_total_percent: float
    memory_total_percent: float
    disk_usage_percent: Dict[str, float] # Mount point -> usage %

# --- NeoOps Server Class (Refactored) ---

class NeoOpsServer(BaseServer):
    """Neo Operations Server inheriting from BaseServer."""

    def __init__(self):
        """Initialize Neo Operations Server."""
        super().__init__(app_name="neoo_server") # Check app name
        # Initialize NeoOps specific components if any (e.g., process monitor)
        # self.process_manager = ProcessManager()
        self.logger.info("Neo Operations Server Initialized")

    def register_routes(self) -> None:
        """Register NeoOps specific routes after base routes."""
        super().register_routes()

        # Example NeoOps routes (replace/add actual ones)
        @self.app.get("/api/v1/processes", response_model=ListProcessesResponse, tags=["NeoOps"])
        @handle_exceptions()
        async def list_processes(
            request: Request,
            # TODO: Add security Depends(self.get_api_key)
        ) -> ListProcessesResponse:
            """List running processes."""
            logger = request.state.log_manager
            logger.info("Received request to list processes")
            # Placeholder - replace with actual process listing logic
            processes = [
                ProcessInfo(pid=123, name="python", cpu_percent=10.5, memory_percent=5.2),
                ProcessInfo(pid=456, name="node", cpu_percent=5.1, memory_percent=8.9),
            ]
            logger.info(f"Returning info for {len(processes)} processes")
            return ListProcessesResponse(processes=processes)

        @self.app.get("/api/v1/resources", response_model=ResourceUsage, tags=["NeoOps"])
        @handle_exceptions()
        async def get_resource_usage(
            request: Request,
            # TODO: Add security Depends(self.get_api_key)
        ) -> ResourceUsage:
            """Get system resource usage."""
            logger = request.state.log_manager
            logger.info("Received request for resource usage")
            # Placeholder - replace with actual resource monitoring logic (e.g., psutil)
            usage = ResourceUsage(
                cpu_total_percent=35.2,
                memory_total_percent=60.1,
                disk_usage_percent={"/": 75.5, "/data": 40.0}
            )
            logger.info("Returning resource usage")
            return usage

# App Factory pattern
def create_app() -> FastAPI:
    server = NeoOpsServer()
    return server.app 