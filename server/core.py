from mcp.server.fastmcp import FastMCP
import os
import platform
import subprocess
import shlex
import time
import signal
import re
import glob
import stat
import shutil
import threading
import queue
import json
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import socket
import math
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from functools import wraps
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
import cProfile
import pstats
import io
import tempfile
from debugger import create_debugger
from decorators import set_debugger
import sys
import ast
import psutil
from opentelemetry.sdk.metrics._internal.measurement import Measurement
import asyncio
import metrics
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
# import yaml

# Initialize the MCP server
mcp = FastMCP("Terminal Command Runner MCP", port=7443, log_level="DEBUG")

# Create FastAPI app
app = FastAPI()

# For testing purposes, we'll use FastAPI's test client directly
# The app will be mounted to FastMCP in production
test_client = None
if "pytest" in sys.modules:
    from fastapi.testclient import TestClient
    test_client = TestClient(app)
else:
    # Mount the FastAPI app to the MCP server
    mcp.mount_app(app)

@app.get("/sse")
async def sse_endpoint(request: Request):
    """Server-Sent Events endpoint for real-time updates."""
    async def event_generator():
        try:
            # Send exactly one event for testing
            event = {
                "event": "update",
                "data": {
                    "timestamp": time.time(),
                    "status": "ok"
                }
            }
            yield f"data: {json.dumps(event)}\n\n"
            
        except Exception as e:
            print(f"SSE error: {e}")
            
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Global variables for process management
session_lock = threading.Lock()
active_sessions = {}
output_queues = {}

# Global variables for debug state management
debug_sessions = {}
debug_breakpoints = {}

# Initialize tracer
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: "mcp-server",
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
})

def get_memory_usage(options):
    """Get memory usage of the MCP server."""
    try:
        memory_info = psutil.Process().memory_info()
        return [Measurement(
            value=memory_info.rss,
            attributes={"unit": "bytes"},
            time_unix_nano=int(time.time_ns()),
            instrument=memory_usage,
            context=None
        )]
    except Exception as e:
        print(f"Error getting memory usage: {e}")
        return [Measurement(
            value=0,
            attributes={"unit": "bytes", "error": str(e)},
            time_unix_nano=int(time.time_ns()),
            instrument=memory_usage,
            context=None
        )]

# Only enable tracing and metrics if not in test mode
is_test_mode = "pytest" in sys.modules
enable_telemetry = os.environ.get("ENABLE_TELEMETRY", "0") == "1"

if not is_test_mode and enable_telemetry:
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)

    # Configure exporter
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    # Get metrics from metrics module
    meter = metrics.get_meter()

    # Create metrics
    tool_duration = meter.create_histogram(
        name="mcp.tool.duration",
        description="Duration of MCP tool execution",
        unit="s"
    )

    tool_calls = meter.create_counter(
        name="mcp.tool.calls",
        description="Number of MCP tool calls",
        unit="1"
    )

    tool_errors = meter.create_counter(
        name="mcp.tool.errors",
        description="Number of MCP tool errors",
        unit="1"
    )

    # Create a counter for active sessions
    active_sessions_counter = meter.create_up_down_counter(
        name="mcp.sessions.active",
        description="Number of active MCP sessions",
        unit="1"
    )

    memory_usage = meter.create_observable_gauge(
        name="mcp.system.memory_usage",
        description="Memory usage of the MCP server",
        unit="bytes",
        callbacks=[get_memory_usage]
    )
else:
    # Mock objects for test mode or when telemetry is disabled
    class MockTracer:
        def start_as_current_span(self, *args, **kwargs):
            class MockSpan:
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def set_attribute(self, *args): pass
                def record_exception(self, *args): pass
            return MockSpan()
    
    tracer = MockTracer()
    
    class MockMeter:
        def create_histogram(self, *args, **kwargs): return self
        def create_counter(self, *args, **kwargs): return self
        def create_up_down_counter(self, *args, **kwargs): return self
        def create_observable_gauge(self, *args, **kwargs): return self
        def add(self, *args, **kwargs): pass
        def record(self, *args, **kwargs): pass
    
    meter = MockMeter()
    tool_duration = meter
    tool_calls = meter
    tool_errors = meter
    active_sessions_counter = meter
    memory_usage = meter

def update_active_sessions_metric():
    """Update the active sessions metric."""
    with session_lock:
        active_sessions_counter.add(len(active_sessions))

def trace_tool(func):
    """Decorator to add tracing to MCP tools"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(
            name=f"mcp.tool.{func.__name__}",
            attributes={
                "mcp.tool.name": func.__name__,
                "mcp.tool.args": str(args),
                "mcp.tool.kwargs": str(kwargs)
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
    @wraps(func)
    def wrapper(*args, **kwargs):
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

# Add tracing to existing tools
async def add_tracing_to_tools():
    """Add tracing to all registered MCP tools"""
    tools = await mcp.list_tools()
    for tool_name in tools:
        tool_func = tools[tool_name]
        if not hasattr(tool_func, "_traced"):
            traced_func = trace_tool(tool_func)
            traced_func._traced = True
            mcp.add_tool(tool_name)(traced_func)

@mcp.tool()
def get_trace_info() -> Dict[str, Any]:
    """
    Get information about the current tracing configuration
    
    Returns:
        Dictionary with tracing information
    """
    try:
        current_span = trace.get_current_span()
        
        return {
            'status': 'success',
            'tracer': {
                'name': tracer.name,
                'version': trace.get_tracer_provider().__class__.__name__
            },
            'current_span': {
                'name': current_span.name if current_span else None,
                'context': str(current_span.get_span_context()) if current_span else None,
                'active': bool(current_span)
            },
            'exporter': {
                'type': otlp_exporter.__class__.__name__,
                'endpoint': otlp_exporter.endpoint
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def configure_tracing(exporter_endpoint: str = None, service_name: str = None, service_version: str = None) -> Dict[str, Any]:
    """
    Configure tracing settings
    
    Args:
        exporter_endpoint: OTLP exporter endpoint URL
        service_name: Service name for tracing
        service_version: Service version for tracing
    
    Returns:
        Dictionary with configuration result
    """
    try:
        global otlp_exporter, resource
        
        # Update exporter if endpoint provided
        if exporter_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=exporter_endpoint)
            trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        # Update resource if service info provided
        if service_name or service_version:
            attributes = {}
            if service_name:
                attributes[ResourceAttributes.SERVICE_NAME] = service_name
            if service_version:
                attributes[ResourceAttributes.SERVICE_VERSION] = service_version
            
            resource = Resource(attributes=attributes)
            
            # Update tracer provider with new resource
            trace.set_tracer_provider(TracerProvider(resource=resource))
        
        return {
            'status': 'success',
            'config': {
                'exporter_endpoint': otlp_exporter.endpoint,
                'service_name': resource.attributes.get(ResourceAttributes.SERVICE_NAME),
                'service_version': resource.attributes.get(ResourceAttributes.SERVICE_VERSION)
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def get_metrics_info() -> Dict[str, Any]:
    """
    Get information about the current metrics configuration
    
    Returns:
        Dictionary with metrics information
    """
    try:
        return {
            'status': 'success',
            'meter': {
                'name': meter.name,
                'version': meter_provider.__class__.__name__
            },
            'metrics': {
                'tool_duration': {
                    'name': tool_duration.name,
                    'description': tool_duration.description,
                    'unit': tool_duration.unit
                },
                'tool_calls': {
                    'name': tool_calls.name,
                    'description': tool_calls.description,
                    'unit': tool_calls.unit
                },
                'tool_errors': {
                    'name': tool_errors.name,
                    'description': tool_errors.description,
                    'unit': tool_errors.unit
                },
                'active_sessions': {
                    'name': active_sessions_counter.name,
                    'description': active_sessions_counter.description,
                    'unit': active_sessions_counter.unit
                },
                'memory_usage': {
                    'name': memory_usage.name,
                    'description': memory_usage.description,
                    'unit': memory_usage.unit
                }
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def configure_metrics(exporter_endpoint: str = None) -> Dict[str, Any]:
    """
    Configure metrics settings
    
    Args:
        exporter_endpoint: OTLP exporter endpoint URL
    
    Returns:
        Dictionary with configuration result
    """
    try:
        global meter_provider, meter
        
        if exporter_endpoint:
            # Create new meter provider with updated endpoint
            meter_provider = MeterProvider(
                metric_readers=[PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=exporter_endpoint)
                )]
            )
            set_meter_provider(meter_provider)
            meter = get_meter_provider().get_meter("mcp-server")
            
            # Recreate metrics with new meter
            global tool_duration, tool_calls, tool_errors, active_sessions, memory_usage
            tool_duration = meter.create_histogram(
                name="mcp.tool.duration",
                description="Duration of MCP tool execution",
                unit="s"
            )
            tool_calls = meter.create_counter(
                name="mcp.tool.calls",
                description="Number of MCP tool calls",
                unit="1"
            )
            tool_errors = meter.create_counter(
                name="mcp.tool.errors",
                description="Number of MCP tool errors",
                unit="1"
            )
            active_sessions = meter.create_up_down_counter(
                name="mcp.sessions.active",
                description="Number of active MCP sessions",
                unit="1"
            )
            memory_usage = meter.create_observable_gauge(
                name="mcp.system.memory_usage",
                description="Memory usage of the MCP server",
                unit="bytes",
                callbacks=[lambda _: [(None, psutil.Process().memory_info().rss)]]
            )
        
        return {
            'status': 'success',
            'config': {
                'exporter_endpoint': exporter_endpoint or "http://localhost:4317"
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# Add metrics to all tools
async def add_metrics_to_tools():
    """Add metrics to all registered MCP tools"""
    tools = await mcp.list_tools()
    for tool_name in tools:
        tool_func = tools[tool_name]
        if not hasattr(tool_func, "_metrics"):
            metriced_func = metrics_tool(tool_func)
            metriced_func._metrics = True
            mcp.add_tool(tool_name)(metriced_func)

# Add profiling to all tools
async def add_profiling_to_tools():
    """Add profiling to all registered MCP tools"""
    tools = await mcp.list_tools()
    for tool_name in tools:
        tool_func = tools[tool_name]
        if not hasattr(tool_func, "_profiled"):
            profiled_func = profile_tool(tool_func)
            profiled_func._profiled = True
            mcp.add_tool(tool_name)(profiled_func)

def execute_command(command: str, timeout: float = 30, allow_background: bool = False) -> Dict[str, Any]:
    """Execute a shell command with safety checks and timeout.
    
    Args:
        command: The command to execute
        timeout: Maximum execution time in seconds
        allow_background: Whether to allow the command to run in background
        
    Returns:
        Dict containing execution results with keys:
        - exit_code: The command exit code (None if background)
        - stdout: Standard output
        - stderr: Standard error
        - pid: Process ID (None if not background)
        - runtime: Execution time in seconds
        - complete: Whether execution is complete
        - error: Error message if any
    """
    start_time = time.time()
    
    # Validate command
    if not is_command_safe(command):
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": "Command was blocked for security reasons",
            "pid": None,
            "runtime": 0,
            "complete": True,
            "error": "Command blocked"
        }
    
    try:
        # Setup process with proper signal handling
        if sys.platform != "win32":
            # On Unix-like systems, create a new process group
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True,
                bufsize=1,
                universal_newlines=True,
                preexec_fn=os.setsid  # Create new process group
            )
        else:
            # On Windows, use normal process creation
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
        
        # Handle background execution
        if allow_background:
            pid = process.pid
            output_queue = queue.Queue()
            
            def read_output_thread(pipe, source):
                try:
                    for line in pipe:
                        output_queue.put({"source": source, "data": line})
                except Exception as e:
                    output_queue.put({"source": source, "data": f"Error reading output: {str(e)}\n"})
                finally:
                    try:
                        pipe.close()
                    except Exception:
                        pass
            
            # Start output reading threads
            stdout_thread = threading.Thread(target=read_output_thread, args=(process.stdout, "stdout"))
            stderr_thread = threading.Thread(target=read_output_thread, args=(process.stderr, "stderr"))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            with session_lock:
                active_sessions[pid] = {
                    "process": process,
                    "command": command,
                    "start_time": start_time,
                    "output_queue": output_queue,
                    "stdout_thread": stdout_thread,
                    "stderr_thread": stderr_thread
                }
                update_active_sessions_metric()
            
            return {
                "exit_code": None,
                "stdout": "",
                "stderr": "",
                "pid": pid,
                "runtime": time.time() - start_time,
                "complete": False
            }
        
        # Handle synchronous execution
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            exit_code = process.returncode
            complete = True
        except subprocess.TimeoutExpired:
            # Try to terminate the process group on Unix-like systems
            if sys.platform != "win32":
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass
            process.kill()
            stdout, stderr = process.communicate()
            exit_code = -1
            complete = True
            stderr += "\nCommand timed out"
        
        return {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "pid": None,
            "runtime": time.time() - start_time,
            "complete": complete
        }
        
    except Exception as e:
        return {
            "exit_code": None,
            "stdout": "",
            "stderr": str(e),
            "pid": None,
            "runtime": time.time() - start_time,
            "complete": True,
            "error": str(e)
        }

def read_queue_contents(q: queue.Queue) -> List[str]:
    """Read all available content from a queue without blocking."""
    contents = []
    while True:
        try:
            contents.append(q.get_nowait())
        except queue.Empty:
            break
    return contents

def read_output(pid: int) -> Dict[str, Any]:
    """Read output from a background process.
    
    Args:
        pid: Process ID of the background process
        
    Returns:
        Dict containing:
        - stdout: Standard output
        - stderr: Standard error
        - complete: Whether process has completed
        - pid: Process ID (None if complete)
        - runtime: Process runtime in seconds
        - exit_code: Process exit code (None if still running)
    """
    with session_lock:
        if pid not in active_sessions:
            return {
                "stdout": "",
                "stderr": "Process not found",
                "complete": True,
                "pid": None,
                "runtime": 0,
                "exit_code": None,
                "error": "Process not found"
            }
        
        session = active_sessions[pid]
        process = session["process"]
        start_time = session["start_time"]
        output_queue = session["output_queue"]
        
        # Check if process has completed
        if process.poll() is not None:
            # Process finished, get final output
            stdout, stderr = process.communicate()
            exit_code = process.returncode
            runtime = time.time() - start_time
            
            # Clean up threads
            if "stdout_thread" in session:
                session["stdout_thread"].join(timeout=1)
            if "stderr_thread" in session:
                session["stderr_thread"].join(timeout=1)
            
            # Clean up session
            del active_sessions[pid]
            update_active_sessions_metric()
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "complete": True,
                "pid": None,
                "runtime": runtime,
                "exit_code": exit_code
            }
        
        # Process still running, get current output
        try:
            stdout = ""
            stderr = ""
            
            # Read all available output from queue with a timeout
            max_iterations = 100  # Prevent infinite loops
            iteration = 0
            while iteration < max_iterations:
                try:
                    output = output_queue.get_nowait()
                    if output["source"] == "stdout":
                        stdout += output["data"]
                    else:
                        stderr += output["data"]
                except queue.Empty:
                    break
                iteration += 1
            
            # If we hit the max iterations, log a warning
            if iteration >= max_iterations:
                stderr += "\nWarning: Maximum iterations reached while reading output queue"
            
            return {
                "stdout": stdout,
                "stderr": stderr,
                "complete": False,
                "pid": pid,
                "runtime": time.time() - start_time,
                "exit_code": None
            }
            
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "complete": False,
                "pid": pid,
                "runtime": time.time() - start_time,
                "exit_code": None,
                "error": str(e)
            }

@mcp.resource("debug://state")
def debug_state() -> Dict[str, Any]:
    """
    Resource that provides current debug state information
    
    Returns:
        Dictionary with debug state information
    """
    active_sessions = []
    
    for session_id, session in debug_sessions.items():
        if session.get('active', False):
            active_sessions.append({
                'session_id': session_id,
                'file': session.get('file'),
                'line': session.get('line'),
                'variables': session.get('variables', {}),
                'call_stack': session.get('call_stack', []),
                'breakpoints': debug_breakpoints.get(session_id, [])
            })
    
    return {
        'active_sessions': active_sessions,
        'global_breakpoints': [bp for bp_list in debug_breakpoints.values() for bp in bp_list],
        'timestamp': datetime.now().isoformat()
    }

@mcp.tool()
def debug_control(action: str, session_id: str = None, file_path: str = None, line_number: int = None, expression: str = None) -> Dict[str, Any]:
    """
    Control debugging sessions and evaluate expressions
    
    Args:
        action: Debug action ('start', 'stop', 'step', 'continue', 'breakpoint', 'evaluate')
        session_id: Debug session identifier
        file_path: Path to the file being debugged
        line_number: Line number for breakpoint
        expression: Expression to evaluate in current context
    
    Returns:
        Dictionary with operation result
    """
    try:
        if action == 'start':
            if not file_path:
                return {'status': 'error', 'error': 'File path required to start debugging'}
                
            # Create new debug session
            session_id = f"debug_{int(time.time())}"
            debug_sessions[session_id] = {
                'active': True,
                'file': file_path,
                'line': 1,
                'variables': {},
                'call_stack': [],
                'start_time': datetime.now().isoformat()
            }
            
            # Start debug process
            process = subprocess.Popen(
                ['python', '-m', 'pdb', file_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            debug_sessions[session_id]['process'] = process
            return {
                'status': 'success',
                'session_id': session_id,
                'message': f'Debug session started for {file_path}'
            }
            
        elif action == 'stop':
            if not session_id or session_id not in debug_sessions:
                return {'status': 'error', 'error': 'Invalid session ID'}
                
            session = debug_sessions[session_id]
            if session.get('process'):
                session['process'].terminate()
            
            session['active'] = False
            return {
                'status': 'success',
                'message': f'Debug session {session_id} stopped'
            }
            
        elif action == 'breakpoint':
            if not file_path or not line_number:
                return {'status': 'error', 'error': 'File path and line number required for breakpoint'}
                
            if session_id not in debug_breakpoints:
                debug_breakpoints[session_id] = []
                
            breakpoint_info = {
                'file': file_path,
                'line': line_number,
                'enabled': True
            }
            
            debug_breakpoints[session_id].append(breakpoint_info)
            return {
                'status': 'success',
                'message': f'Breakpoint set at {file_path}:{line_number}'
            }
            
        elif action in ['step', 'continue']:
            if not session_id or session_id not in debug_sessions:
                return {'status': 'error', 'error': 'Invalid session ID'}
                
            session = debug_sessions[session_id]
            if not session.get('process'):
                return {'status': 'error', 'error': 'Debug process not running'}
                
            # Send appropriate command to debugger
            cmd = 'n' if action == 'step' else 'c'
            session['process'].stdin.write(f'{cmd}\n')
            session['process'].stdin.flush()
            
            # Read output until next break
            output = []
            while True:
                line = session['process'].stdout.readline()
                if not line or '(Pdb)' in line:
                    break
                output.append(line.strip())
            
            return {
                'status': 'success',
                'output': output,
                'action': action
            }
            
        elif action == 'evaluate':
            if not session_id or session_id not in debug_sessions:
                return {'status': 'error', 'error': 'Invalid session ID'}
                
            if not expression:
                return {'status': 'error', 'error': 'Expression required for evaluation'}
                
            session = debug_sessions[session_id]
            if not session.get('process'):
                return {'status': 'error', 'error': 'Debug process not running'}
                
            # Send expression to debugger
            session['process'].stdin.write(f'p {expression}\n')
            session['process'].stdin.flush()
            
            # Read result
            result = session['process'].stdout.readline().strip()
            return {
                'status': 'success',
                'expression': expression,
                'result': result
            }
            
        else:
            return {'status': 'error', 'error': f'Unknown action: {action}'}
            
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def git_operation(command: str, parameters: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Execute Git operations safely
    
    Args:
        command: Git command to execute ('status', 'diff', 'log', 'branch', 'commit')
        parameters: Additional parameters for the command
    
    Returns:
        Dictionary with operation result
    """
    if not parameters:
        parameters = {}
        
    # Validate command
    allowed_commands = {
        'status': [],
        'diff': ['file', 'staged'],
        'log': ['limit', 'file'],
        'branch': ['name', 'delete'],
        'commit': ['message', 'files']
    }
    
    if command not in allowed_commands:
        return {
            'status': 'error',
            'error': f'Unsupported git command: {command}'
        }
    
    try:
        if command == 'status':
            result = subprocess.run(['git', 'status', '--porcelain'], 
                                 capture_output=True, text=True, check=True)
            
            # Parse status output
            changes = {
                'staged': [],
                'unstaged': [],
                'untracked': []
            }
            
            for line in result.stdout.split('\n'):
                if not line:
                    continue
                status = line[:2]
                file = line[3:]
                
                if status[0] != ' ':
                    changes['staged'].append({'file': file, 'status': status[0]})
                if status[1] != ' ':
                    changes['unstaged'].append({'file': file, 'status': status[1]})
                if status == '??':
                    changes['untracked'].append(file)
                    
            return {
                'status': 'success',
                'changes': changes
            }
            
        elif command == 'diff':
            cmd = ['git', 'diff']
            if parameters.get('staged'):
                cmd.append('--staged')
            if parameters.get('file'):
                cmd.append(parameters['file'])
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                'status': 'success',
                'diff': result.stdout
            }
            
        elif command == 'log':
            cmd = ['git', 'log', '--pretty=format:%H|%an|%ad|%s']
            if parameters.get('limit'):
                cmd.append(f'-n{parameters["limit"]}')
            if parameters.get('file'):
                cmd.append(parameters['file'])
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            commits = []
            for line in result.stdout.split('\n'):
                if line:
                    hash, author, date, message = line.split('|')
                    commits.append({
                        'hash': hash,
                        'author': author,
                        'date': date,
                        'message': message
                    })
                    
            return {
                'status': 'success',
                'commits': commits
            }
            
        elif command == 'branch':
            if parameters.get('delete'):
                if not parameters.get('name'):
                    return {'status': 'error', 'error': 'Branch name required for deletion'}
                cmd = ['git', 'branch', '-D', parameters['name']]
            elif parameters.get('name'):
                cmd = ['git', 'checkout', '-b', parameters['name']]
            else:
                cmd = ['git', 'branch']
                
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return {
                'status': 'success',
                'output': result.stdout
            }
            
        elif command == 'commit':
            if not parameters.get('message'):
                return {'status': 'error', 'error': 'Commit message required'}
                
            # Stage files if specified
            if parameters.get('files'):
                files = parameters['files'] if isinstance(parameters['files'], list) else [parameters['files']]
                for file in files:
                    subprocess.run(['git', 'add', file], check=True)
            
            # Create commit
            result = subprocess.run(['git', 'commit', '-m', parameters['message']], 
                                 capture_output=True, text=True, check=True)
                                 
            return {
                'status': 'success',
                'message': result.stdout
            }
            
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'error': e.stderr
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

# Development Tools

@mcp.tool()
def install_dependency(package: str, dev: bool = False) -> Dict[str, Any]:
    """
    Install Python package using uv
    
    Args:
        package: Package name and optional version spec
        dev: Whether to install as a development dependency
    
    Returns:
        Dictionary with installation result
    """
    try:
        cmd = ['uv', 'add']
        if dev:
            cmd.append('--dev')
        cmd.append(package)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Read pyproject.toml to verify installation
        with open('pyproject.toml', 'r') as f:
            pyproject_content = f.read()
            
        return {
            'status': 'success',
            'output': result.stdout,
            'package': package,
            'pyproject_toml': pyproject_content
        }
    except subprocess.CalledProcessError as e:
        return {
            'status': 'error',
            'error': e.stderr
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def run_tests(target: str = None, docker: bool = False) -> Dict[str, Any]:
    """
    Run tests with proper isolation
    
    Args:
        target: Specific test target (file or directory)
        docker: Whether to run tests in Docker
    
    Returns:
        Dictionary with test results
    """
    try:
        if docker:
            cmd = ['make', 'test']
            if target:
                cmd.extend(['TEST_TARGET=' + target])
        else:
            cmd = ['pytest']
            if target:
                cmd.append(target)
            cmd.extend(['-v', '--capture=no'])
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Process the output to be more LLM-friendly
        output_lines = result.stdout.split('\n')
        filtered_output = _filter_test_output(output_lines)
        
        return {
            'status': 'success' if result.returncode == 0 else 'failure',
            'output': filtered_output,
            'exit_code': result.returncode,
            'errors': result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _filter_test_output(lines: List[str]) -> str:
    """Helper to filter and format test output for LLM consumption"""
    important_lines = []
    summary_stats = {}
    
    for line in lines:
        # Keep test results
        if line.startswith('test_'):
            important_lines.append(line)
        # Keep error messages
        elif 'ERROR' in line or 'FAILED' in line:
            important_lines.append(line)
        # Extract summary statistics
        elif 'failed' in line and 'passed' in line:
            summary_stats['summary'] = line.strip()
            
    return {
        'details': important_lines,
        'summary': summary_stats
    }

@mcp.tool()
def format_code(path: str = '.') -> Dict[str, Any]:
    """
    Format code using ruff
    
    Args:
        path: Path to format (file or directory)
    
    Returns:
        Dictionary with formatting result
    """
    try:
        cmd = ['ruff', 'format', path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            'status': 'success' if result.returncode == 0 else 'error',
            'output': result.stdout,
            'errors': result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def lint_code(path: str = '.', fix: bool = False) -> Dict[str, Any]:
    """
    Run ruff linting
    
    Args:
        path: Path to lint (file or directory)
        fix: Whether to automatically fix issues
    
    Returns:
        Dictionary with linting result
    """
    try:
        cmd = ['ruff', 'check']
        if fix:
            cmd.append('--fix')
        cmd.append(path)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Process output to be more LLM-friendly
        output_lines = result.stdout.split('\n')
        filtered_output = _filter_lint_output(output_lines)
        
        return {
            'status': 'success' if result.returncode == 0 else 'warning',
            'issues': filtered_output,
            'errors': result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _filter_lint_output(lines: List[str]) -> List[Dict[str, Any]]:
    """Helper to filter and format lint output for LLM consumption"""
    issues = []
    
    for line in lines:
        if not line.strip():
            continue
            
        # Parse ruff output format
        try:
            file_path, line_no, message = line.split(':', 2)
            issues.append({
                'file': file_path.strip(),
                'line': int(line_no),
                'message': message.strip()
            })
        except ValueError:
            continue
            
    return issues

@mcp.tool()
def monitor_performance(duration: int = 60, interval: float = 1.0) -> Dict[str, Any]:
    """
    Monitor system performance metrics
    
    Args:
        duration: Monitoring duration in seconds
        interval: Sampling interval in seconds
    
    Returns:
        Dictionary with performance metrics
    """
    try:
        import psutil
        from datetime import datetime, timedelta
        
        metrics = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'network': []
        }
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration)
        
        while datetime.now() < end_time:
            # CPU metrics
            metrics['cpu'].append({
                'timestamp': datetime.now().isoformat(),
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            })
            
            # Memory metrics
            mem = psutil.virtual_memory()
            metrics['memory'].append({
                'timestamp': datetime.now().isoformat(),
                'total': mem.total,
                'available': mem.available,
                'percent': mem.percent,
                'used': mem.used,
                'free': mem.free
            })
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics['disk'].append({
                'timestamp': datetime.now().isoformat(),
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            })
            
            # Network metrics
            net = psutil.net_io_counters()
            metrics['network'].append({
                'timestamp': datetime.now().isoformat(),
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
                'packets_sent': net.packets_sent,
                'packets_recv': net.packets_recv
            })
            
            time.sleep(interval)
        
        # Calculate summary statistics
        summary = {
            'cpu': {
                'avg': sum(m['percent'] for m in metrics['cpu']) / len(metrics['cpu']) if metrics['cpu'] else 0,
                'max': max(m['percent'] for m in metrics['cpu']) if metrics['cpu'] else 0,
                'min': min(m['percent'] for m in metrics['cpu']) if metrics['cpu'] else 0
            },
            'memory': {
                'avg_percent': sum(m['percent'] for m in metrics['memory']) / len(metrics['memory']) if metrics['memory'] else 0,
                'max_percent': max(m['percent'] for m in metrics['memory']) if metrics['memory'] else 0,
                'min_percent': min(m['percent'] for m in metrics['memory']) if metrics['memory'] else 0
            },
            'disk': {
                'start_percent': metrics['disk'][0]['percent'] if metrics['disk'] else 0,
                'end_percent': metrics['disk'][-1]['percent'] if metrics['disk'] else 0
            },
            'network': {
                'total_sent': metrics['network'][-1]['bytes_sent'] - metrics['network'][0]['bytes_sent'] if len(metrics['network']) > 1 else 0,
                'total_recv': metrics['network'][-1]['bytes_recv'] - metrics['network'][0]['bytes_recv'] if len(metrics['network']) > 1 else 0
            }
        }
        
        return {
            'status': 'success',
            'summary': summary,
            'raw_metrics': metrics
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def generate_documentation(target: str, doc_type: str = "api", template: str = None) -> Dict[str, Any]:
    """Generate documentation for code.
    
    Args:
        target: File or directory to generate docs for
        doc_type: Type of documentation ('api', 'readme', 'wiki')
        template: Optional template file to use
        
    Returns:
        Dictionary with generated documentation
    """
    try:
        if doc_type == "api":
            return _generate_api_docs(target)
        elif doc_type == "readme":
            return _generate_readme(target, template)
        elif doc_type == "wiki":
            return _generate_wiki(target, template)
        else:
            return {
                "status": "error",
                "error": f"Unknown documentation type: {doc_type}"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _generate_api_docs(target: str) -> Dict[str, Any]:
    """Generate API documentation using pdoc."""
    try:
        import pdoc
        
        # Generate HTML documentation
        doc = pdoc.doc.Module(pdoc.import_module(target))
        html = doc.html()
        
        # Save to file
        output_dir = "docs/api"
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{target}.html")
        
        with open(output_file, "w") as f:
            f.write(html)
            
        return {
            "status": "success",
            "output_file": output_file,
            "module": target
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _generate_readme(target: str, template: str = None) -> Dict[str, Any]:
    """Generate README documentation."""
    try:
        # Get project info
        project_info = _analyze_project_info(target)
        
        # Load template or use default
        if template and os.path.exists(template):
            with open(template) as f:
                template_content = f.read()
        else:
            template_content = DEFAULT_README_TEMPLATE
            
        # Generate README content
        content = template_content.format(
            project_name=project_info["name"],
            description=project_info["description"],
            setup=project_info["setup"],
            usage=project_info["usage"],
            api=project_info["api"],
            contributing=project_info["contributing"]
        )
        
        # Save README
        output_file = os.path.join(target, "README.md")
        with open(output_file, "w") as f:
            f.write(content)
            
        return {
            "status": "success",
            "output_file": output_file,
            "content": content
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _generate_wiki(target: str, template: str = None) -> Dict[str, Any]:
    """Generate wiki documentation."""
    try:
        # Analyze codebase
        analysis = _analyze_codebase_for_wiki(target)
        
        # Generate wiki pages
        pages = {}
        wiki_dir = "docs/wiki"
        os.makedirs(wiki_dir, exist_ok=True)
        
        for topic, content in analysis.items():
            page_file = os.path.join(wiki_dir, f"{topic}.md")
            with open(page_file, "w") as f:
                f.write(content)
            pages[topic] = page_file
            
        return {
            "status": "success",
            "pages": pages,
            "index": os.path.join(wiki_dir, "index.md")
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _setup_validation_gates_internal(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Set up validation gates for the project."""
    if config is None:
        config = {
            "pre_commit": True,
            "ci": {
                "linting": True,
                "testing": True,
                "coverage": {
                    "required": 90
                },
                "security": True
            },
            "benchmarks": {
                "performance": True,
                "memory": True
            }
        }
        
    results = {}
    
    # Set up pre-commit hooks
    if config.get("pre_commit"):
        results["pre_commit"] = _setup_pre_commit_hooks(config)
        
    # Set up CI validation
    if config.get("ci"):
        results["ci"] = _setup_ci_validation(config["ci"])
        
    # Set up benchmarks
    if config.get("benchmarks"):
        results["benchmarks"] = _setup_benchmarks(config["benchmarks"])
        
    return {
        "status": "success" if all(r.get("status") == "success" for r in results.values()) else "error",
        "results": results
    }

def _analyze_project_internal(path: str = ".") -> Dict[str, Any]:
    """Analyze project for documentation and insights."""
    try:
        # Get project info
        info = _analyze_project_info(path)
        
        # Get wiki content
        wiki = _analyze_codebase_for_wiki(path)
        
        # Analyze dependencies
        dependencies = {}
        if os.path.exists("requirements.txt"):
            with open("requirements.txt") as f:
                dependencies["requirements"] = [line.strip() for line in f if line.strip()]
        elif os.path.exists("pyproject.toml"):
            with open("pyproject.toml") as f:
                content = f.read()
                deps_match = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
                if deps_match:
                    dependencies["pyproject"] = [
                        dep.strip().strip('"\'') 
                        for dep in deps_match.group(1).split(",")
                        if dep.strip()
                    ]
                    
        # Analyze code metrics
        metrics = {
            "files": 0,
            "lines": 0,
            "functions": 0,
            "classes": 0,
            "imports": set()
        }
        
        for root, _, files in os.walk(path):
            if ".git" in root or "__pycache__" in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    metrics["files"] += 1
                    file_path = os.path.join(root, file)
                    
                    with open(file_path) as f:
                        content = f.read()
                        
                    metrics["lines"] += len(content.splitlines())
                    
                    tree = ast.parse(content)
                    metrics["functions"] += len([
                        node for node in ast.walk(tree) 
                        if isinstance(node, ast.FunctionDef)
                    ])
                    metrics["classes"] += len([
                        node for node in ast.walk(tree)
                        if isinstance(node, ast.ClassDef)
                    ])
                    metrics["imports"].update([
                        node.names[0].name
                        for node in ast.walk(tree)
                        if isinstance(node, ast.Import) and node.names
                    ])
                    metrics["imports"].update([
                        node.module
                        for node in ast.walk(tree)
                        if isinstance(node, ast.ImportFrom) and node.module
                    ])
                    
        metrics["imports"] = sorted(metrics["imports"])
        
        return {
            "status": "success",
            "info": info,
            "wiki": wiki,
            "dependencies": dependencies,
            "metrics": metrics
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _manage_changes_internal(action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Manage code changes and releases."""
    try:
        if action == "branch":
            return _manage_branch(params)
        elif action == "pr":
            return _create_pull_request(params)
        elif action == "release":
            return _create_release(params)
        elif action == "changelog":
            return _generate_changelog(params)
        else:
            return {
                "status": "error",
                "error": f"Unknown action: {action}"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@mcp.tool()
def setup_validation_gates(config: Dict[str, Any] = None) -> Dict[str, Any]:
    """Set up validation gates for the project.
    
    Args:
        config: Configuration for validation gates. If None, uses default config.
        
    Returns:
        Dict with setup results for each validation gate.
    """
    return _setup_validation_gates_internal(config)

@mcp.tool()
def analyze_project(path: str = ".") -> Dict[str, Any]:
    """Analyze project for documentation and insights.
    
    Args:
        path: Path to project root. Defaults to current directory.
        
    Returns:
        Dict with project analysis results.
    """
    return _analyze_project_internal(path)

@mcp.tool()
def manage_changes(action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Manage code changes and releases.
    
    Args:
        action: Action to perform ('branch', 'pr', 'release', 'changelog')
        params: Parameters for the action
        
    Returns:
        Dict with action results.
    """
    return _manage_changes_internal(action, params)

# Constants

DEFAULT_README_TEMPLATE = """
# {project_name}

{description}

## Setup

{setup}

## Usage

{usage}

## API Documentation

{api}

## Contributing

{contributing}
"""

DEFAULT_VALIDATION_CONFIG = {
    "pre_commit": {
        "hooks": [
            "black",
            "flake8",
            "mypy",
            "pytest"
        ]
    },
    "ci": {
        "linting": True,
        "testing": True,
        "coverage": {
            "required": 90
        },
        "security": True
    },
    "benchmarks": {
        "performance": True,
        "memory": True
    }
}

def _setup_pre_commit_hooks(config: Dict[str, Any]) -> Dict[str, Any]:
    """Set up pre-commit hooks."""
    try:
        hooks = config.get("hooks", [])
        
        # Create pre-commit config
        pre_commit_config = {
            "repos": [
                {
                    "repo": "https://github.com/psf/black",
                    "rev": "stable",
                    "hooks": [{"id": "black"}]
                },
                {
                    "repo": "https://github.com/pycqa/flake8",
                    "rev": "master",
                    "hooks": [{"id": "flake8"}]
                },
                {
                    "repo": "https://github.com/pre-commit/mirrors-mypy",
                    "rev": "master",
                    "hooks": [{"id": "mypy"}]
                }
            ]
        }
        
        # Save config
        with open(".pre-commit-config.yaml", "w") as f:
            yaml.dump(pre_commit_config, f)
            
        # Install hooks
        result = subprocess.run(
            ["pre-commit", "install"],
            capture_output=True,
            text=True
        )
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _setup_ci_validation(config: Dict[str, Any]) -> Dict[str, Any]:
    """Set up CI validation."""
    try:
        # Create GitHub Actions workflow
        workflow = {
            "name": "CI",
            "on": ["push", "pull_request"],
            "jobs": {
                "validate": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "uses": "actions/checkout@v2"
                        },
                        {
                            "uses": "actions/setup-python@v2",
                            "with": {
                                "python-version": "3.x"
                            }
                        }
                    ]
                }
            }
        }
        
        # Add validation steps based on config
        steps = workflow["jobs"]["validate"]["steps"]
        
        if config.get("linting"):
            steps.append({
                "name": "Lint",
                "run": "pip install flake8 && flake8"
            })
            
        if config.get("testing"):
            steps.append({
                "name": "Test",
                "run": "pip install pytest && pytest"
            })
            
        if config.get("coverage"):
            steps.append({
                "name": "Coverage",
                "run": f"pip install pytest-cov && pytest --cov=. --cov-fail-under={config['coverage'].get('required', 90)}"
            })
            
        if config.get("security"):
            steps.append({
                "name": "Security Check",
                "run": "pip install bandit && bandit -r ."
            })
            
        # Save workflow
        os.makedirs(".github/workflows", exist_ok=True)
        with open(".github/workflows/ci.yml", "w") as f:
            yaml.dump(workflow, f)
            
        return {
            "status": "success",
            "workflow": workflow
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _setup_benchmarks(config: Dict[str, Any]) -> Dict[str, Any]:
    """Set up performance benchmarks."""
    try:
        benchmarks = []
        
        if config.get("performance"):
            # Create performance benchmark
            benchmark = """
import pytest
from your_module import your_function

@pytest.mark.benchmark
def test_performance(benchmark):
    result = benchmark(your_function)
    assert result  # Add appropriate assertion
"""
            benchmarks.append(("tests/test_performance.py", benchmark))
            
        if config.get("memory"):
            # Create memory benchmark
            benchmark = """
import pytest
import memory_profiler

@pytest.mark.benchmark
def test_memory():
    @memory_profiler.profile
    def wrapper():
        # Add your function call here
        pass
        
    wrapper()
"""
            benchmarks.append(("tests/test_memory.py", benchmark))
            
        # Save benchmarks
        os.makedirs("tests", exist_ok=True)
        for file_path, content in benchmarks:
            with open(file_path, "w") as f:
                f.write(content)
                
        return {
            "status": "success",
            "benchmarks": [path for path, _ in benchmarks]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _analyze_project_info(path: str) -> Dict[str, Any]:
    """Analyze project information for documentation."""
    try:
        info = {
            "name": os.path.basename(os.path.abspath(path)),
            "description": "",
            "setup": "",
            "usage": "",
            "api": "",
            "contributing": ""
        }
        
        # Try to get description from setup.py/pyproject.toml
        if os.path.exists("setup.py"):
            with open("setup.py") as f:
                content = f.read()
                desc_match = re.search(r'description\s*=\s*[\'"](.+?)[\'"]', content)
                if desc_match:
                    info["description"] = desc_match.group(1)
        elif os.path.exists("pyproject.toml"):
            with open("pyproject.toml") as f:
                content = f.read()
                desc_match = re.search(r'description\s*=\s*[\'"](.+?)[\'"]', content)
                if desc_match:
                    info["description"] = desc_match.group(1)
                    
        # Get setup instructions
        if os.path.exists("pyproject.toml"):
            info["setup"] = """
1. Install dependencies:
   ```
   pip install .
   ```
"""
        elif os.path.exists("requirements.txt"):
            info["setup"] = """
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
"""
        
        # Get usage examples from docstrings
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    with open(os.path.join(root, file)) as f:
                        content = f.read()
                        docstring_match = re.search(r'"""(.+?)"""', content, re.DOTALL)
                        if docstring_match and "Example" in docstring_match.group(1):
                            info["usage"] += f"\n### {file}\n\n{docstring_match.group(1)}"
                            
        # Get API documentation
        info["api"] = "See the [API Documentation](docs/api/index.html) for detailed reference."
        
        # Get contributing guidelines
        if os.path.exists("CONTRIBUTING.md"):
            with open("CONTRIBUTING.md") as f:
                info["contributing"] = f.read()
        else:
            info["contributing"] = """
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
"""
        
        return info
    except Exception as e:
        return {
            "name": "Unknown",
            "description": "Error analyzing project info: " + str(e),
            "setup": "",
            "usage": "",
            "api": "",
            "contributing": ""
        }

def _analyze_codebase_for_wiki(path: str) -> Dict[str, str]:
    """Analyze codebase for wiki documentation."""
    try:
        analysis = {
            "index": "# Project Wiki\n\n",
            "architecture": "# Architecture\n\n",
            "modules": "# Modules\n\n",
            "workflows": "# Workflows\n\n",
            "development": "# Development Guide\n\n"
        }
        
        # Analyze architecture
        analysis["architecture"] += "## Overview\n\n"
        for root, dirs, files in os.walk(path):
            if ".git" in dirs:
                dirs.remove(".git")
                
            rel_path = os.path.relpath(root, path)
            if rel_path == ".":
                analysis["architecture"] += "Project structure:\n\n```\n"
            else:
                analysis["architecture"] += "  " * rel_path.count(os.sep) + rel_path.split(os.sep)[-1] + "/\n"
                
            for file in sorted(files):
                if file.endswith(".py"):
                    analysis["architecture"] += "  " * (rel_path.count(os.sep) + 1) + file + "\n"
                    
        analysis["architecture"] += "```\n"
        
        # Analyze modules
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith(".py"):
                    with open(os.path.join(root, file)) as f:
                        content = f.read()
                        
                    # Extract classes and functions
                    tree = ast.parse(content)
                    classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                    functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                    
                    if classes or functions:
                        rel_path = os.path.relpath(os.path.join(root, file), path)
                        analysis["modules"] += f"## {rel_path}\n\n"
                        
                        if classes:
                            analysis["modules"] += "### Classes\n\n"
                            for cls in classes:
                                analysis["modules"] += f"- `{cls}`\n"
                                
                        if functions:
                            analysis["modules"] += "\n### Functions\n\n"
                            for func in functions:
                                analysis["modules"] += f"- `{func}`\n"
                                
                        analysis["modules"] += "\n"
                        
        # Add development guide
        analysis["development"] += """
## Setup Development Environment

1. Clone the repository
2. Install dependencies
3. Set up pre-commit hooks
4. Run tests

## Code Style

Follow PEP 8 guidelines and use the provided linting tools.

## Testing

Write tests for new features and ensure all tests pass before submitting changes.

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request
"""
        
        # Update index
        analysis["index"] += """
- [Architecture](architecture.md)
- [Modules](modules.md)
- [Workflows](workflows.md)
- [Development Guide](development.md)
"""
        
        return analysis
    except Exception as e:
        return {
            "index": f"Error analyzing codebase: {str(e)}"
        }

def _manage_branch(params: Dict[str, Any]) -> Dict[str, Any]:
    """Manage git branches."""
    try:
        action = params.get("action")
        branch = params.get("branch")
        
        if not action or not branch:
            return {
                "status": "error",
                "error": "Missing required parameters"
            }
            
        if action == "create":
            cmd = ["git", "checkout", "-b", branch]
        elif action == "delete":
            cmd = ["git", "branch", "-D", branch]
        elif action == "merge":
            target = params.get("target", "main")
            cmd = ["git", "merge", branch, target]
        else:
            return {
                "status": "error",
                "error": f"Unknown branch action: {action}"
            }
            
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _create_pull_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a pull request."""
    try:
        title = params.get("title")
        body = params.get("body")
        base = params.get("base", "main")
        head = params.get("head")
        
        if not all([title, body, head]):
            return {
                "status": "error",
                "error": "Missing required parameters"
            }
            
        # Create PR using GitHub CLI
        cmd = [
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", base,
            "--head", head
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _create_release(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a release."""
    try:
        version = params.get("version")
        notes = params.get("notes")
        
        if not version:
            return {
                "status": "error",
                "error": "Version is required"
            }
            
        # Create git tag
        tag_cmd = ["git", "tag", "-a", f"v{version}", "-m", f"Release {version}"]
        tag_result = subprocess.run(tag_cmd, capture_output=True, text=True)
        
        if tag_result.returncode != 0:
            return {
                "status": "error",
                "error": f"Failed to create tag: {tag_result.stderr}"
            }
            
        # Push tag
        push_cmd = ["git", "push", "origin", f"v{version}"]
        push_result = subprocess.run(push_cmd, capture_output=True, text=True)
        
        if push_result.returncode != 0:
            return {
                "status": "error",
                "error": f"Failed to push tag: {push_result.stderr}"
            }
            
        # Create GitHub release
        release_cmd = [
            "gh", "release", "create",
            f"v{version}",
            "--title", f"Release {version}",
            "--notes", notes or f"Release {version}"
        ]
        
        release_result = subprocess.run(release_cmd, capture_output=True, text=True)
        
        return {
            "status": "success" if release_result.returncode == 0 else "error",
            "version": version,
            "output": release_result.stdout,
            "error": release_result.stderr if release_result.returncode != 0 else None
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _generate_changelog(params: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a changelog."""
    try:
        since = params.get("since")
        until = params.get("until", "HEAD")
        
        # Get git log
        cmd = [
            "git", "log",
            "--pretty=format:%h %s",
            f"{since}..{until}" if since else ""
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return {
                "status": "error",
                "error": f"Failed to get git log: {result.stderr}"
            }
            
        # Parse commits and categorize
        changes = {
            "features": [],
            "fixes": [],
            "docs": [],
            "other": []
        }
        
        for line in result.stdout.split("\n"):
            if not line:
                continue
                
            hash, message = line.split(" ", 1)
            
            if message.startswith("feat"):
                changes["features"].append((hash, message))
            elif message.startswith("fix"):
                changes["fixes"].append((hash, message))
            elif message.startswith("docs"):
                changes["docs"].append((hash, message))
            else:
                changes["other"].append((hash, message))
                
        # Generate markdown
        content = ["# Changelog\n"]
        
        for category, commits in changes.items():
            if commits:
                content.append(f"\n## {category.title()}\n")
                for hash, message in commits:
                    content.append(f"- [{hash}] {message}")
                    
        changelog = "\n".join(content)
        
        # Save to file
        output_file = "CHANGELOG.md"
        with open(output_file, "w") as f:
            f.write(changelog)
        
        return {
            "status": "success",
            "output_file": output_file,
            "content": changelog
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _analyze_security(node: ast.AST) -> Dict[str, Any]:
    """Analyze code for security issues."""
    issues = []
    recommendations = []
    
    class SecurityVisitor(ast.NodeVisitor):
        def visit_Import(self, node):
            dangerous_imports = {
                "os": "System access",
                "subprocess": "Command execution",
                "pickle": "Unsafe deserialization",
                "marshal": "Unsafe deserialization",
                "shelve": "Unsafe file access"
            }
            
            for name in node.names:
                if name.name in dangerous_imports:
                    issues.append(f"Dangerous import: {name.name} ({dangerous_imports[name.name]})")
                    recommendations.append(f"Consider using a safer alternative to {name.name}")
            self.generic_visit(node)
            
        def visit_ImportFrom(self, node):
            dangerous_modules = {
                "os": "System access",
                "subprocess": "Command execution",
                "pickle": "Unsafe deserialization",
                "marshal": "Unsafe deserialization",
                "shelve": "Unsafe file access"
            }
            
            if node.module in dangerous_modules:
                issues.append(f"Dangerous import: {node.module} ({dangerous_modules[node.module]})")
                recommendations.append(f"Consider using a safer alternative to {node.module}")
            self.generic_visit(node)
            
        def visit_Call(self, node):
            dangerous_functions = {
                "eval": "Code execution",
                "exec": "Code execution",
                "input": "Unsanitized input",
                "open": "File access"
            }
            
            if isinstance(node.func, ast.Name):
                if node.func.id in dangerous_functions:
                    issues.append(f"Dangerous function call: {node.func.id} ({dangerous_functions[node.func.id]})")
                    recommendations.append(f"Replace {node.func.id}() with a safer alternative")
            self.generic_visit(node)
    
    visitor = SecurityVisitor()
    visitor.visit(node)
    
    status = "success"
    if issues:
        status = "error"
    
    return {
        "status": status,
        "issues": issues,
        "recommendations": recommendations
    }

def _analyze_style(code: str) -> Dict[str, Any]:
    """Analyze code style."""
    issues = []
    recommendations = []
    
    try:
        tree = ast.parse(code)
        
        class StyleVisitor(ast.NodeVisitor):
            def visit_Name(self, node):
                if not node.id.islower() and not node.id.isupper():
                    issues.append(f"Variable name '{node.id}' should be lowercase with underscores")
                    recommendations.append("Use lowercase with underscores for variable names")
                elif len(node.id) == 1 and node.id not in ['i', 'j', 'k', 'n', 'm']:
                    issues.append(f"Single-letter variable name '{node.id}' should be more descriptive")
                    recommendations.append("Use descriptive variable names")
                self.generic_visit(node)
                
            def visit_FunctionDef(self, node):
                if not node.name.islower():
                    issues.append(f"Function name '{node.name}' should be lowercase with underscores")
                    recommendations.append("Use lowercase with underscores for function names")
                if not node.args.args and not isinstance(node.body[0], ast.Expr):
                    issues.append(f"Function '{node.name}' is missing a docstring")
                    recommendations.append("Add docstrings to all functions")
                self.generic_visit(node)
                
            def visit_ClassDef(self, node):
                if not node.name[0].isupper():
                    issues.append(f"Class name '{node.name}' should use CapWords convention")
                    recommendations.append("Use CapWords for class names")
                if not isinstance(node.body[0], ast.Expr):
                    issues.append(f"Class '{node.name}' is missing a docstring")
                    recommendations.append("Add docstrings to all classes")
                self.generic_visit(node)
        
        visitor = StyleVisitor()
        visitor.visit(tree)
        
        # Check line length
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line.strip()) > 100:
                issues.append(f"Line {i} is too long (>100 characters)")
                recommendations.append("Keep lines under 100 characters")
        
        status = "success"
        if issues:
            status = "warning"
        
        return {
            "status": status,
            "issues": issues,
            "recommendations": list(set(recommendations))  # Remove duplicates
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to analyze style"
        }

def force_terminate(pid: int) -> Dict[str, Any]:
    """Force terminate a background process.
    
    Args:
        pid: Process ID to terminate
        
    Returns:
        Dict containing:
        - success: Whether termination was successful
        - error: Error message if any
    """
    with session_lock:
        if pid not in active_sessions:
            return {
                "success": False,
                "error": "Process not found"
            }
        
        try:
            session = active_sessions[pid]
            process = session["process"]
            
            # Try graceful termination first
            process.terminate()
            try:
                process.wait(timeout=3)  # Give it 3 seconds to terminate
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                process.kill()
                try:
                    process.wait(timeout=1)  # Give it 1 second to die
                except subprocess.TimeoutExpired:
                    # If still not dead, try to kill the entire process group
                    if sys.platform != "win32":
                        try:
                            os.killpg(os.getpgid(pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass  # Process already dead
                    return {
                        "success": False,
                        "error": "Process could not be terminated"
                    }
            
            # Clean up threads with timeouts
            if "stdout_thread" in session:
                try:
                    session["stdout_thread"].join(timeout=1)
                except Exception:
                    pass  # Ignore thread join errors
            if "stderr_thread" in session:
                try:
                    session["stderr_thread"].join(timeout=1)
                except Exception:
                    pass  # Ignore thread join errors
            
            # Clean up session
            del active_sessions[pid]
            update_active_sessions_metric()
            
            return {
                "success": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

def block_command(command: str) -> dict:
    """Add a command to the blacklist.

    Args:
        command (str): The command to block.

    Returns:
        dict: A dictionary containing:
            - success (bool): Whether the operation was successful.
            - error (str, optional): Error message if operation failed.
    """
    try:
        with session_lock:
            blacklisted_commands.add(command)
        return {"success": True}
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to block command: {str(e)}"
        }

def unblock_command(command: str) -> dict:
    """Remove a command from the blacklist.

    Args:
        command (str): The command to unblock.

    Returns:
        dict: A dictionary containing:
            - success (bool): Whether the operation was successful.
            - error (str, optional): Error message if operation failed.
    """
    try:
        with session_lock:
            blacklisted_commands.discard(command)
        return {"success": True}
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to unblock command: {str(e)}"
        }

def list_sessions() -> dict:
    """List all active command sessions.

    Returns:
        dict: A dictionary containing:
            - sessions (list): List of active sessions, each containing:
                - pid (int): Process ID
                - command (str): Command being executed
                - start_time (float): When the command started
                - runtime (float): How long the command has been running
            - error (str, optional): Error message if operation failed.
    """
    try:
        with session_lock:
            current_time = time.time()
            sessions = []
            for pid, session in active_sessions.items():
                process = session["process"]
                if process.poll() is None:  # Process is still running
                    sessions.append({
                        "pid": pid,
                        "command": session["command"],
                        "start_time": session["start_time"],
                        "runtime": current_time - session["start_time"]
                    })
                else:
                    # Process has completed, clean it up
                    process.communicate()  # Ensure all output is read
                    del active_sessions[pid]
                    active_sessions_counter.set(len(active_sessions))

            return {"sessions": sessions}
    except Exception as e:
        return {
            "sessions": [],
            "error": f"Failed to list sessions: {str(e)}"
        }

def main():
    # Set up the server
    import uvicorn
    print("Starting server from MAIN")
    uvicorn.run(mcp.app, host="0.0.0.0", port=8000)
    # Only run the SSE transport when the script is run directly

    mcp.run(transport="sse")

    # Initialize tools
    asyncio.run(add_metrics_to_tools())
    asyncio.run(add_tracing_to_tools())
    asyncio.run(add_profiling_to_tools())
    update_active_sessions_metric()

if __name__ == "__main__":
    main()

# mcp.run(transport="sse")

# --- File Operations ---
# Based on functions previously found (erroneously) in server/neodo.py

@mcp.tool()
def read_file(path: str, max_size_mb: float = 10) -> Dict[str, Any]:
    """Read contents of a file."""
    try:
        abs_path = os.path.abspath(path)
        if not is_path_safe(abs_path):
             return {"status": "error", "error": "Access denied to read this path"}
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > max_size_mb:
            return {"status": "error", "error": f"File size ({size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb}MB)"}
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"status": "success", "content": content, "size_bytes": len(content.encode('utf-8'))}
    except FileNotFoundError:
        return {"status": "error", "error": f"File not found: {path}"}
    except Exception as e:
        return {"status": "error", "error": f"Failed to read file: {str(e)}"}

@mcp.tool()
def write_file(path: str, content: str, create_dirs: bool = True) -> Dict[str, Any]:
    """Write content to a file."""
    try:
        abs_path = os.path.abspath(path)
        if not is_path_safe(abs_path):
             return {"status": "error", "error": "Access denied to write to this path"}
        if create_dirs:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "message": f"Content written to {path}", "size_bytes": len(content.encode('utf-8'))}
    except Exception as e:
        return {"status": "error", "error": f"Failed to write file: {str(e)}"}

@mcp.tool()
def create_directory(path: str) -> Dict[str, Any]:
    """Create a directory."""
    try:
        abs_path = os.path.abspath(path)
        if not is_path_safe(abs_path):
             return {"status": "error", "error": "Access denied to create directory at this path"}
        if os.path.exists(path):
             return {"status": "error", "error": f"Path already exists: {path}"}
        os.makedirs(path, exist_ok=True)
        return {"status": "success", "message": f"Directory created: {path}"}
    except Exception as e:
        return {"status": "error", "error": f"Failed to create directory: {str(e)}"}

@mcp.tool()
def list_directory(path: str, show_hidden: bool = False) -> Dict[str, Any]:
    """List contents of a directory."""
    try:
        abs_path = os.path.abspath(path)
        if not is_path_safe(abs_path):
             return {"status": "error", "error": "Access denied to list this directory"}
        contents = []
        for item in os.listdir(path):
            if not show_hidden and item.startswith('.'):
                continue
            item_path = os.path.join(path, item)
            item_info = {"name": item, "path": item_path}
            try:
                stat_info = os.stat(item_path)
                if os.path.isdir(item_path):
                    item_info["type"] = "directory"
                else:
                    item_info["type"] = "file"
                    item_info["size"] = stat_info.st_size
                item_info["modified"] = stat_info.st_mtime
            except OSError:
                item_info["type"] = "unknown"
            contents.append(item_info)
        return {"status": "success", "contents": contents}
    except FileNotFoundError:
        return {"status": "error", "error": f"Directory not found: {path}"}
    except NotADirectoryError:
        return {"status": "error", "error": f"Path is not a directory: {path}"}
    except Exception as e:
        return {"status": "error", "error": f"Failed to list directory: {str(e)}"}

@mcp.tool()
def move_file(source: str, destination: str) -> Dict[str, Any]:
    """Move or rename a file or directory."""
    try:
        abs_source = os.path.abspath(source)
        abs_dest = os.path.abspath(destination)
        if not is_path_safe(abs_source) or not is_path_safe(abs_dest):
             return {"status": "error", "error": "Access denied for source or destination path"}
        shutil.move(source, destination)
        return {"status": "success", "message": f"Moved {source} to {destination}"}
    except FileNotFoundError:
        return {"status": "error", "error": f"Source path not found: {source}"}
    except Exception as e:
        return {"status": "error", "error": f"Failed to move file: {str(e)}"}

@mcp.tool()
def search_files(directory: str, pattern: str, recursive: bool = False, max_results: int = 100) -> Dict[str, Any]:
    """Search for files matching a pattern."""
    try:
        abs_dir = os.path.abspath(directory)
        if not is_path_safe(abs_dir):
            return {"status": "error", "error": "Access denied to search this directory"}
        matches = []
        search_pattern = os.path.join(directory, pattern)
        if recursive:
            for root, _, files in os.walk(directory):
                 if not is_path_safe(os.path.abspath(root)):
                     continue 
                 for filename in glob.glob(os.path.join(root, pattern)): 
                    if len(matches) >= max_results:
                        break
                    matches.append(filename)
                 if len(matches) >= max_results:
                     break
        else:
            for filename in glob.glob(search_pattern):
                if len(matches) >= max_results:
                    break
                matches.append(filename)
        return {"status": "success", "matches": matches[:max_results]}
    except Exception as e:
        return {"status": "error", "error": f"Failed to search files: {str(e)}"}

@mcp.tool()
def get_file_info(path: str) -> Dict[str, Any]:
    """Get detailed information about a file or directory."""
    info = {"exists": False}
    try:
        abs_path = os.path.abspath(path)
        if not is_path_safe(abs_path):
             return {"status": "error", "error": "Access denied to access this path"}
        if not os.path.exists(path):
            return {"status": "success", "exists": False}
        stat_info = os.stat(path)
        info = {
            "path": path,
            "name": os.path.basename(path),
            "type": "directory" if os.path.isdir(path) else "file",
            "size": stat_info.st_size,
            "created": stat_info.st_ctime,
            "modified": stat_info.st_mtime,
            "accessed": stat_info.st_atime,
            "permissions": stat.filemode(stat_info.st_mode),
            "exists": True
        }
        return {"status": "success", **info}
    except Exception as e:
        return {"status": "error", "error": f"Failed to get file info: {str(e)}", **info}

# --- End File Operations ---

@mcp.tool()
def monitor_performance(duration: int = 60, interval: float = 1.0) -> Dict[str, Any]:
    """
    Monitor system performance metrics
    
    Args:
        duration: Monitoring duration in seconds
        interval: Sampling interval in seconds
    
    Returns:
        Dictionary with performance metrics
    """
    try:
        import psutil
        from datetime import datetime, timedelta
        
        metrics = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'network': []
        }
        
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration)
        
        while datetime.now() < end_time:
            # CPU metrics
            metrics['cpu'].append({
                'timestamp': datetime.now().isoformat(),
                'percent': psutil.cpu_percent(interval=0.1),
                'count': psutil.cpu_count(),
                'freq': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            })
            
            # Memory metrics
            mem = psutil.virtual_memory()
            metrics['memory'].append({
                'timestamp': datetime.now().isoformat(),
                'total': mem.total,
                'available': mem.available,
                'percent': mem.percent,
                'used': mem.used,
                'free': mem.free
            })
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics['disk'].append({
                'timestamp': datetime.now().isoformat(),
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            })
            
            # Network metrics
            net = psutil.net_io_counters()
            metrics['network'].append({
                'timestamp': datetime.now().isoformat(),
                'bytes_sent': net.bytes_sent,
                'bytes_recv': net.bytes_recv,
                'packets_sent': net.packets_sent,
                'packets_recv': net.packets_recv
            })
            
            time.sleep(interval)
        
        # Calculate summary statistics
        summary = {
            'cpu': {
                'avg': sum(m['percent'] for m in metrics['cpu']) / len(metrics['cpu']) if metrics['cpu'] else 0,
                'max': max(m['percent'] for m in metrics['cpu']) if metrics['cpu'] else 0,
                'min': min(m['percent'] for m in metrics['cpu']) if metrics['cpu'] else 0
            },
            'memory': {
                'avg_percent': sum(m['percent'] for m in metrics['memory']) / len(metrics['memory']) if metrics['memory'] else 0,
                'max_percent': max(m['percent'] for m in metrics['memory']) if metrics['memory'] else 0,
                'min_percent': min(m['percent'] for m in metrics['memory']) if metrics['memory'] else 0
            },
            'disk': {
                'start_percent': metrics['disk'][0]['percent'] if metrics['disk'] else 0,
                'end_percent': metrics['disk'][-1]['percent'] if metrics['disk'] else 0
            },
            'network': {
                'total_sent': metrics['network'][-1]['bytes_sent'] - metrics['network'][0]['bytes_sent'] if len(metrics['network']) > 1 else 0,
                'total_recv': metrics['network'][-1]['bytes_recv'] - metrics['network'][0]['bytes_recv'] if len(metrics['network']) > 1 else 0
            }
        }
        
        return {
            'status': 'success',
            'summary': summary,
            'raw_metrics': metrics
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }