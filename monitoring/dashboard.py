#!/usr/bin/env python3

from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from prometheus_client import start_http_server
import psutil
import time
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class MCPMonitoring:
    def __init__(self, 
                 prometheus_port: int = 9464,
                 otlp_endpoint: str = "http://localhost:4318/v1/metrics",
                 export_interval_ms: int = 5000):
        """Initialize the monitoring system"""
        self.prometheus_port = prometheus_port
        self.otlp_endpoint = otlp_endpoint
        self.export_interval_ms = export_interval_ms
        self.meter = None
        self.system_metrics = {}
        self.tool_metrics = {}
        
    def setup(self):
        """Set up the monitoring system with both Prometheus and OTLP exporters"""
        # Start Prometheus server
        start_http_server(self.prometheus_port)
        
        # Create metric readers
        prometheus_reader = PrometheusMetricReader()
        otlp_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=self.otlp_endpoint),
            export_interval_ms=self.export_interval_ms
        )
        
        # Create and set meter provider
        provider = MeterProvider(metric_readers=[prometheus_reader, otlp_reader])
        metrics.set_meter_provider(provider)
        
        # Get meter for MCP metrics
        self.meter = metrics.get_meter("mcp.monitoring")
        
        # Initialize metrics
        self._setup_system_metrics()
        self._setup_tool_metrics()
        
        logger.info(f"Monitoring system started - Prometheus port: {self.prometheus_port}")
        
    def _setup_system_metrics(self):
        """Set up system-level metrics"""
        # CPU Usage
        self.system_metrics["cpu_usage"] = self.meter.create_observable_gauge(
            "mcp.system.cpu_usage",
            description="CPU usage percentage",
            unit="percent",
            callbacks=[self._get_cpu_usage]
        )
        
        # Memory Usage
        self.system_metrics["memory_usage"] = self.meter.create_observable_gauge(
            "mcp.system.memory_usage",
            description="Memory usage percentage",
            unit="percent",
            callbacks=[self._get_memory_usage]
        )
        
        # Disk Usage
        self.system_metrics["disk_usage"] = self.meter.create_observable_gauge(
            "mcp.system.disk_usage",
            description="Disk usage percentage",
            unit="percent",
            callbacks=[self._get_disk_usage]
        )
        
        # Process Count
        self.system_metrics["process_count"] = self.meter.create_observable_gauge(
            "mcp.system.process_count",
            description="Number of running MCP processes",
            callbacks=[self._get_process_count]
        )
        
    def _setup_tool_metrics(self):
        """Set up tool-specific metrics"""
        # Tool Execution Counter
        self.tool_metrics["execution_count"] = self.meter.create_counter(
            "mcp.tool.execution_count",
            description="Number of tool executions",
            unit="calls"
        )
        
        # Tool Execution Time
        self.tool_metrics["execution_time"] = self.meter.create_histogram(
            "mcp.tool.execution_time",
            description="Tool execution time",
            unit="ms"
        )
        
        # Tool Error Counter
        self.tool_metrics["error_count"] = self.meter.create_counter(
            "mcp.tool.error_count",
            description="Number of tool execution errors"
        )
        
        # Active Tools
        self.tool_metrics["active_tools"] = self.meter.create_observable_gauge(
            "mcp.tool.active_count",
            description="Number of currently active tools",
            callbacks=[self._get_active_tools]
        )
        
    def _get_cpu_usage(self) -> Dict[str, Any]:
        """Get CPU usage callback"""
        return {"": psutil.cpu_percent()}
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage callback"""
        return {"": psutil.virtual_memory().percent}
    
    def _get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage callback"""
        return {"": psutil.disk_usage("/").percent}
    
    def _get_process_count(self) -> Dict[str, Any]:
        """Get MCP process count callback"""
        count = len([p for p in psutil.process_iter(["name"]) 
                    if "mcp" in p.info["name"].lower()])
        return {"": count}
    
    def _get_active_tools(self) -> Dict[str, Any]:
        """Get active tools count callback"""
        # This should be implemented based on your tool tracking mechanism
        return {"": 0}  # Placeholder
    
    def record_tool_execution(self, tool_name: str, duration_ms: float, 
                            success: bool = True):
        """Record a tool execution"""
        # Record execution count
        self.tool_metrics["execution_count"].add(
            1,
            {"tool": tool_name}
        )
        
        # Record execution time
        self.tool_metrics["execution_time"].record(
            duration_ms,
            {"tool": tool_name}
        )
        
        # Record error if failed
        if not success:
            self.tool_metrics["error_count"].add(
                1,
                {"tool": tool_name}
            )
            
    def get_metric_data(self) -> Dict[str, Any]:
        """Get current metric data for all metrics"""
        return {
            "system": {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage("/").percent,
                "process_count": len([p for p in psutil.process_iter(["name"]) 
                                   if "mcp" in p.info["name"].lower()])
            },
            "tools": {
                # This should be implemented based on your tool tracking
                "active_count": 0,
                # Add other tool metrics as needed
            }
        }

def create_monitoring(prometheus_port: int = 9464,
                     otlp_endpoint: str = "http://localhost:4318/v1/metrics",
                     export_interval_ms: int = 5000) -> MCPMonitoring:
    """Create and initialize a monitoring instance"""
    monitoring = MCPMonitoring(
        prometheus_port=prometheus_port,
        otlp_endpoint=otlp_endpoint,
        export_interval_ms=export_interval_ms
    )
    monitoring.setup()
    return monitoring 