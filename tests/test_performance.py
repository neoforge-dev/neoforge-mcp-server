import pytest
import asyncio
import time
import random
import string
from statistics import mean, stdev
from typing import Dict, List, Any
from fastapi.testclient import TestClient
from server.core.server import app as core_app
from server.neod.server import app as neod_app
from server.neoo.server import app as neoo_app
from server.neolocal.server import app as neolocal_app

# Performance thresholds (in seconds)
THRESHOLDS = {
    "health_check": 0.01,  # 10ms
    "tool_registration": 0.01,  # 10ms
    "tool_execution": 0.01,  # 10ms
    "file_operation": 0.01,  # 10ms
    "system_info": 0.01,  # 10ms
    "concurrent_operations": 0.01,  # 10ms
    "stress_test": 0.05,  # 50ms
    "large_file_operation": 0.02,  # 20ms
    "multiple_tools": 0.02  # 20ms
}

class PerformanceTest:
    def __init__(self):
        self.core_client = TestClient(core_app)
        self.neod_client = TestClient(neod_app)
        self.neoo_client = TestClient(neoo_app)
        self.neolocal_client = TestClient(neolocal_app)
        self.registered_tools = []

    def measure_latency(self, operation: callable, *args, **kwargs) -> float:
        """Measure the latency of an operation."""
        start_time = time.time()
        operation(*args, **kwargs)
        return time.time() - start_time

    def benchmark_operation(self, operation: callable, iterations: int = 10, *args, **kwargs) -> Dict[str, Any]:
        """Benchmark an operation over multiple iterations."""
        latencies = []
        for _ in range(iterations):
            latency = self.measure_latency(operation, *args, **kwargs)
            latencies.append(latency)
        
        return {
            "mean": mean(latencies),
            "stdev": stdev(latencies) if len(latencies) > 1 else 0,
            "min": min(latencies),
            "max": max(latencies),
            "iterations": iterations
        }

    def generate_random_string(self, length: int = 1000) -> str:
        """Generate a random string of specified length."""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def test_health_check_performance():
    """Test performance of health check endpoints."""
    perf = PerformanceTest()
    
    # Test Core MCP Server health check
    result = perf.benchmark_operation(
        perf.core_client.get, 
        iterations=10,
        url="/health"
    )
    assert result["mean"] < THRESHOLDS["health_check"], f"Health check too slow: {result['mean']}s"
    return result

def test_tool_registration_performance():
    """Test performance of tool registration."""
    perf = PerformanceTest()
    
    # Test tool registration
    result = perf.benchmark_operation(
        perf.core_client.post,
        iterations=10,
        url="/api/v1/tools/register",
        json={
            "name": "test_tool",
            "description": "Test tool",
            "endpoint": "http://localhost:7444/api/v1/llm/generate"
        }
    )
    assert result["mean"] < THRESHOLDS["tool_registration"], f"Tool registration too slow: {result['mean']}s"
    return result

def test_tool_execution_performance():
    """Test performance of tool execution."""
    perf = PerformanceTest()
    
    # First register a tool
    perf.core_client.post(
        "/api/v1/tools/register",
        json={
            "name": "test_tool",
            "description": "Test tool",
            "endpoint": "http://localhost:7444/api/v1/llm/generate"
        }
    )
    
    # Test tool execution
    result = perf.benchmark_operation(
        perf.core_client.post,
        iterations=10,
        url="/api/v1/tools/execute",
        json={
            "tool": "test_tool",
            "params": {
                "prompt": "Hello, world!",
                "max_tokens": 10
            }
        }
    )
    assert result["mean"] < THRESHOLDS["tool_execution"], f"Tool execution too slow: {result['mean']}s"
    return result

def test_file_operation_performance():
    """Test performance of file operations."""
    perf = PerformanceTest()
    
    # Test file info operation
    result = perf.benchmark_operation(
        perf.neolocal_client.post,
        iterations=10,
        url="/api/v1/local/file_info",
        json={
            "path": "README.md"
        }
    )
    assert result["mean"] < THRESHOLDS["file_operation"], f"File operation too slow: {result['mean']}s"
    return result

def test_system_info_performance():
    """Test performance of system information retrieval."""
    perf = PerformanceTest()
    
    # Test system info operation
    result = perf.benchmark_operation(
        perf.neoo_client.post,
        iterations=10,
        url="/api/v1/operations/system_info",
        json={}
    )
    assert result["mean"] < THRESHOLDS["system_info"], f"System info retrieval too slow: {result['mean']}s"
    return result

def test_concurrent_operations():
    """Test performance under concurrent load."""
    perf = PerformanceTest()
    
    # Define operations to run concurrently
    operations = [
        (perf.core_client.get, "/health"),
        (perf.neolocal_client.post, "/api/v1/local/file_info", {"path": "README.md"}),
        (perf.neoo_client.post, "/api/v1/operations/system_info", {})
    ]
    
    # Run operations sequentially (since TestClient is synchronous)
    start_time = time.time()
    for op, url, *args in operations:
        if args:
            op(url, json=args[0])
        else:
            op(url)
    total_time = time.time() - start_time
    
    # Assert that operations complete within reasonable time
    assert total_time < 3.0, f"Operations too slow: {total_time}s"
    return {"total_time": total_time}

def test_stress_performance():
    """Test performance under stress conditions."""
    perf = PerformanceTest()
    
    # Generate large payload
    large_payload = perf.generate_random_string(10000)
    
    # Test multiple operations under stress
    operations = [
        (perf.core_client.get, "/health"),
        (perf.core_client.post, "/api/v1/tools/register", {
            "name": "stress_tool",
            "description": "Stress test tool",
            "endpoint": "http://localhost:7444/api/v1/llm/generate",
            "payload": large_payload
        }),
        (perf.neolocal_client.post, "/api/v1/local/file_info", {
            "path": "README.md",
            "payload": large_payload
        })
    ]
    
    # Run stress test
    start_time = time.time()
    for op, url, *args in operations:
        if args:
            op(url, json=args[0])
        else:
            op(url)
    total_time = time.time() - start_time
    
    assert total_time < THRESHOLDS["stress_test"], f"Stress test too slow: {total_time}s"
    return {"total_time": total_time}

def test_large_file_operation():
    """Test performance with large file operations."""
    perf = PerformanceTest()
    
    # Create a large file
    large_content = perf.generate_random_string(100000)
    with open("test_large_file.txt", "w") as f:
        f.write(large_content)
    
    try:
        # Test file operations with large file
        result = perf.benchmark_operation(
            perf.neolocal_client.post,
            iterations=5,
            url="/api/v1/local/file_info",
            json={
                "path": "test_large_file.txt"
            }
        )
        assert result["mean"] < THRESHOLDS["large_file_operation"], f"Large file operation too slow: {result['mean']}s"
        return result
    finally:
        # Clean up
        import os
        if os.path.exists("test_large_file.txt"):
            os.remove("test_large_file.txt")

def test_multiple_tools():
    """Test performance with multiple tool registrations and executions."""
    perf = PerformanceTest()
    
    # Register multiple tools
    tools = []
    for i in range(5):
        tool_name = f"test_tool_{i}"
        perf.core_client.post(
            "/api/v1/tools/register",
            json={
                "name": tool_name,
                "description": f"Test tool {i}",
                "endpoint": "http://localhost:7444/api/v1/llm/generate"
            }
        )
        tools.append(tool_name)
    
    # Execute all tools
    start_time = time.time()
    for tool in tools:
        perf.core_client.post(
            "/api/v1/tools/execute",
            json={
                "tool": tool,
                "params": {
                    "prompt": "Hello, world!",
                    "max_tokens": 10
                }
            }
        )
    total_time = time.time() - start_time
    
    assert total_time < THRESHOLDS["multiple_tools"], f"Multiple tools execution too slow: {total_time}s"
    return {"total_time": total_time} 