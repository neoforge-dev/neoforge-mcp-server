import functools
import inspect
import sys
import threading
from typing import Any, Callable, Dict, Optional

from debugger import MCPDebugger
from opentelemetry import trace
import time

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

def trace_tool(func):
    """Decorator to add tracing to MCP tools"""
    # Assumes 'tracer' is available globally or configured appropriately
    # In a real app, tracer might be injected or accessed via app state
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check if tracer exists and is configured
        try:
            current_tracer = trace.get_tracer(__name__) # Or however tracer is obtained
        except Exception:
            current_tracer = None # No tracer available

        if not current_tracer or isinstance(current_tracer, trace.NoOpTracer):
             # If no real tracer, just call the function
            return func(*args, **kwargs)
            
        with current_tracer.start_as_current_span(
            name=f"mcp.tool.{func.__name__}",
            attributes={
                "mcp.tool.name": func.__name__,
                "mcp.tool.args": str(args), # Be careful with large args
                "mcp.tool.kwargs": str(kwargs) # Be careful with large kwargs
            }
        ) as span:
            try:
                result = func(*args, **kwargs)
                if isinstance(result, dict):
                    span.set_attribute("mcp.tool.status", result.get("status", "unknown"))
                    if "error" in result:
                        span.set_attribute("mcp.tool.error", result["error"])
                return result
            except Exception as e:
                span.set_attribute("mcp.tool.error", str(e))
                span.record_exception(e)
                raise
    return wrapper

def metrics_tool(func):
    """Decorator to add metrics to MCP tools"""
    # Assumes metrics objects (tool_calls, tool_duration, tool_errors) 
    # are available globally or configured appropriately
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Get meter/instruments - this needs a proper mechanism
        # Placeholder: Accessing them globally (Bad practice! Needs DI)
        # These globals would need to be defined *somewhere* accessible
        # E.g., in a central monitoring setup module
        try:
            from metrics import tool_calls, tool_duration, tool_errors # Example global import
        except ImportError:
             # Mock or NoOp instruments if metrics not set up
            class MockInstrument: 
                def add(self, *a, **kw): pass
                def record(self, *a, **kw): pass
            tool_calls = tool_duration = tool_errors = MockInstrument()
            
        start_time = time.time()
        tool_calls.add(1, {"tool": func.__name__})

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            tool_duration.record(duration, {"tool": func.__name__})
            return result
        except Exception as e:
            tool_errors.add(1, {"tool": func.__name__, "error": str(e)})
            raise
    return wrapper 