"""
Shared monitoring utilities for MCP servers.
"""

import os
import time
import psutil
from typing import Any, Dict, Optional, List, Callable
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

class MonitoringManager:
    """Manages monitoring setup and configuration."""
    
    def __init__(
        self,
        service_name: str,
        service_version: str = "1.0.0",
        tracing_endpoint: Optional[str] = None,
        metrics_endpoint: Optional[str] = None,
        enable_tracing: bool = True,
        enable_metrics: bool = True
    ):
        """Initialize monitoring manager.
        
        Args:
            service_name: Name of the service
            service_version: Service version
            tracing_endpoint: OTLP exporter endpoint for tracing
            metrics_endpoint: OTLP exporter endpoint for metrics
            enable_tracing: Whether to enable tracing
            enable_metrics: Whether to enable metrics
        """
        self.service_name = service_name
        self.service_version = service_version
        
        # Create resource
        self.resource = Resource.create({
            "service.name": service_name,
            "service.version": service_version
        })
        
        # Setup tracing
        self.tracer = None
        if enable_tracing:
            self._setup_tracing(tracing_endpoint)
            
        # Setup metrics
        self.meter = None
        if enable_metrics:
            self._setup_metrics(metrics_endpoint)
            
        # Initialize metrics
        if self.meter:
            self._init_metrics()
            
    def _setup_tracing(self, endpoint: Optional[str]) -> None:
        """Setup tracing with OpenTelemetry."""
        # Only set up tracing if no provider exists
        if trace.get_tracer_provider() is None:
            # Create tracer provider
            tracer_provider = TracerProvider(resource=self.resource)
            
            # Add OTLP exporter if endpoint provided
            if endpoint:
                otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
                span_processor = BatchSpanProcessor(otlp_exporter)
                tracer_provider.add_span_processor(span_processor)
                
            # Set global tracer provider
            trace.set_tracer_provider(tracer_provider)
        
        # Get tracer
        self.tracer = trace.get_tracer(
            self.service_name,
            self.service_version
        )
        
    def _setup_metrics(self, endpoint: Optional[str]) -> None:
        """Setup metrics with OpenTelemetry."""
        # Only set up metrics if no provider exists
        if metrics.get_meter_provider() is None:
            # Create metric readers
            readers = []
            if endpoint:
                otlp_exporter = OTLPMetricExporter(endpoint=endpoint)
                readers.append(PeriodicExportingMetricReader(otlp_exporter))
            
            # Create meter provider
            meter_provider = MeterProvider(
                resource=self.resource,
                metric_readers=readers
            )
            
            # Set global meter provider
            metrics.set_meter_provider(meter_provider)
        
        # Get meter
        self.meter = metrics.get_meter(
            self.service_name,
            self.service_version
        )
        
    def _init_metrics(self) -> None:
        """Initialize default metrics."""
        # Request metrics
        self.request_counter = self.meter.create_counter(
            "requests_total",
            description="Total number of requests"
        )
        
        self.request_duration = self.meter.create_histogram(
            "request_duration_seconds",
            description="Request duration in seconds"
        )
        
        # Error metrics
        self.error_counter = self.meter.create_counter(
            "errors_total",
            description="Total number of errors"
        )
        
        # Resource metrics
        self.cpu_gauge = self.meter.create_up_down_counter(
            "cpu_usage_percent",
            description="CPU usage percentage"
        )
        
        self.memory_gauge = self.meter.create_up_down_counter(
            "memory_usage_bytes",
            description="Memory usage in bytes"
        )
        
    def create_span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = trace.SpanKind.SERVER
    ) -> Span:
        """Create a new span.
        
        Args:
            name: Span name
            attributes: Span attributes
            kind: Span kind (defaults to SERVER)
            
        Returns:
            New span
        """
        if not self.tracer:
            raise RuntimeError("Tracing not enabled")
            
        return self.tracer.start_span(
            name,
            attributes=attributes,
            kind=kind
        )
        
    @contextmanager
    def span_in_context(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = trace.SpanKind.SERVER
    ):
        """Create a span and set it as the current span.
        
        Args:
            name: Span name
            attributes: Span attributes
            kind: Span kind (defaults to SERVER)
            
        Yields:
            Active span
        """
        if not self.tracer:
            yield None
            return
            
        with self.tracer.start_as_current_span(
            name,
            attributes=attributes,
            kind=kind
        ) as span:
            yield span
            
    def trace(
        self,
        name: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = trace.SpanKind.SERVER
    ) -> Callable:
        """Decorator to trace a function.
        
        Args:
            name: Span name (defaults to function name)
            attributes: Span attributes
            kind: Span kind (defaults to SERVER)
            
        Returns:
            Decorated function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                if not self.tracer:
                    return func(*args, **kwargs)
                    
                span_name = name or func.__name__
                with self.span_in_context(span_name, attributes, kind) as span:
                    try:
                        result = func(*args, **kwargs)
                        if span:
                            span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        if span:
                            span.set_status(
                                Status(StatusCode.ERROR, str(e))
                            )
                            span.record_exception(e)
                        raise
            return wrapper
        return decorator
        
    def record_request(
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
        if not self.meter:
            return
            
        attributes = {
            "method": method,
            "path": path,
            "status_code": status_code
        }
        
        self.request_counter.add(1, attributes)
        self.request_duration.record(duration, attributes)
        
        if status_code >= 400:
            self.error_counter.add(1, attributes)
            
    def record_resource_usage(self) -> None:
        """Record resource usage metrics."""
        if not self.meter:
            return
            
        # Get CPU and memory usage
        process = psutil.Process()
        cpu_percent = process.cpu_percent()
        memory_info = process.memory_info()
        
        # Record metrics
        self.cpu_gauge.add(cpu_percent, {"type": "process"})
        self.memory_gauge.add(memory_info.rss, {"type": "rss"})
        self.memory_gauge.add(memory_info.vms, {"type": "vms"})
        
    def get_trace_info(self) -> Dict[str, Any]:
        """Get information about current tracing configuration.
        
        Returns:
            Dictionary with tracing information
        """
        return {
            "enabled": self.tracer is not None,
            "service_name": self.service_name,
            "service_version": self.service_version
        }
        
    def get_metrics_info(self) -> Dict[str, Any]:
        """Get information about current metrics configuration.
        
        Returns:
            Dictionary with metrics information
        """
        return {
            "enabled": self.meter is not None,
            "service_name": self.service_name,
            "service_version": self.service_version
        }

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