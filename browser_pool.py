#!/usr/bin/env python3
"""
Browser Pool Module for MCP Browser

This module provides a resource pool for efficiently managing browser instances,
allowing for reuse of browser contexts and proper cleanup of resources.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("browser_pool")


@dataclass
class BrowserInstance:
    """Class representing a browser instance with its associated contexts."""
    instance_id: str
    contexts: Dict[str, dict] = field(default_factory=dict)
    in_use: bool = False
    last_used: float = field(default_factory=lambda: asyncio.get_event_loop().time())

    def add_context(self, context_id: str, context_data: dict) -> None:
        """Add a browser context to this instance."""
        self.contexts[context_id] = context_data
        self.last_used = asyncio.get_event_loop().time()
        logger.info(f"Added context {context_id} to browser instance {self.instance_id}")

    def remove_context(self, context_id: str) -> None:
        """Remove a browser context from this instance."""
        if context_id in self.contexts:
            del self.contexts[context_id]
            logger.info(f"Removed context {context_id} from browser instance {self.instance_id}")
        else:
            logger.warning(f"Attempted to remove non-existent context {context_id}")

    def mark_as_used(self) -> None:
        """Mark this browser instance as in use."""
        self.in_use = True
        self.last_used = asyncio.get_event_loop().time()

    def mark_as_free(self) -> None:
        """Mark this browser instance as free for reuse."""
        self.in_use = False
        self.last_used = asyncio.get_event_loop().time()


class BrowserPool:
    """
    A resource pool for managing browser instances efficiently.
    
    This class manages browser instances to minimize resource usage
    while providing fast access to browser contexts. It handles
    creation, allocation, and cleanup of browser resources.
    """
    
    def __init__(self, max_instances: int = 5, idle_timeout: float = 300):
        """
        Initialize the browser pool.
        
        Args:
            max_instances: Maximum number of concurrent browser instances
            idle_timeout: Time in seconds before cleaning up idle instances
        """
        self.instances: Dict[str, BrowserInstance] = {}
        self.max_instances = max_instances
        self.idle_timeout = idle_timeout
        self.cleanup_task = None
        self.lock = asyncio.Lock()
        logger.info(f"Initialized BrowserPool with max_instances={max_instances}, idle_timeout={idle_timeout}")

    async def start(self) -> None:
        """Start the browser pool and its maintenance tasks."""
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Started BrowserPool cleanup task")

    async def stop(self) -> None:
        """Stop the browser pool and clean up all instances."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
        
        # Clean up all instances
        async with self.lock:
            for instance_id in list(self.instances.keys()):
                await self._close_browser_instance(instance_id)
        
        logger.info("BrowserPool stopped and all instances cleaned up")

    async def get_browser_instance(self) -> str:
        """
        Get an available browser instance or create a new one.
        
        Returns:
            A unique identifier for the browser instance
        """
        async with self.lock:
            # Look for an available instance
            for instance_id, instance in self.instances.items():
                if not instance.in_use:
                    instance.mark_as_used()
                    logger.info(f"Reusing existing browser instance {instance_id}")
                    return instance_id
            
            # Create a new instance if below max
            if len(self.instances) < self.max_instances:
                instance_id = str(uuid.uuid4())
                self.instances[instance_id] = BrowserInstance(instance_id=instance_id, in_use=True)
                logger.info(f"Created new browser instance {instance_id}")
                return instance_id
            
            # No available instances
            logger.warning("No available browser instances and at capacity")
            raise RuntimeError("No available browser instances and at capacity")
    
    async def release_browser_instance(self, instance_id: str) -> None:
        """
        Release a browser instance back to the pool.
        
        Args:
            instance_id: The ID of the browser instance to release
        """
        async with self.lock:
            if instance_id in self.instances:
                self.instances[instance_id].mark_as_free()
                logger.info(f"Released browser instance {instance_id} back to pool")
            else:
                logger.warning(f"Attempted to release non-existent browser instance {instance_id}")
    
    async def create_browser_context(self, instance_id: str, context_data: dict = None) -> str:
        """
        Create a new browser context in the specified instance.
        
        Args:
            instance_id: The ID of the browser instance
            context_data: Optional data to associate with this context
            
        Returns:
            A unique identifier for the browser context
        """
        if context_data is None:
            context_data = {}
            
        async with self.lock:
            if instance_id not in self.instances:
                logger.error(f"Attempted to create context in non-existent browser instance {instance_id}")
                raise ValueError(f"Browser instance {instance_id} does not exist")
            
            context_id = str(uuid.uuid4())
            self.instances[instance_id].add_context(context_id, context_data)
            return context_id
    
    async def close_browser_context(self, instance_id: str, context_id: str) -> None:
        """
        Close a browser context.
        
        Args:
            instance_id: The ID of the browser instance
            context_id: The ID of the browser context to close
        """
        async with self.lock:
            if instance_id not in self.instances:
                logger.warning(f"Attempted to close context in non-existent browser instance {instance_id}")
                return
            
            self.instances[instance_id].remove_context(context_id)
    
    async def get_context_data(self, instance_id: str, context_id: str) -> Optional[dict]:
        """
        Get the data associated with a browser context.
        
        Args:
            instance_id: The ID of the browser instance
            context_id: The ID of the browser context
            
        Returns:
            The context data or None if not found
        """
        async with self.lock:
            if instance_id not in self.instances:
                return None
            
            instance = self.instances[instance_id]
            return instance.contexts.get(context_id)
    
    async def get_all_instances(self) -> List[Dict]:
        """
        Get information about all browser instances.
        
        Returns:
            A list of dictionaries containing instance information
        """
        async with self.lock:
            result = []
            for instance_id, instance in self.instances.items():
                result.append({
                    "instance_id": instance_id,
                    "in_use": instance.in_use,
                    "last_used": instance.last_used,
                    "context_count": len(instance.contexts),
                })
            return result
    
    async def _cleanup_loop(self) -> None:
        """Background task to clean up idle browser instances."""
        try:
            while True:
                await asyncio.sleep(60)  # Check every minute
                await self._cleanup_idle_instances()
        except asyncio.CancelledError:
            logger.info("Browser pool cleanup task cancelled")
            raise
    
    async def _cleanup_idle_instances(self) -> None:
        """Clean up browser instances that have been idle for too long."""
        now = asyncio.get_event_loop().time()
        
        async with self.lock:
            for instance_id, instance in list(self.instances.items()):
                # Skip instances that are in use
                if instance.in_use:
                    continue
                
                # Close instances that have been idle for too long
                if now - instance.last_used > self.idle_timeout:
                    logger.info(f"Cleaning up idle browser instance {instance_id}")
                    await self._close_browser_instance(instance_id)
    
    async def _close_browser_instance(self, instance_id: str) -> None:
        """Close a browser instance and clean up its resources."""
        if instance_id in self.instances:
            logger.info(f"Closing browser instance {instance_id}")
            # In a real implementation, this would include browser-specific cleanup
            # such as closing the actual browser process
            del self.instances[instance_id] 