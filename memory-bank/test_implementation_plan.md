# Test Implementation Plan for MCP Tools

## Overview

This document outlines the plan for implementing tests for MCP tools that currently lack test coverage. The implementation follows best practices for Python testing, using pytest as the primary testing framework.

## Test Coverage Analysis

Based on our code analysis, the following 13 MCP tools require test implementation:

1. get_trace_info
2. configure_tracing
3. get_metrics_info
4. configure_metrics
5. install_dependency
6. run_tests
7. format_code
8. lint_code
9. monitor_performance
10. generate_documentation
11. setup_validation_gates
12. analyze_project
13. manage_changes

## Implementation Approach

### Phase 1: Observability Tools

#### get_trace_info Tests
```python
def test_get_trace_info_success(mocker):
    """Test successful retrieval of tracing information."""
    # Mock tracer and span
    mock_span = mocker.MagicMock()
    mock_span.name = "test_span"
    mock_span.get_span_context = mocker.MagicMock(return_value="context")
    mocker.patch('opentelemetry.trace.get_current_span', return_value=mock_span)
    
    # Execute the tool
    result = server.get_trace_info()
    
    # Verify result
    assert result["status"] == "success"
    assert result["tracer"]["name"] == tracer.name
    assert result["current_span"]["name"] == "test_span"
    assert result["current_span"]["active"] == True

def test_get_trace_info_no_span(mocker):
    """Test tracing info when no span is active."""
    # Mock no active span
    mocker.patch('opentelemetry.trace.get_current_span', return_value=None)
    
    # Execute the tool
    result = server.get_trace_info()
    
    # Verify result
    assert result["status"] == "success"
    assert result["current_span"]["name"] == None
    assert result["current_span"]["active"] == False

def test_get_trace_info_error(mocker):
    """Test error handling in get_trace_info."""
    # Mock exception
    mocker.patch('opentelemetry.trace.get_current_span', 
                 side_effect=Exception("Test error"))
    
    # Execute the tool
    result = server.get_trace_info()
    
    # Verify result
    assert result["status"] == "error"
    assert "error" in result
    assert "Test error" in result["error"]
```

#### configure_tracing Tests
```python
def test_configure_tracing_endpoint(mocker):
    """Test configuring tracing with custom endpoint."""
    # Mock dependencies
    mock_exporter = mocker.MagicMock()
    mock_processor = mocker.MagicMock()
    mock_provider = mocker.MagicMock()
    
    mocker.patch('opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter', 
                 return_value=mock_exporter)
    mocker.patch('opentelemetry.sdk.trace.export.BatchSpanProcessor', 
                 return_value=mock_processor)
    mocker.patch('opentelemetry.sdk.trace.TracerProvider', 
                 return_value=mock_provider)
    mocker.patch('opentelemetry.trace.set_tracer_provider')
    
    # Execute the tool
    result = server.configure_tracing(exporter_endpoint="http://custom:4317")
    
    # Verify result
    assert result["status"] == "success"
    assert "config" in result
    assert result["config"]["exporter_endpoint"] == "http://custom:4317"

def test_configure_tracing_service_info(mocker):
    """Test configuring tracing with service information."""
    # Mock dependencies
    mock_resource = mocker.MagicMock()
    mock_provider = mocker.MagicMock()
    
    mocker.patch('opentelemetry.sdk.resources.Resource', return_value=mock_resource)
    mocker.patch('opentelemetry.sdk.trace.TracerProvider', return_value=mock_provider)
    mocker.patch('opentelemetry.trace.set_tracer_provider')
    
    # Execute the tool
    result = server.configure_tracing(
        service_name="test-service", 
        service_version="1.0.0"
    )
    
    # Verify result
    assert result["status"] == "success"
    assert "config" in result

def test_configure_tracing_error(mocker):
    """Test error handling in configure_tracing."""
    # Mock exception
    mocker.patch('opentelemetry.exporter.otlp.proto.grpc.trace_exporter.OTLPSpanExporter', 
                 side_effect=Exception("Test error"))
    
    # Execute the tool
    result = server.configure_tracing(exporter_endpoint="http://custom:4317")
    
    # Verify result
    assert result["status"] == "error"
    assert "error" in result
    assert "Test error" in result["error"]
```

Similar test implementations will be provided for get_metrics_info and configure_metrics.

### Phase 2: Development Tools

#### install_dependency Tests
```python
def test_install_dependency_success(mocker, tmp_path):
    """Test successful package installation."""
    # Setup mock environment
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = mocker.MagicMock(
        stdout="Successfully installed test-package-1.0.0",
        stderr="",
        returncode=0
    )
    
    # Create mock pyproject.toml
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[tool.poetry.dependencies]\npython = "^3.8"\ntest-package = "1.0.0"\n')
    mocker.patch('builtins.open', mocker.mock_open(read_data=pyproject_path.read_text()))
    
    # Execute the tool
    result = server.install_dependency("test-package")
    
    # Verify result
    assert result["status"] == "success"
    assert "test-package" in result["package"]
    mock_run.assert_called_once()
    assert "uv" in mock_run.call_args[0][0][0]
    assert "add" in mock_run.call_args[0][0][1]
    assert "test-package" in mock_run.call_args[0][0][-1]

def test_install_dependency_dev(mocker, tmp_path):
    """Test installing package as dev dependency."""
    # Setup mock
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = mocker.MagicMock(
        stdout="Successfully installed test-package-1.0.0",
        stderr="",
        returncode=0
    )
    
    # Create mock pyproject.toml
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[tool.poetry.dev-dependencies]\ntest-package = "1.0.0"\n')
    mocker.patch('builtins.open', mocker.mock_open(read_data=pyproject_path.read_text()))
    
    # Execute the tool
    result = server.install_dependency("test-package", dev=True)
    
    # Verify result
    assert result["status"] == "success"
    assert "test-package" in result["package"]
    mock_run.assert_called_once()
    assert "--dev" in mock_run.call_args[0][0]

def test_install_dependency_error(mocker):
    """Test error handling during package installation."""
    # Setup mock for failed installation
    mock_run = mocker.patch('subprocess.run')
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1,
        cmd=["uv", "add", "non-existent-package"],
        stderr="Package not found"
    )
    
    # Execute the tool
    result = server.install_dependency("non-existent-package")
    
    # Verify result
    assert result["status"] == "error"
    assert "error" in result
    assert "Package not found" in result["error"]
```

Similar test implementations will be provided for run_tests, format_code, and lint_code.

### Phase 3: Monitoring and Documentation Tools

#### monitor_performance Tests
```python
def test_monitor_performance_basic(mocker):
    """Test basic performance monitoring functionality."""
    # Mock psutil functions
    mock_cpu = mocker.patch('psutil.cpu_percent', return_value=10.5)
    mock_cpu_count = mocker.patch('psutil.cpu_count', return_value=8)
    mock_cpu_freq = mocker.patch('psutil.cpu_freq', return_value=mocker.MagicMock(_asdict=lambda: {"current": 2400}))
    mock_memory = mocker.patch('psutil.virtual_memory', return_value=mocker.MagicMock(
        total=16000000000, available=8000000000, percent=50.0, used=8000000000, free=8000000000
    ))
    mock_disk = mocker.patch('psutil.disk_usage', return_value=mocker.MagicMock(
        total=512000000000, used=128000000000, free=384000000000, percent=25.0
    ))
    mock_net = mocker.patch('psutil.net_io_counters', side_effect=[
        mocker.MagicMock(bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20),
        mocker.MagicMock(bytes_sent=1500, bytes_recv=3000, packets_sent=15, packets_recv=30)
    ])
    
    # Mock time functions to control test duration
    mocker.patch('time.sleep', return_value=None)
    time_values = [0, 0.5, 1.0, 1.5, 2.0]
    time_mock = mocker.patch('time.time')
    time_mock.side_effect = time_values
    
    mock_datetime = mocker.patch('datetime.datetime')
    mock_datetime.now.return_value = mocker.MagicMock(isoformat=lambda: "2023-01-01T12:00:00")
    
    # Execute the tool with short duration for testing
    result = server.monitor_performance(duration=2, interval=0.5)
    
    # Verify result
    assert result["status"] == "success"
    assert "metrics" in result
    assert "summary" in result
    assert len(result["metrics"]["cpu"]) > 0
    assert len(result["metrics"]["memory"]) > 0
    assert len(result["metrics"]["disk"]) > 0
    assert len(result["metrics"]["network"]) > 0
    
    # Verify summary calculations
    assert "avg" in result["summary"]["cpu"]
    assert "avg_percent" in result["summary"]["memory"]
    assert "avg_percent" in result["summary"]["disk"]
    assert "total_sent" in result["summary"]["network"]
    assert "total_recv" in result["summary"]["network"]

def test_monitor_performance_error(mocker):
    """Test error handling in performance monitoring."""
    # Mock psutil to raise exception
    mocker.patch('psutil.cpu_percent', side_effect=Exception("Test error"))
    
    # Execute the tool
    result = server.monitor_performance(duration=1)
    
    # Verify result
    assert result["status"] == "error"
    assert "error" in result
    assert "Test error" in result["error"]
```

#### generate_documentation Tests
```python
def test_generate_api_docs(mocker, tmp_path):
    """Test API documentation generation."""
    # Mock dependencies
    mock_pdoc = mocker.patch('pdoc.doc.Module')
    mock_pdoc.return_value.html.return_value = "<html>Test API docs</html>"
    mocker.patch('importlib.import_module', return_value=mocker.MagicMock())
    mocker.patch('os.makedirs')
    mock_open = mocker.patch('builtins.open', mocker.mock_open())
    
    # Execute the tool
    result = server.generate_documentation("test_module", doc_type="api")
    
    # Verify result
    assert result["status"] == "success"
    assert "output_file" in result
    assert mock_open.called
    mock_open().write.assert_called_once_with("<html>Test API docs</html>")

def test_generate_readme(mocker, tmp_path):
    """Test README generation."""
    # Mock dependencies
    mock_analyze = mocker.patch('server._analyze_project_info')
    mock_analyze.return_value = {
        "name": "Test Project",
        "description": "Test description",
        "setup": "Test setup",
        "usage": "Test usage",
        "api": "Test API",
        "contributing": "Test contributing"
    }
    mock_open = mocker.patch('builtins.open', mocker.mock_open())
    
    # Execute the tool
    result = server.generate_documentation("test_dir", doc_type="readme")
    
    # Verify result
    assert result["status"] == "success"
    assert "output_file" in result
    assert mock_open.called
    # Verify template expansion
    write_call = mock_open().write.call_args[0][0]
    assert "Test Project" in write_call
    assert "Test description" in write_call

def test_generate_documentation_error(mocker):
    """Test error handling in documentation generation."""
    # Mock exception
    mocker.patch('importlib.import_module', side_effect=ImportError("Module not found"))
    
    # Execute the tool
    result = server.generate_documentation("non_existent_module", doc_type="api")
    
    # Verify result
    assert result["status"] == "error"
    assert "error" in result
    assert "Module not found" in result["error"]
```

### Phase 4: Project Management Tools

Similar detailed test implementations will be provided for setup_validation_gates, analyze_project, and manage_changes tools.

### Phase 5: AI Coding Agent Tools

#### Test Goals
- Verify that each AI Coding Agent tool functions correctly
- Ensure tools handle various programming languages and project structures
- Test error handling and edge cases
- Validate performance characteristics meet requirements

#### understand_code Tests

```python
class TestUnderstandCode:
    """Tests for the understand_code tool."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_project = create_test_project()
        
    def teardown_method(self):
        """Clean up test resources."""
        clean_test_project(self.test_project)
        
    def test_understand_code_basic_analysis(self):
        """Test basic code analysis functionality."""
        # Arrange
        target_path = os.path.join(self.test_project, "sample.py")
        
        # Act
        result = server.understand_code(
            target_path=target_path,
            analysis_depth=1,
            include_external_deps=False,
            output_format="graph"
        )
        
        # Assert
        assert result["status"] == "success"
        assert "output" in result
        assert "graph" in result["output"]
        assert "metadata" in result
        assert result["metadata"]["files_analyzed"] > 0
        
    def test_understand_code_deep_analysis(self):
        """Test deep analysis with multiple files."""
        # Arrange
        target_path = self.test_project
        
        # Act
        result = server.understand_code(
            target_path=target_path,
            analysis_depth=3,
            include_external_deps=True,
            output_format="map"
        )
        
        # Assert
        assert result["status"] == "success"
        assert "output" in result
        assert "map" in result["output"]
        assert result["metadata"]["files_analyzed"] > 1
        assert result["metadata"]["relationships_found"] > 0
        
    def test_understand_code_invalid_path(self):
        """Test error handling for invalid path."""
        # Arrange
        target_path = "/path/does/not/exist"
        
        # Act
        result = server.understand_code(
            target_path=target_path,
            analysis_depth=1
        )
        
        # Assert
        assert result["status"] == "error"
        assert "error" in result
```

#### refactor_code Tests

```python
class TestRefactorCode:
    """Tests for the refactor_code tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_project = create_test_project()
        
    def teardown_method(self):
        """Clean up test resources."""
        clean_test_project(self.test_project)
        
    def test_refactor_code_rename_symbol(self):
        """Test refactoring that renames a symbol."""
        # Arrange
        target_path = os.path.join(self.test_project, "sample.py")
        refactoring_type = "rename"
        original_name = "example_function"
        new_name = "renamed_function"
        
        # Act
        result = server.refactor_code(
            target_path=target_path,
            refactoring_type=refactoring_type,
            original_name=original_name,
            new_name=new_name
        )
        
        # Assert
        assert result["status"] == "success"
        assert result["changes"] > 0
        assert "modified_files" in result
        
        # Verify the function was actually renamed
        with open(target_path, "r") as f:
            content = f.read()
            assert original_name not in content
            assert new_name in content
            
    def test_refactor_code_extract_method(self):
        """Test refactoring that extracts a method."""
        # Implementation details...
        pass
        
    def test_refactor_code_error_handling(self):
        """Test error handling in refactoring."""
        # Implementation details...
        pass
```

#### generate_tests Tests

```python
class TestGenerateTests:
    """Tests for the generate_tests tool."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_project = create_test_project()
        
    def teardown_method(self):
        """Clean up test resources."""
        clean_test_project(self.test_project)
        
    def test_generate_tests_basic_function(self):
        """Test generating tests for a basic function."""
        # Arrange
        target_path = os.path.join(self.test_project, "sample.py")
        
        # Act
        result = server.generate_tests(
            target_path=target_path,
            coverage_target=0.8
        )
        
        # Assert
        assert result["status"] == "success"
        assert "tests" in result
        assert len(result["tests"]) > 0
        assert "test_file_path" in result
        
        # Verify test file was created and contains tests
        assert os.path.exists(result["test_file_path"])
        with open(result["test_file_path"], "r") as f:
            content = f.read()
            assert "test_" in content
            assert "assert" in content
            
    def test_generate_tests_complex_class(self):
        """Test generating tests for a complex class."""
        # Implementation details...
        pass
        
    def test_generate_tests_edge_cases(self):
        """Test generation of edge case tests."""
        # Implementation details...
        pass
```

## Test Environment Setup

For all tests, we'll use the following setup:

1. **pytest Configuration**:
   - Use pytest fixtures for common setup
   - Enable pytest-cov for coverage reporting
   - Configure pytest-mock for mocking dependencies

2. **Mock External Dependencies**:
   - Subprocess calls
   - File system operations
   - Network requests
   - API client interactions

3. **Test Data**:
   - Create test fixtures with sample data
   - Use temporary directories for file operations
   - Set up mock responses for API calls

## Implementation Timeline

1. **Week 1**: Implement tests for observability tools
   - get_trace_info
   - configure_tracing
   - get_metrics_info
   - configure_metrics

2. **Week 2**: Implement tests for development tools
   - install_dependency
   - run_tests
   - format_code
   - lint_code

3. **Week 3**: Implement tests for monitoring and documentation tools
   - monitor_performance
   - generate_documentation

4. **Week 4**: Implement tests for project management tools
   - setup_validation_gates
   - analyze_project
   - manage_changes

5. **Week 5**: Implement tests for AI Coding Agent tools
   - understand_code
   - refactor_code
   - generate_tests
   - analyze_dependencies
   - review_code

6. **Week 6**: Finalize and optimize test suite
   - Improve test coverage where needed
   - Optimize test performance
   - Document testing patterns and practices

## Success Criteria

1. **Coverage Metrics**:
   - Minimum 80% test coverage for each tool
   - All primary functionality paths tested
   - Error handling paths tested

2. **Test Quality**:
   - Tests are independent and isolated
   - Tests are deterministic (no flaky tests)
   - Tests are fast (execution < 5 seconds per test)

3. **Documentation**:
   - Test patterns documented
   - Test approach explained
   - Coverage reports generated 