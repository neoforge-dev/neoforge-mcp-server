"""
Mock container module to satisfy imports.
"""

from typing import Callable, Dict, Any


class Container:
    """A simplified mock container for dependency injection."""
    
    def __init__(self):
        self._providers = {}
    
    def provider(self, func: Callable) -> Callable:
        """Register a provider function."""
        self._providers[func.__name__] = func
        return func
    
    def provide(self, name: str) -> Any:
        """Provide an instance for a named dependency."""
        if name in self._providers:
            return self._providers[name]()
        raise KeyError(f"Provider not found: {name}")
    
    def __call__(self, *args, **kwargs):
        """Make the container callable for compatibility."""
        return self 