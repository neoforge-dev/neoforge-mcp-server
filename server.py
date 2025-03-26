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
from langchain.chains.llm import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.llms import HuggingFacePipeline
from langchain_community.llms import OpenAI
from langchain_community.llms import Anthropic
from transformers import pipeline
import torch
import psutil
from opentelemetry.sdk.metrics._internal.measurement import Measurement
import asyncio
import anthropic
import openai
from transformers import pipeline
import metrics
import yaml

# Initialize the MCP server
mcp = FastMCP("Terminal Command Runner MCP", port=7443, log_level="DEBUG")

# Global variables for process management
session_lock = threading.Lock()
active_sessions = {}
blacklisted_commands = set(['rm -rf /', 'mkfs'])
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

def is_command_safe(cmd: str) -> bool:
    """Check if a command is safe to execute"""
    if not cmd.strip():
        return False
    for blocked in blacklisted_commands:
        if blocked in cmd:
            return False
    return True

# Terminal Tools

def execute_command(command: str, timeout: int = 10, allow_background: bool = True) -> dict:
    """Execute a command with timeout and output capture."""
    if not command or not isinstance(command, str):
        return {
            "status": "error",
            "error": "Invalid command",
            "pid": None,
            "exit_code": 1,
            "stdout": "",
            "stderr": "Invalid command provided"
        }

    if not is_command_safe(command):
        return {
            "status": "error",
            "error": "Command blocked",
            "pid": None,
            "exit_code": 1,
            "stdout": "",
            "stderr": "Command was blocked for security reasons"
        }

    try:
        # Split command into args while preserving quoted strings
        args = shlex.split(command)
        
        # Create output queues
        stdout_queue = queue.Queue()
        stderr_queue = queue.Queue()
        
        # Start process
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        pid = process.pid
        
        # Create reader thread event for signaling
        stop_event = threading.Event()
        
        def reader_thread():
            """Thread to read process output."""
            try:
                while not stop_event.is_set():
                    # Read with timeout to allow checking stop_event
                    stdout_line = process.stdout.readline()
                    if stdout_line:
                        stdout_queue.put(stdout_line)
                    
                    stderr_line = process.stderr.readline()
                    if stderr_line:
                        stderr_queue.put(stderr_line)
                    
                    # Check if process has finished
                    if process.poll() is not None:
                        break
                    
                    time.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                stderr_queue.put(f"Error reading output: {str(e)}")
            finally:
                # Ensure remaining output is read
                for line in process.stdout:
                    stdout_queue.put(line)
                for line in process.stderr:
                    stderr_queue.put(line)
        
        # Start reader thread
        reader = threading.Thread(target=reader_thread)
        reader.daemon = True
        reader.start()
        
        # Store session info
        with session_lock:
            active_sessions[pid] = {
                "process": process,
                "command": command,
                "start_time": time.time(),
                "stdout_queue": stdout_queue,
                "stderr_queue": stderr_queue,
                "reader_thread": reader,
                "stop_event": stop_event
            }
            update_active_sessions_metric()
        
        # Wait for timeout
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if not allow_background:
                # Clean up if background not allowed
                stop_event.set()
                process.terminate()
                try:
                    process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                with session_lock:
                    if pid in active_sessions:
                        del active_sessions[pid]
                        update_active_sessions_metric()
                
                return {
                    "status": "error",
                    "error": "Command timed out",
                    "pid": None,
                    "runtime": timeout,
                    "exit_code": None,
                    "stdout": "".join(read_queue_contents(stdout_queue)),
                    "stderr": "".join(read_queue_contents(stderr_queue))
                }
        
        # Process completed within timeout
        if process.returncode is not None:
            stop_event.set()
            reader.join(timeout=1)
            
            with session_lock:
                if pid in active_sessions:
                    del active_sessions[pid]
                    update_active_sessions_metric()
            
            return {
                "status": "success" if process.returncode == 0 else "error",
                "pid": None,
                "runtime": time.time() - active_sessions[pid]["start_time"],
                "exit_code": process.returncode,
                "stdout": "".join(read_queue_contents(stdout_queue)),
                "stderr": "".join(read_queue_contents(stderr_queue)),
                "complete": True
            }
        
        # Process is running in background
        return {
            "status": "running",
            "pid": pid,
            "runtime": time.time() - active_sessions[pid]["start_time"],
            "exit_code": None,
            "stdout": "".join(read_queue_contents(stdout_queue)),
            "stderr": "".join(read_queue_contents(stderr_queue)),
            "complete": False
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "pid": None,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(e)
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

@mcp.tool()
def read_output(pid: int) -> Dict[str, Any]:
    """Read output from a running command session."""
    try:
        with session_lock:
            if pid not in active_sessions:
                return {
                    "status": "error",
                    "error": f"No active session for PID {pid}",
                    "pid": None,
                    "stdout": "",
                    "stderr": f"No active session found for PID {pid}",
                    "complete": True
                }
            
            session = active_sessions[pid]
            process = session["process"]
            stdout_queue = session["stdout_queue"]
            stderr_queue = session["stderr_queue"]
        
        # Read available output
        stdout = "".join(read_queue_contents(stdout_queue))
        stderr = "".join(read_queue_contents(stderr_queue))
        
        # Check if process has completed
        returncode = process.poll()
        if returncode is not None:
            # Process finished, clean up
            session["stop_event"].set()
            session["reader_thread"].join(timeout=1)
            
            with session_lock:
                if pid in active_sessions:
                    del active_sessions[pid]
                    update_active_sessions_metric()
            
            return {
                "status": "success" if returncode == 0 else "error",
                "pid": None,
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": returncode,
                "complete": True
            }
        
        # Process still running
        return {
            "status": "running",
            "pid": pid,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": None,
            "complete": False
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "pid": None,
            "stdout": "",
            "stderr": str(e),
            "complete": True
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
                cmd = ['git', 'branch', '-d', parameters['name']]
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
def filter_output(content: str, max_lines: int = 50, important_patterns: List[str] = None) -> Dict[str, Any]:
    """
    Process and format long command outputs for better LLM consumption
    
    Args:
        content: The text content to filter
        max_lines: Maximum number of lines to include
        important_patterns: List of regex patterns to always include
    
    Returns:
        Dictionary with filtered content
    """
    try:
        lines = content.split('\n')
        total_lines = len(lines)
        
        if not important_patterns:
            important_patterns = [
                r'error', r'warning', r'fail', r'exception',
                r'success', r'completed', r'starting', r'finished'
            ]
        
        # Always keep lines matching important patterns
        important_lines = []
        other_lines = []
        
        for line in lines:
            if any(re.search(pattern, line, re.IGNORECASE) for pattern in important_patterns):
                important_lines.append(line)
            else:
                other_lines.append(line)
        
        # Calculate remaining space for other lines
        remaining_space = max_lines - len(important_lines)
        
        if remaining_space <= 0:
            filtered_lines = important_lines[:max_lines]
        else:
            # Select a representative sample of other lines
            step = len(other_lines) // remaining_space if remaining_space > 0 else 1
            sampled_lines = other_lines[::step][:remaining_space]
            filtered_lines = important_lines + sampled_lines
        
        return {
            'filtered_content': '\n'.join(filtered_lines),
            'total_lines': total_lines,
            'included_lines': len(filtered_lines),
            'important_lines': len(important_lines),
            'truncated': total_lines > len(filtered_lines)
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def context_length(text: str) -> Dict[str, Any]:
    """
    Track LLM context usage
    
    Args:
        text: Text to analyze for context length
    
    Returns:
        Dictionary with context length metrics
    """
    try:
        # Simple tokenization (this is a basic approximation)
        words = text.split()
        characters = len(text)
        lines = text.count('\n') + 1
        
        # Rough token estimation (OpenAI GPT-style)
        # This is a very rough approximation - actual tokenization is more complex
        estimated_tokens = len(words) * 1.3
        
        # Context length limits (example values)
        limits = {
            'claude-3-opus': 200000,
            'claude-3-sonnet': 100000,
            'gpt-4': 128000,
            'gpt-3.5': 16000
        }
        
        # Calculate percentage of context used
        usage = {model: (estimated_tokens / limit) * 100 for model, limit in limits.items()}
        
        return {
            'estimated_tokens': int(estimated_tokens),
            'words': len(words),
            'characters': characters,
            'lines': lines,
            'context_usage_percent': usage,
            'approaching_limit': any(pct > 75 for pct in usage.values())
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def analyze_codebase(path: str = ".", analysis_type: str = "all") -> Dict[str, Any]:
    """
    Advanced codebase analysis tool
    
    Args:
        path: Path to analyze
        analysis_type: Type of analysis ('complexity', 'dependencies', 'security', 'all')
    
    Returns:
        Dictionary with analysis results
    """
    try:
        results = {
            'metrics': {},
            'dependencies': {},
            'security_issues': [],
            'complexity_hotspots': []
        }
        
        # Get all Python files
        python_files = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        if analysis_type in ('all', 'complexity'):
            # Analyze code complexity
            for file_path in python_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                # Calculate complexity metrics
                complexity = _calculate_complexity(content)
                if complexity['score'] > 15:
                    results['complexity_hotspots'].append({
                        'file': file_path,
                        'complexity': complexity
                    })
                results['metrics'][file_path] = complexity
        
        if analysis_type in ('all', 'dependencies'):
            # Analyze dependencies
            import_pattern = re.compile(r'^(?:from|import)\s+([\w\.]+)', re.MULTILINE)
            for file_path in python_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                imports = import_pattern.findall(content)
                results['dependencies'][file_path] = list(set(imports))
        
        if analysis_type in ('all', 'security'):
            # Security analysis
            security_patterns = {
                'hardcoded_secret': (r'(?i)(?:password|secret|key|token)\s*=\s*[\'"][^\'"]+[\'"]', 'high'),
                'sql_injection': (r'(?i)(?:execute|executemany)\s*\([^)]*\%[^)]*\)', 'high'),
                'command_injection': (r'(?i)(?:os\.system|subprocess\.(?:call|Popen|run))\s*\([^)]*\%[^)]*\)', 'high'),
                'unsafe_yaml': (r'(?i)yaml\.load\(', 'medium'),
                'pickle_usage': (r'(?i)pickle\.loads?\(', 'medium')
            }
            
            for file_path in python_files:
                with open(file_path, 'r') as f:
                    content = f.read()
                    
                for issue_type, (pattern, severity) in security_patterns.items():
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        line_no = content[:match.start()].count('\n') + 1
                        results['security_issues'].append({
                            'file': file_path,
                            'line': line_no,
                            'type': issue_type,
                            'severity': severity,
                            'context': match.group(0)
                        })
        
        return {
            'status': 'success',
            'results': results
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _calculate_complexity(content: str) -> Dict[str, Any]:
    """Helper function to calculate code complexity metrics"""
    complexity = {
        'score': 1,
        'functions': 0,
        'classes': 0,
        'branches': 0,
        'loops': 0,
        'cognitive_score': 0
    }
    
    # Count basic structures
    complexity['functions'] = len(re.findall(r'^\s*def\s+', content, re.MULTILINE))
    complexity['classes'] = len(re.findall(r'^\s*class\s+', content, re.MULTILINE))
    
    # Count control flow structures
    control_patterns = {
        'if': r'\bif\s+',
        'elif': r'\belif\s+',
        'else': r'\belse\s*:',
        'for': r'\bfor\s+',
        'while': r'\bwhile\s+',
        'try': r'\btry\s*:',
        'except': r'\bexcept\s*',
        'with': r'\bwith\s+'
    }
    
    for pattern in control_patterns.values():
        count = len(re.findall(pattern, content))
        complexity['branches'] += count
        complexity['cognitive_score'] += count
    
    # Calculate overall complexity score
    complexity['score'] = (
        complexity['cognitive_score'] +
        complexity['functions'] * 1.5 +
        complexity['classes'] * 2 +
        complexity['branches'] * 0.5
    )
    
    return complexity

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
                'avg': sum(m['percent'] for m in metrics['cpu']) / len(metrics['cpu']),
                'max': max(m['percent'] for m in metrics['cpu']),
                'min': min(m['percent'] for m in metrics['cpu'])
            },
            'memory': {
                'avg_percent': sum(m['percent'] for m in metrics['memory']) / len(metrics['memory']),
                'max_percent': max(m['percent'] for m in metrics['memory']),
                'min_available': min(m['available'] for m in metrics['memory'])
            },
            'disk': {
                'avg_percent': sum(m['percent'] for m in metrics['disk']) / len(metrics['disk']),
                'available': metrics['disk'][-1]['free']
            },
            'network': {
                'total_sent': metrics['network'][-1]['bytes_sent'] - metrics['network'][0]['bytes_sent'],
                'total_recv': metrics['network'][-1]['bytes_recv'] - metrics['network'][0]['bytes_recv']
            }
        }
        
        return {
            'status': 'success',
            'metrics': metrics,
            'summary': summary,
            'duration': duration,
            'samples': len(metrics['cpu'])
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def manage_llm_context(content: str, model: str = "claude-3-sonnet", max_tokens: int = None) -> Dict[str, Any]:
    """
    Advanced LLM context management and optimization
    
    Args:
        content: Text content to analyze and optimize
        model: Target LLM model
        max_tokens: Maximum desired tokens (defaults to model limit)
    
    Returns:
        Dictionary with context management results
    """
    try:
        # Model context limits
        model_limits = {
            'claude-3-opus': 200000,
            'claude-3-sonnet': 100000,
            'gpt-4': 128000,
            'gpt-3.5': 16000
        }
        
        if model not in model_limits:
            return {
                'status': 'error',
                'error': f'Unknown model: {model}'
            }
        
        # Use specified max_tokens or model limit
        token_limit = max_tokens or model_limits[model]
        
        # Analyze content
        words = content.split()
        chars = len(content)
        lines = content.count('\n') + 1
        
        # Estimate tokens (improved estimation)
        estimated_tokens = int(len(words) * 1.3)  # Rough approximation
        
        # Calculate context metrics
        metrics = {
            'estimated_tokens': estimated_tokens,
            'words': len(words),
            'characters': chars,
            'lines': lines,
            'usage_percent': (estimated_tokens / token_limit) * 100
        }
        
        # Generate optimization suggestions
        suggestions = []
        if estimated_tokens > token_limit:
            suggestions.append({
                'type': 'truncation',
                'message': f'Content exceeds {model} token limit by approximately {estimated_tokens - token_limit} tokens'
            })
            
            # Suggest specific optimizations
            if lines > 100:
                suggestions.append({
                    'type': 'structure',
                    'message': 'Consider reducing line count by combining related lines'
                })
            
            code_blocks = len(re.findall(r'```.*?```', content, re.DOTALL))
            if code_blocks > 5:
                suggestions.append({
                    'type': 'code',
                    'message': 'Consider reducing number of code blocks or showing only relevant portions'
                })
        
        # Optimize content if needed
        optimized_content = content
        if estimated_tokens > token_limit:
            optimized_content = _optimize_content(content, token_limit)
        
        return {
            'status': 'success',
            'metrics': metrics,
            'suggestions': suggestions,
            'optimized_content': optimized_content if optimized_content != content else None,
            'model': model,
            'token_limit': token_limit
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _optimize_content(content: str, token_limit: int) -> str:
    """Helper function to optimize content for token limit"""
    # Split content into sections
    sections = re.split(r'\n\s*\n', content)
    
    # Calculate approximate tokens per section
    section_tokens = [(s, int(len(s.split()) * 1.3)) for s in sections]
    
    # Sort sections by importance (keeping code blocks and error messages)
    def section_importance(section_tuple):
        section, _ = section_tuple
        if re.match(r'```.*?```', section, re.DOTALL):
            return 3  # Highest priority for code blocks
        if re.search(r'error|exception|warning|fail', section, re.IGNORECASE):
            return 2  # High priority for errors/warnings
        return 1  # Normal priority
    
    section_tokens.sort(key=section_importance, reverse=True)
    
    # Rebuild content within token limit
    optimized_sections = []
    current_tokens = 0
    
    for section, tokens in section_tokens:
        if current_tokens + tokens <= token_limit:
            optimized_sections.append(section)
            current_tokens += tokens
        elif tokens > 100:  # For large sections, try to keep important parts
            # Keep first and last few lines
            lines = section.split('\n')
            if len(lines) > 6:
                truncated = '\n'.join(lines[:3] + ['...'] + lines[-3:])
                truncated_tokens = int(len(truncated.split()) * 1.3)
                if current_tokens + truncated_tokens <= token_limit:
                    optimized_sections.append(truncated)
                    current_tokens += truncated_tokens
    
    return '\n\n'.join(optimized_sections)

@mcp.tool()
def enhanced_testing(test_type: str = "unit", coverage: bool = True, parallel: bool = True) -> Dict[str, Any]:
    """
    Enhanced testing support with coverage and parallel execution
    
    Args:
        test_type: Type of tests to run ("unit", "integration", "all")
        coverage: Whether to collect coverage data
        parallel: Whether to run tests in parallel
    
    Returns:
        Dictionary with test results and coverage data
    """
    try:
        cmd = ['pytest']
        
        # Add test selection based on type
        if test_type == "unit":
            cmd.extend(['-m', 'unit'])
        elif test_type == "integration":
            cmd.extend(['-m', 'integration'])
        
        # Add coverage if requested
        if coverage:
            cmd.extend(['--cov=.', '--cov-report=term-missing'])
        
        # Add parallel execution if requested
        if parallel:
            cmd.extend(['-n', 'auto'])
        
        # Add output capture and verbosity
        cmd.extend(['-v', '--capture=no'])
        
        # Run tests
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Parse test results
        test_results = _parse_test_output(result.stdout)
        
        # Parse coverage data if collected
        coverage_data = None
        if coverage and result.returncode == 0:
            coverage_data = _parse_coverage_output(result.stdout)
        
        return {
            'status': 'success' if result.returncode == 0 else 'failure',
            'test_results': test_results,
            'coverage': coverage_data,
            'exit_code': result.returncode,
            'errors': result.stderr if result.stderr else None
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

def _parse_test_output(output: str) -> Dict[str, Any]:
    """Helper function to parse pytest output"""
    results = {
        'passed': [],
        'failed': [],
        'skipped': [],
        'warnings': [],
        'summary': {}
    }
    
    for line in output.split('\n'):
        if line.startswith('test_'):
            if 'PASSED' in line:
                results['passed'].append(line)
            elif 'FAILED' in line:
                results['failed'].append(line)
            elif 'SKIPPED' in line:
                results['skipped'].append(line)
        elif 'warning' in line.lower():
            results['warnings'].append(line)
        elif '===' in line and ('failed' in line or 'passed' in line):
            results['summary']['final'] = line.strip()
    
    # Calculate statistics
    results['summary']['total'] = len(results['passed']) + len(results['failed']) + len(results['skipped'])
    results['summary']['pass_rate'] = (len(results['passed']) / results['summary']['total'] * 100) if results['summary']['total'] > 0 else 0
    
    return results

def _parse_coverage_output(output: str) -> Dict[str, Any]:
    """Helper function to parse coverage output"""
    coverage_data = {
        'total': 0,
        'covered': 0,
        'missing': 0,
        'files': {}
    }
    
    coverage_section = False
    for line in output.split('\n'):
        if '---------- coverage:' in line:
            coverage_section = True
            continue
        
        if coverage_section and line.strip():
            if line.startswith('TOTAL'):
                parts = line.split()
                try:
                    coverage_data['total'] = int(parts[1])
                    coverage_data['covered'] = int(parts[2])
                    coverage_data['missing'] = int(parts[3])
                except (IndexError, ValueError):
                    pass
            elif '.py' in line:
                parts = line.split()
                try:
                    file_name = parts[0]
                    coverage_data['files'][file_name] = {
                        'statements': int(parts[1]),
                        'missing': int(parts[2]),
                        'coverage': int(parts[3].rstrip('%'))
                    }
                except (IndexError, ValueError):
                    pass
    
    return coverage_data

class MCPProfiler:
    """Profiler for MCP tools and operations"""
    
    def __init__(self):
        self.profiler = cProfile.Profile()
        self.active = False
        self.stats = None
        self.output_file = None
    
    def start(self, output_file: Optional[str] = None):
        """Start profiling"""
        if output_file:
            self.output_file = output_file
        self.active = True
        self.profiler.enable()
    
    def stop(self) -> Optional[str]:
        """Stop profiling and return stats"""
        if not self.active:
            return None
            
        self.profiler.disable()
        self.active = False
        
        # Create stats object
        s = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=s)
        stats.sort_stats('cumulative')
        stats.print_stats()
        
        # Save to file if specified
        if self.output_file:
            stats.dump_stats(self.output_file)
            
        return s.getvalue()
    
    def reset(self):
        """Reset the profiler"""
        self.profiler = cProfile.Profile()
        self.active = False
        self.stats = None

# Initialize global profiler
mcp_profiler = MCPProfiler()

def profile_tool(func):
    """Decorator to add profiling to MCP tools"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if mcp_profiler.active:
            return func(*args, **kwargs)
        
        # Create temporary file for stats
        with tempfile.NamedTemporaryFile(suffix='.prof', delete=False) as tmp:
            mcp_profiler.start(tmp.name)
            try:
                result = func(*args, **kwargs)
                stats = mcp_profiler.stop()
                
                # Add profiling info to result if it's a dict
                if isinstance(result, dict):
                    result['profiling'] = {
                        'stats': stats,
                        'stats_file': tmp.name
                    }
                return result
            except Exception as e:
                mcp_profiler.stop()
                os.unlink(tmp.name)
                raise
            finally:
                mcp_profiler.reset()
    return wrapper

@mcp.tool()
def start_profiling() -> Dict[str, Any]:
    """
    Start profiling MCP tools
    
    Returns:
        Dictionary with profiling status
    """
    try:
        mcp_profiler.start()
        return {
            'status': 'success',
            'message': 'Profiling started'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def stop_profiling() -> Dict[str, Any]:
    """
    Stop profiling and get results
    
    Returns:
        Dictionary with profiling results
    """
    try:
        stats = mcp_profiler.stop()
        if stats:
            return {
                'status': 'success',
                'stats': stats
            }
        else:
            return {
                'status': 'error',
                'message': 'No active profiling session'
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def get_profiling_stats(stats_file: str) -> Dict[str, Any]:
    """
    Get profiling statistics from a stats file
    
    Args:
        stats_file: Path to the stats file
        
    Returns:
        Dictionary with profiling statistics
    """
    try:
        if not os.path.exists(stats_file):
            return {
                'status': 'error',
                'error': f'Stats file not found: {stats_file}'
            }
            
        stats = pstats.Stats(stats_file)
        s = io.StringIO()
        stats.sort_stats('cumulative')
        stats.print_stats()
        
        return {
            'status': 'success',
            'stats': s.getvalue()
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def profile_code(code: str, globals_dict: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Profile a piece of Python code
    
    Args:
        code: Python code to profile
        globals_dict: Optional globals dictionary
        
    Returns:
        Dictionary with profiling results
    """
    try:
        # Create temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp.flush()
            
            # Create temporary file for stats
            with tempfile.NamedTemporaryFile(suffix='.prof', delete=False) as stats_tmp:
                # Profile the code execution
                profiler = cProfile.Profile()
                if globals_dict is None:
                    globals_dict = {}
                profiler.runctx(code, globals_dict, {}, stats_tmp.name)
                
                # Get stats
                stats = pstats.Stats(profiler)
                s = io.StringIO()
                stats.sort_stats('cumulative')
                stats.print_stats()
                
                return {
                    'status': 'success',
                    'stats': s.getvalue(),
                    'stats_file': stats_tmp.name,
                    'code_file': tmp.name
                }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }

@mcp.tool()
def generate_code(prompt: str, model: str = "claude-3-sonnet", context: Optional[Dict[str, Any]] = None, system_prompt: Optional[str] = None) -> Dict[str, Any]:
    """Generate code using various models."""
    try:
        if not prompt:
            return {
                "status": "error",
                "error": "Empty prompt provided",
                "language": "python"
            }
        
        # Get workspace info
        workspace_info = _get_workspace_info()
        
        # Prepare context
        full_context = {
            "workspace": workspace_info,
            **(context or {})
        }
        
        # Get system prompt
        if system_prompt is None:
            system_prompt = _get_default_system_prompt("python")
        
        # Generate code based on model type
        if model in ["claude-3-sonnet", "claude-3-opus"]:
            result = _generate_with_api_model(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=None,
                temperature=0.7
            )
        elif model in ["gpt-4", "gpt-3.5-turbo"]:
            result = _generate_with_api_model(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=None,
                temperature=0.7
            )
        elif model in ["code-llama", "starcoder"]:
            result = _generate_with_local_model(
                prompt=prompt,
                model=model,
                system_prompt=system_prompt,
                max_tokens=None,
                temperature=0.7
            )
        else:
            return {
                "status": "error",
                "error": f"Invalid model: {model}",
                "language": "python"
            }
        
        if result["status"] == "success":
            # Track metrics
            _track_generation_metrics(
                model=model,
                language="python",
                tokens_used=result.get("tokens_used", 0),
                success=True
            )
            
            # Add context to result
            result["context"] = full_context
        
        return result
        
    except Exception as e:
        _track_generation_metrics(
            model=model,
            language="python",
            tokens_used=0,
            success=False
        )
        return {
            "status": "error",
            "error": str(e),
            "language": "python"
        }

def _generate_with_api_model(
    prompt: str,
    model: str,
    system_prompt: str,
    max_tokens: Optional[int] = None,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """Generate code using API-based models (Claude or GPT)."""
    try:
        start_time = time.time()
        
        if model in ["claude-3-sonnet", "claude-3-opus"]:
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens or 1000,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return {
                "status": "success",
                "code": str(response.content),  # Convert to string to handle mock response
                "tokens_used": response.usage.total_tokens,
                "generation_time": time.time() - start_time
            }
            
        elif model in ["gpt-4", "gpt-3.5-turbo"]:
            response = openai.ChatCompletion.create(
                model=model,
                max_tokens=max_tokens or 1000,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return {
                "status": "success",
                "code": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "generation_time": time.time() - start_time
            }
            
        else:
            return {
                "status": "error",
                "error": f"Unsupported API model: {model}",
                "language": "python"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "language": "python"
        }

def _generate_with_local_model(
    prompt: str,
    model: str,
    system_prompt: str,
    max_tokens: Optional[int] = None,
    temperature: float = 0.7
) -> Dict[str, Any]:
    """Generate code using local models."""
    try:
        start_time = time.time()
        config = _get_local_model_config(model)
        
        # Initialize pipeline
        pipe = pipeline(
            "text-generation",
            model=config["model"],
            device=config.get("device", "cpu")
        )
        
        # Combine prompts
        full_prompt = f"{system_prompt}\n\n{prompt}"
        
        # Generate code
        response = pipe(
            full_prompt,
            max_length=max_tokens or 1000,
            temperature=temperature,
            num_return_sequences=1
        )
        
        # Handle both function and list responses from the mock
        if callable(response):
            response = response(
                full_prompt,
                max_length=max_tokens or 1000,
                temperature=temperature,
                num_return_sequences=1
            )
        
        if isinstance(response, list) and response:
            generated_text = response[0]["generated_text"]
        elif isinstance(response, dict):
            generated_text = response["generated_text"]
        else:
            return {
                "status": "error",
                "error": "Invalid response format",
                "language": "python"
            }
            
        return {
            "status": "success",
            "code": generated_text,
            "tokens_used": len(generated_text.split()),  # Approximate token count
            "generation_time": time.time() - start_time
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "language": "python"
        }

def _get_local_model_config(model: str) -> Dict[str, Any]:
    """Get configuration for local models."""
    configs = {
        "code-llama": {
            "model_name": "codellama/CodeLlama-34b-Python",
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        },
        "starcoder": {
            "model_name": "bigcode/starcoder",
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
    }
    
    if model not in configs:
        raise ValueError(f"Unknown model: {model}")
    
    return configs[model]

def validate_code_quality(code: str, checks: Optional[List[str]] = None) -> Dict[str, Any]:
    """Validate code quality with various checks."""
    if not code:
        return {
            "status": "error",
            "error": "No code provided",
            "language": "python"
        }
        
    if checks is None:
        checks = ["syntax", "complexity", "security", "performance", "style"]
        
    results = {}
    overall_status = "success"
    
    try:
        # Parse code
        tree = ast.parse(code)
        
        # Syntax check
        results["syntax"] = {
            "status": "success",
            "message": "Code is syntactically correct"
        }
        
        # Run requested checks
        if "complexity" in checks:
            try:
                complexity_result = _analyze_complexity(tree)
                results["complexity"] = complexity_result
                results["complexity"]["complexity_score"] = complexity_result["score"]  # For backward compatibility
                if complexity_result["status"] != "success":
                    overall_status = complexity_result["status"]
            except Exception as e:
                results["complexity"] = {
                    "status": "error",
                    "error": str(e),
                    "message": "Failed to analyze complexity"
                }
                overall_status = "error"
                
        if "security" in checks:
            try:
                security_result = _analyze_security(tree)
                results["security"] = security_result
                if security_result["status"] != "success":
                    overall_status = "warning"
            except Exception as e:
                results["security"] = {
                    "status": "error",
                    "error": str(e),
                    "message": "Failed to analyze security"
                }
                overall_status = "error"
                
        if "performance" in checks:
            try:
                performance_result = _analyze_performance(tree)
                results["performance"] = performance_result
                if performance_result["status"] != "success":
                    overall_status = "warning"
            except Exception as e:
                results["performance"] = {
                    "status": "error",
                    "error": str(e),
                    "message": "Failed to analyze performance"
                }
                overall_status = "error"
                
        if "style" in checks:
            try:
                style_result = _analyze_style(code)
                results["style"] = style_result
                if style_result["status"] != "success":
                    overall_status = "warning"
            except Exception as e:
                results["style"] = {
                    "status": "error",
                    "error": str(e),
                    "message": "Failed to analyze style"
                }
                overall_status = "error"
                
    except SyntaxError as e:
        return {
            "status": "error",
            "results": {
                "syntax": {
                    "status": "error",
                    "error": str(e),
                    "message": "Syntax error detected"
                }
            },
            "language": "python",
            "summary": "❌ Syntax error"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "language": "python"
        }
        
    # Generate summary
    summary = []
    for check, result in results.items():
        icon = "✅" if result["status"] == "success" else "⚠️" if result["status"] == "warning" else "❌"
        message = result.get("message", result.get("error", "Check completed"))
        summary.append(f"{icon} {check.title()}: {message}")
        
    return {
        "status": overall_status,
        "results": results,
        "language": "python",
        "summary": "\n".join(summary)
    }

def _get_workspace_info() -> Dict[str, Any]:
    """Get current workspace context"""
    try:
        workspace = WorkspaceManager.get_active_workspace()
        return {
            'workspace_id': workspace.id,
            'tools': workspace.get_tools(),
            'environment': workspace.get_environment(),
            'dependencies': workspace.get_dependencies()
        }
    except Exception:
        return {}

def _get_default_system_prompt(language: str) -> str:
    """Get default system prompt for code generation"""
    return f"""You are an expert {language} developer. Generate clean, efficient, and well-documented code.
Follow these principles:
1. Write clear, maintainable code
2. Include proper error handling
3. Add comprehensive documentation
4. Follow language best practices
5. Consider performance implications
"""

def _track_generation_metrics(
    model: str,
    language: str,
    tokens_used: int,
    success: bool
) -> None:
    """Track code generation metrics"""
    try:
        metrics = {
            'code_generation_requests': Counter(),
            'tokens_used': Histogram(),
            'generation_success': Counter(),
        }
        
        metrics['code_generation_requests'].add(
            1,
            {'model': model, 'language': language}
        )
        
        metrics['tokens_used'].record(
            tokens_used,
            {'model': model, 'language': language}
        )
        
        if success:
            metrics['generation_success'].add(
                1,
                {'model': model, 'language': language}
            )
    except Exception:
        pass  # Fail silently for metrics

def _analyze_complexity(node: ast.AST) -> Dict[str, Any]:
    """Analyze code complexity using AST."""
    complexity = 0
    issues = []
    
    class ComplexityVisitor(ast.NodeVisitor):
        def visit_If(self, node):
            nonlocal complexity
            complexity += 1
            self.generic_visit(node)
            
        def visit_For(self, node):
            nonlocal complexity
            complexity += 1
            self.generic_visit(node)
            
        def visit_While(self, node):
            nonlocal complexity
            complexity += 1
            self.generic_visit(node)
            
        def visit_Try(self, node):
            nonlocal complexity
            complexity += 1
            self.generic_visit(node)
            
        def visit_FunctionDef(self, node):
            nonlocal complexity, issues
            args_count = len(node.args.args)
            if args_count > 5:
                issues.append(f"Function '{node.name}' has too many parameters ({args_count})")
            self.generic_visit(node)
            
        def visit_BoolOp(self, node):
            nonlocal complexity
            complexity += len(node.values) - 1
            self.generic_visit(node)
    
    visitor = ComplexityVisitor()
    visitor.visit(node)
    
    status = "success"
    if complexity > 10:
        status = "error"
        issues.append(f"Code is too complex (complexity score: {complexity})")
    elif complexity > 5:
        status = "warning"
        issues.append(f"Code is moderately complex (complexity score: {complexity})")
        
    return {
        "status": status,
        "score": complexity,
        "issues": issues
    }

def _analyze_performance(node: ast.AST) -> Dict[str, Any]:
    """Analyze code for performance issues."""
    issues = []
    recommendations = []
    
    class PerformanceVisitor(ast.NodeVisitor):
        def visit_For(self, node):
            if isinstance(node.target, ast.Name) and isinstance(node.iter, ast.Call):
                if isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                    # Check for range() without start/step
                    if len(node.iter.args) == 1:
                        recommendations.append("Consider using range with start/step parameters for better control")
            self.generic_visit(node)
            
        def visit_ListComp(self, node):
            # List comprehension is generally good
            pass
            
        def visit_Call(self, node):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "append":
                    parent = getattr(node, "parent", None)
                    if isinstance(parent, ast.For):
                        recommendations.append("Consider using list comprehension instead of append in loop")
            self.generic_visit(node)
            
        def visit_BinOp(self, node):
            if isinstance(node.op, ast.Add) and isinstance(node.left, ast.Str):
                recommendations.append("Use join() instead of + for string concatenation")
            self.generic_visit(node)
    
    visitor = PerformanceVisitor()
    visitor.visit(node)
    
    status = "success"
    if len(recommendations) > 2:
        status = "warning"
        issues.append("Multiple performance improvements possible")
    
    return {
        "status": status,
        "issues": issues,
        "recommendations": recommendations
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

if __name__ == "__main__":
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