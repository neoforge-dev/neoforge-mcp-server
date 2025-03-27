"""Tests for observability tools - tracing and metrics."""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Import the server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from server import core

@pytest.fixture
def mock_tracer():
    """Set up mock tracer for testing."""
    with patch('server.core.trace') as mock_trace:
        mock_span = MagicMock()
        mock_span.name = "test_span"
        mock_span.get_span_context.return_value = "test-context"
        mock_trace.get_current_span.return_value = mock_span
        mock_trace.get_tracer_provider.return_value.__class__.__name__ = "TestTracerProvider"
        yield mock_trace

@pytest.fixture
def mock_exporter():
    """Set up mock exporter for testing."""
    with patch('server.core.otlp_exporter') as mock_exp:
        mock_exp.endpoint = "http://localhost:4317"
        mock_exp.__class__.__name__ = "OTLPSpanExporter"
        yield mock_exp

class TestGetTraceInfo:
    """Tests for get_trace_info tool."""
    
    def test_get_trace_info_success(self, mock_tracer, mock_exporter):
        """Test successful retrieval of tracing information."""
        # Execute the tool
        result = core.get_trace_info()
        
        # Verify result
        assert result["status"] == "success"
        assert result["tracer"]["name"] == mock_tracer.name
        assert result["tracer"]["version"] == "TestTracerProvider"
        assert result["current_span"]["name"] == "test_span"
        assert result["current_span"]["context"] == "test-context"
        assert result["current_span"]["active"] == True
        assert result["exporter"]["type"] == "OTLPSpanExporter"
        assert result["exporter"]["endpoint"] == "http://localhost:4317"

    def test_get_trace_info_no_span(self, mock_tracer):
        """Test tracing info when no span is active."""
        # Mock no active span
        mock_tracer.get_current_span.return_value = None
        
        # Execute the tool
        result = core.get_trace_info()
        
        # Verify result
        assert result["status"] == "success"
        assert result["current_span"]["name"] == None
        assert result["current_span"]["context"] == None
        assert result["current_span"]["active"] == False

    def test_get_trace_info_error(self, mock_tracer):
        """Test error handling in get_trace_info."""
        # Mock exception
        mock_tracer.get_current_span.side_effect = Exception("Test error")
        
        # Execute the tool
        result = core.get_trace_info()
        
        # Verify result
        assert result["status"] == "error"
        assert "error" in result
        assert "Test error" in result["error"]

class TestConfigureTracing:
    """Tests for configure_tracing tool."""
    
    def test_configure_tracing_endpoint(self, monkeypatch):
        """Test configuring tracing with custom endpoint."""
        # Mock dependencies
        mock_exporter = MagicMock()
        mock_processor = MagicMock()
        mock_provider = MagicMock()
        mock_resource = MagicMock()
        
        monkeypatch.setattr('server.core.OTLPSpanExporter', lambda endpoint: mock_exporter)
        monkeypatch.setattr('server.core.BatchSpanProcessor', lambda exporter: mock_processor)
        monkeypatch.setattr('server.core.TracerProvider', lambda resource: mock_provider)
        monkeypatch.setattr('server.core.resource', mock_resource)
        
        # Set up mock attributes
        mock_exporter.endpoint = "http://custom:4317"
        mock_resource.attributes = {}
        
        # Execute the tool
        result = core.configure_tracing(exporter_endpoint="http://custom:4317")
        
        # Verify result
        assert result["status"] == "success"
        assert "config" in result
        assert result["config"]["exporter_endpoint"] == "http://custom:4317"
        
    def test_configure_tracing_service_info(self, monkeypatch):
        """Test configuring tracing with service information."""
        # Mock dependencies
        mock_resource = MagicMock()
        mock_resource_class = MagicMock(return_value=mock_resource)
        mock_provider = MagicMock()
        mock_attributes = {}
        
        monkeypatch.setattr('server.core.Resource', mock_resource_class)
        monkeypatch.setattr('server.core.TracerProvider', lambda resource: mock_provider)
        monkeypatch.setattr('server.core.otlp_exporter.endpoint', "http://localhost:4317")
        
        # Set up attributes
        def get_attr(key, default=None):
            return mock_attributes.get(key, default)
        
        mock_resource.attributes = MagicMock()
        mock_resource.attributes.get = get_attr
        
        # Execute the tool
        result = core.configure_tracing(
            service_name="test-service", 
            service_version="1.0.0"
        )
        
        # Verify result
        assert result["status"] == "success"
        assert "config" in result
        assert result["config"]["exporter_endpoint"] == "http://localhost:4317"
        # Verify Resource was called with attributes
        resource_call = mock_resource_class.call_args[0][0]
        assert "attributes" in resource_call

    def test_configure_tracing_error(self, monkeypatch):
        """Test error handling in configure_tracing."""
        # Mock exception
        def raise_error(*args, **kwargs):
            raise Exception("Test error")
        
        monkeypatch.setattr('server.core.OTLPSpanExporter', raise_error)
        
        # Execute the tool
        result = core.configure_tracing(exporter_endpoint="http://custom:4317")
        
        # Verify result
        assert result["status"] == "error"
        assert "error" in result
        assert "Test error" in result["error"] 