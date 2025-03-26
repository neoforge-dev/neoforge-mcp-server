"""
Metrics module for the MCP server.
"""
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Initialize metrics provider
meter_provider = MeterProvider(
    metric_readers=[PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint="http://localhost:4317")
    )]
)
metrics.set_meter_provider(meter_provider)

# Create meter
meter = metrics.get_meter("mcp")

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

active_sessions_counter = meter.create_up_down_counter(
    name="mcp.sessions.active",
    description="Number of active MCP sessions",
    unit="1"
)

def get_meter():
    """Get the MCP meter."""
    return meter 