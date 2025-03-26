import functools
import inspect
import sys
import threading
from typing import Any, Callable, Dict, Optional

from debugger import MCPDebugger

_debugger: Optional[MCPDebugger] = None
_debug_lock = threading.Lock()

def get_debugger() -> Optional[MCPDebugger]:
    """Get the global debugger instance"""
    return _debugger

def set_debugger(debugger: MCPDebugger):
    """Set the global debugger instance"""
    global _debugger
    with _debug_lock:
        _debugger = debugger

def debuggable(tool_name: str, description: str = ""):
    """Decorator to make a tool debuggable
    
    Args:
        tool_name: Name of the tool
        description: Optional description of the tool
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            debugger = get_debugger()
            if debugger and '--debug' in sys.argv:
                # Register tool if not already registered
                if tool_name not in debugger.tool_registry:
                    debugger.tool_registry[tool_name] = {
                        'function': func,
                        'description': description or func.__doc__
                    }
                # Start debugging session
                debugger.debug_tool(tool_name, *args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator 