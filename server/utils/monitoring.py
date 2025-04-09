"""
Shared monitoring utilities for MCP servers.
"""

import os
import time
import psutil
from typing import Any, Dict, Optional, List, Callable, Generator
from functools import wraps
from contextlib import contextmanager
from opentelemetry import trace, metrics
from opentelemetry.trace import Span, Status, StatusCode, SpanKind
from opentelemetry.metrics import Meter, Counter, UpDownCounter, Histogram
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from prometheus_client import Counter, Histogram, start_http_server
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.metrics import get_meter_provider, set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
import logging

class MonitoringManager:
    """Manages monitoring and observability for MCP servers."""

    def __init__(
        self,
        app_name: str,
        metrics_port: int = 9090,
        enable_tracing: bool = False,
        tracing_endpoint: Optional[str] = None
    ):
        """Initialize monitoring manager.
        
        Args:
            app_name: Name of the application
            metrics_port: Port for metrics endpoint
            enable_tracing: Whether to enable tracing
            tracing_endpoint: Optional tracing endpoint URL
        """
        self.app_name = app_name
        self.metrics_port = metrics_port
        self.enable_tracing = enable_tracing
        self.tracing_endpoint = tracing_endpoint
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenTelemetry
        self._init_opentelemetry()
        
        # Initialize metrics
        self._init_metrics()
        
    def _init_opentelemetry(self) -> None:
        """Initialize OpenTelemetry."""
        # Create resource
        resource = Resource.create({
            ResourceAttributes.SERVICE_NAME: self.app_name,
            ResourceAttributes.SERVICE_VERSION: "1.0.0"
        })
        
        # Initialize tracing if enabled
        if self.enable_tracing and self.tracing_endpoint:
            # Create tracer provider
            tracer_provider = TracerProvider(resource=resource)
            
            # Create OTLP exporter
            exporter = OTLPSpanExporter(endpoint=self.tracing_endpoint)
            
            # Create span processor
            processor = BatchSpanProcessor(exporter)
            
            # Add processor to provider
            tracer_provider.add_span_processor(processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(tracer_provider)
            
    def _init_metrics(self) -> None:
        """Initialize metrics."""
        # Create OTLP exporter
        exporter = OTLPMetricExporter(
            endpoint=f"http://localhost:{self.metrics_port}"
        )
        
        # Create metric reader
        reader = PeriodicExportingMetricReader(exporter)
        
        # Create meter provider with the reader
        meter_provider = MeterProvider(metric_readers=[reader])
        
        # Set global meter provider
        set_meter_provider(meter_provider)
        
    def record_resource_usage(self) -> Dict[str, float]:
        """Record current resource usage.
        
        Returns:
            Dictionary of resource usage metrics
        """
        # Get process
        process = psutil.Process()
        
        # Get CPU usage
        cpu_percent = process.cpu_percent()
        
        # Get memory usage
        memory_info = process.memory_info()
        memory_percent = process.memory_percent()
        
        # Get disk usage
        disk_usage = psutil.disk_usage('/')
        
        # Record metrics
        metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "memory_bytes": memory_info.rss,
            "disk_percent": disk_usage.percent,
            "disk_free": disk_usage.free
        }
        
        # Log metrics
        self.logger.info("Resource usage", extra=metrics)
        
        return metrics
        
    def record_request_metrics(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float
    ) -> None:
        """Record request metrics.
        
        Args:
            method: HTTP method
            path: Request path
            status_code: Response status code
            duration: Request duration in seconds
        """
        # Get meter
        meter = get_meter_provider().get_meter(self.app_name)
        
        # Create counter for requests
        request_counter = meter.create_counter(
            "http_requests_total",
            description="Total number of HTTP requests"
        )
        
        # Create histogram for duration
        duration_histogram = meter.create_histogram(
            "http_request_duration_seconds",
            description="HTTP request duration in seconds"
        )
        
        # Record metrics
        request_counter.add(1, {
            "method": method,
            "path": path,
            "status_code": str(status_code)
        })
        
        duration_histogram.record(duration, {
            "method": method,
            "path": path,
            "status_code": str(status_code)
        })
        
    def record_error(self, error: Exception) -> None:
        """Record error metrics.
        
        Args:
            error: The error that occurred
        """
        # Get meter
        meter = get_meter_provider().get_meter(self.app_name)
        
        # Create counter for errors
        error_counter = meter.create_counter(
            "errors_total",
            description="Total number of errors"
        )
        
        # Record error
        error_counter.add(1, {
            "type": type(error).__name__,
            "message": str(error)
        })
        
    def get_tracer(self) -> trace.Tracer:
        """Get OpenTelemetry tracer.
        
        Returns:
            OpenTelemetry tracer
        """
        return trace.get_tracer(self.app_name)
        
    def create_span(self, name: str) -> trace.Span:
        """Create a new span.
        
        Args:
            name: Name of the span
            
        Returns:
            OpenTelemetry span
        """
        tracer = self.get_tracer()
        return tracer.start_span(name)
        
    @contextmanager
    def span_in_context(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> Generator[trace.Span, None, None]:
        """Create a new span as a context manager.
        
        Args:
            name: Name of the span
            attributes: Optional attributes for the span
            
        Yields:
            The created OpenTelemetry span
        """
        tracer = self.get_tracer()
        with tracer.start_as_current_span(name, attributes=attributes) as span:
            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, description=str(e)))
                span.record_exception(e)
                raise # Re-raise the exception

    def record_custom_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a custom metric.
        
        Args:
            name: Name of the metric
            value: Value to record
            labels: Optional labels for the metric
        """
        # Get meter
        meter = get_meter_provider().get_meter(self.app_name)
        
        # Create counter
        counter = meter.create_counter(
            name,
            description=f"Custom metric: {name}"
        )
        
        # Record metric
        counter.add(value, labels or {})

# Define metrics
REQUEST_COUNT = Counter(
    'mcp_request_total',
    'Total number of requests',
    ['endpoint', 'method', 'status']
)

REQUEST_LATENCY = Histogram(
    'mcp_request_latency_seconds',
    'Request latency in seconds',
    ['endpoint', 'method'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

ERROR_COUNT = Counter(
    'mcp_error_total',
    'Total number of errors',
    ['endpoint', 'method', 'error_type']
)

def monitor_request(endpoint: str, method: str):
    """Decorator to monitor request metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                response = await func(*args, **kwargs)
                status = 'success'
                REQUEST_COUNT.labels(endpoint=endpoint, method=method, status=status).inc()
                return response
            except Exception as e:
                status = 'error'
                error_type = type(e).__name__
                REQUEST_COUNT.labels(endpoint=endpoint, method=method, status=status).inc()
                ERROR_COUNT.labels(endpoint=endpoint, method=method, error_type=error_type).inc()
                raise
            finally:
                duration = time.time() - start_time
                REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)
        return wrapper
    return decorator

def start_monitoring(port: int = 8000):
    """Start the Prometheus metrics server."""
    start_http_server(port)
    print(f"Monitoring server started on port {port}") 