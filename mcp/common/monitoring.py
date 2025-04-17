"""
Mock monitoring module to satisfy imports.
"""

from typing import Callable, Any, Optional
from functools import wraps


class Monitor:
    """Mock Monitor class that provides a no-op implementation."""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
    
    def record_event(self, event_type: str, details: Any = None) -> None:
        """Record a monitoring event (no-op)."""
        pass
    
    def start_span(self, name: str) -> Any:
        """Start a monitoring span (no-op)."""
        class MockSpan:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        return MockSpan()
    
    @staticmethod
    def monitored_call(func: Callable) -> Callable:
        """Decorator to monitor function calls (no-op)."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper 