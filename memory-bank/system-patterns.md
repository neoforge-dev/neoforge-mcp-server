# System Architecture and Design Patterns

## Core Architecture

### MCP Server
- FastMCP-based server implementation
- RESTful API design with tool-based interface
- Server-Sent Events (SSE) transport protocol
- Asynchronous command execution
- Event-driven output streaming
- Thread-safe process management
- Advanced profiling system
- OpenTelemetry integration
- Code generation capabilities
- AI Coding Agent tools integration

### AI Coding Agent Tools Architecture
- Code understanding and analysis system
- Intelligent refactoring framework
- Automated test generation system
- Dependency impact analysis engine
- Code review automation platform
- Language-agnostic parsing with tree-sitter
- Semantic code mapping system
- Relationship graph visualization
- Persistent indexing for large codebases
- Embedding-based semantic search

### Connectivity Architecture
- SSE-based communication protocol
- Port configuration for external access
- Traefik proxy integration for routing
- Firewall configuration for security
- SSH tunnel capability for secure access
- Connection error handling 
- Client reconnection strategies

### Component Structure
```
server.py
├── Core Tools
│   ├── Command Execution
│   ├── Process Management
│   ├── File Operations
│   └── Code Generation
├── Development Tools
│   ├── Code Analysis
│   ├── Performance Monitoring
│   ├── Testing Support
│   └── Profiling
├── AI Coding Agent Tools
│   ├── Code Understanding
│   ├── Intelligent Refactoring
│   ├── Test Generation
│   ├── Dependency Impact Analysis
│   └── Code Review Automation
├── Connectivity Tools
│   ├── Connection Management
│   ├── Transport Configuration
│   ├── Proxy Integration
│   └── Network Troubleshooting
└── Utility Tools
    ├── System Info
    ├── Calculations
    └── Context Management
```

## Design Patterns

### AI Coding Agent Tool Patterns
- **Code Analysis Pattern**: Language-agnostic parsing with custom extractors
- **Graph-Based Code Representation**: Nodes for entities, edges for relationships
- **Semantic Mapping**: Embedding-based connectivity between code and natural language
- **Incremental Analysis**: Update only changed components for performance
- **Persistent Indexing**: Serialize and store analysis results for quick access
- **Language Adapter**: Plug-in architecture for multi-language support
- **Analysis Pipeline**: Multi-stage processing with progressive refinement
- **Entity Resolver**: Connect references across different files and modules

### Communication Patterns
- Server-Sent Events (SSE) for unidirectional streaming
- RESTful API for bidirectional communication
- Protocol negotiation for client compatibility
- Connection pooling for performance
- Graceful degradation for network issues
- Reconnection strategies for resilience

### Command Pattern
- Each tool is implemented as a discrete command
- Standardized input/output interface
- Error handling and validation
- Resource cleanup
- Profiling integration
- Metrics collection

### Observer Pattern
- Process output streaming
- Performance metrics collection
- Event-based notifications
- Profiling data collection
- Code generation events
- Validation results

### Factory Pattern
- Tool registration and instantiation
- Dynamic command creation
- Plugin system support
- Model factory for code generation
- Profiler factory
- Metrics collector factory

### Strategy Pattern
- Configurable execution strategies
- Platform-specific implementations
- Test environment isolation
- Model selection strategy
- Profiling strategy
- Validation strategy

## Implementation Patterns for AI Coding Agent Tools

### Code Understanding Tool
```python
class CodeAnalyzer:
    """Core code analysis engine."""
    
    def __init__(self, target_path: str):
        self.target_path = target_path
        self.parsers = {}
        self.register_parsers()
        
    def register_parsers(self):
        """Register language-specific parsers."""
        self.parsers = {
            ".py": PythonParser(),
            ".js": JavaScriptParser(),
            ".ts": TypeScriptParser(),
            # More languages...
        }
        
    def analyze(self, depth: int = 2, include_external: bool = False) -> AnalysisResult:
        """Analyze code at the specified path."""
        result = AnalysisResult()
        
        # Find all files to analyze
        files = self._find_files(include_external)
        
        # Parse files and extract symbols
        for file_path in files:
            extension = os.path.splitext(file_path)[1]
            if extension in self.parsers:
                parser = self.parsers[extension]
                file_analysis = parser.parse(file_path)
                result.add_file_analysis(file_analysis)
        
        # Build relationships up to specified depth
        result.build_relationships(depth)
        
        return result
    
    def _find_files(self, include_external: bool) -> List[str]:
        """Find files to analyze."""
        # Implementation details...
        pass
        
class GraphBuilder:
    """Builds relationship graphs from analysis results."""
    
    def __init__(self, analysis_result: AnalysisResult):
        self.analysis_result = analysis_result
        self.graph = nx.DiGraph()
        
    def build(self) -> CodeGraph:
        """Build a directed graph of code relationships."""
        # Add nodes for all symbols
        for symbol in self.analysis_result.symbols:
            self.graph.add_node(symbol.id, **symbol.attributes)
        
        # Add edges for relationships
        for relationship in self.analysis_result.relationships:
            self.graph.add_edge(
                relationship.source_id,
                relationship.target_id,
                type=relationship.type,
                **relationship.attributes
            )
        
        return CodeGraph(self.graph)
```

### Intelligent Refactoring Tool
```python
class RefactoringPlanner:
    """Plans code refactoring operations."""
    
    def plan_refactoring(self, code_graph: CodeGraph, target: str, refactoring_type: str) -> RefactoringPlan:
        """Create a plan for refactoring the specified target."""
        # Implementation details...
        pass
        
class BehaviorValidator:
    """Validates that refactoring preserves behavior."""
    
    def validate(self, original_code: str, refactored_code: str) -> ValidationResult:
        """Check if the refactored code preserves the behavior of the original code."""
        # Implementation details...
        pass
```

### Test Generation Tool
```python
class TestGenerator:
    """Generates tests for code."""
    
    def generate_tests(self, source_code: str, coverage_target: float = 0.8) -> List[TestCase]:
        """Generate test cases for the given source code."""
        # Implementation details...
        pass
        
class EdgeCaseDiscoverer:
    """Discovers edge cases for testing."""
    
    def discover(self, source_code: str) -> List[EdgeCase]:
        """Find potential edge cases in the source code."""
        # Implementation details...
        pass
```

## Security Patterns

### Network Security
- Port-specific firewall rules
- Transport-level encryption options
- Proxy-based request filtering
- Connection source validation
- Rate limiting for connection attempts
- Connection monitoring for anomalies

### Command Validation
- Blacklist-based command filtering
- Path traversal prevention
- Resource limit enforcement
- Code generation safety
- Model access control
- Input sanitization

### Process Isolation
- Separate process spaces
- Timeout enforcement
- Resource cleanup
- Model execution isolation
- Profiling isolation
- Validation isolation

### Error Handling
- Comprehensive error capture
- Structured error responses
- Graceful degradation
- Model error handling
- Profiling error recovery
- Validation error reporting

## Performance Patterns

### Connection Management
- Connection pool optimization
- Connection timeout handling
- Reconnection backoff strategies
- Load balancing for multiple clients
- Connection metrics collection
- Health checking for connections

### Resource Management
- Thread pool management
- Process lifecycle control
- Memory usage optimization
- Model resource management
- Profiling overhead control
- Validation resource limits

### Output Handling
- Streaming large outputs
- Buffer management
- Smart truncation
- Model output streaming
- Profiling data streaming
- Validation result streaming

### Caching
- Command result caching
- File content caching
- System info caching
- Model response caching
- Profiling data caching
- Validation result caching

## Testing Patterns

### Test Categories
- Unit tests for core functionality
- Integration tests for tool interaction
- System tests for end-to-end validation
- Model integration tests
- Profiling tests
- Validation tests
- Observability tool tests
- Development tool tests
- Documentation generation tests
- Project management tool tests

### Test Structure for MCP Tools
```python
def test_tool_name_success_case(fixture_setup):
    """Test successful operation of the tool."""
    # Arrange
    test_params = {...}
    expected_output = {...}
    
    # Act
    result = server.tool_name(**test_params)
    
    # Assert
    assert result["status"] == "success"
    assert result["expected_key"] == expected_output
    
def test_tool_name_error_case(fixture_setup):
    """Test error handling of the tool."""
    # Arrange
    invalid_params = {...}
    
    # Act
    result = server.tool_name(**invalid_params)
    
    # Assert
    assert result["status"] == "error"
    assert "error" in result
```

### Test Isolation
- Docker-based test environments
- Mock system operations
- Resource cleanup
- Model mocking
- Profiling isolation
- Validation isolation
- API endpoint mocking
- File system sandboxing
- Dependency injection for testability

### Performance Testing
- Load testing framework
- Resource usage monitoring
- Benchmark suite
- Model performance tests
- Profiling overhead tests
- Validation performance tests
- Metrics collection validation
- Tracing overhead assessment

### Missing Test Implementation Patterns
```python
# Observability Tools Testing Pattern
def test_observability_tool(mocker):
    """Test pattern for observability tools."""
    # Mock dependencies
    mock_dependency = mocker.patch('module.dependency')
    mock_dependency.return_value = expected_data
    
    # Call the tool
    result = server.observability_tool(params)
    
    # Verify result
    assert result["status"] == "success"
    assert "expected_data" in result
    mock_dependency.assert_called_once_with(params)

# Development Tools Testing Pattern
def test_development_tool(tmp_path, mocker):
    """Test pattern for development tools."""
    # Set up test environment
    test_file = tmp_path / "test_file.py"
    test_file.write_text("def test(): pass")
    
    # Mock subprocess calls
    mock_run = mocker.patch('subprocess.run')
    mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
    
    # Call the tool
    result = server.development_tool(str(test_file))
    
    # Verify result
    assert result["status"] == "success"
    assert mock_run.called
    
# Documentation Tools Testing Pattern
def test_documentation_tool(tmp_path):
    """Test pattern for documentation generation tools."""
    # Set up test project
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()
    (test_dir / "test_module.py").write_text("def function(): \"\"\"Docstring\"\"\"")
    
    # Call the tool
    result = server.documentation_tool(str(test_dir))
    
    # Verify result
    assert result["status"] == "success"
    assert (test_dir / "docs").exists()
```

## Development Patterns

### Connectivity Testing
```python
def test_server_connectivity(host: str, port: int) -> Dict[str, Any]:
    """
    Test server connectivity
    
    Args:
        host: Server hostname
        port: Server port
    
    Returns:
        Dictionary with connectivity test results
    """
    try:
        # Try to connect
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            result = s.connect_ex((host, port))
            
        if result == 0:
            return {
                'status': 'success',
                'message': f'Successfully connected to {host}:{port}'
            }
        else:
            return {
                'status': 'error',
                'error': f'Failed to connect to {host}:{port}',
                'code': result
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
```

### Transport Configuration
```python
def configure_transport(transport_type: str) -> Dict[str, Any]:
    """
    Configure server transport
    
    Args:
        transport_type: Transport type ("sse" or "websocket")
    
    Returns:
        Dictionary with configuration result
    """
    try:
        # Validate transport type
        valid_transports = ["sse", "websocket"]
        if transport_type not in valid_transports:
            return {
                'status': 'error',
                'error': f'Invalid transport: {transport_type}. Must be one of {valid_transports}'
            }
            
        # Update configuration
        config = {
            'transport': transport_type,
            'path': '/sse' if transport_type == 'sse' else '/ws',
            'reconnect_interval': 1000
        }
        
        # Save configuration
        with open('config.json', 'w') as f:
            json.dump(config, f)
            
        return {
            'status': 'success',
            'config': config
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
```

### Code Organization
- Modular tool implementation
- Clear separation of concerns
- Consistent file structure
- Model integration structure
- Profiling integration
- Validation organization

### Error Handling
```python
try:
    # Operation-specific logic
    result = perform_operation()
    return {
        'status': 'success',
        'result': result
    }
except SpecificError as e:
    return {
        'status': 'error',
        'error': str(e),
        'type': 'specific_error'
    }
except Exception as e:
    return {
        'status': 'error',
        'error': str(e),
        'type': 'general_error'
    }
```

### Function Structure
```python
@mcp.tool()
def tool_name(param1: Type1, param2: Type2 = default) -> Dict[str, Any]:
    """
    Tool description
    
    Args:
        param1: Description
        param2: Description
    
    Returns:
        Dictionary with operation result
    """
    try:
        # Validation
        if not validate_params(param1, param2):
            return {'status': 'error', 'error': 'Invalid parameters'}
            
        # Core logic
        result = process_operation(param1, param2)
        
        # Result formatting
        return {
            'status': 'success',
            'result': result
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
```

## Integration Patterns

### Tool Communication
- Standardized result format
- Error propagation
- Context sharing
- Model communication
- Profiling data sharing
- Validation result sharing

### Resource Sharing
- Thread-safe queues
- Shared state management
- Resource pools
- Model resource sharing
- Profiling resource sharing
- Validation resource sharing

### Event Handling
- Process lifecycle events
- Error events
- Status updates
- Model events
- Profiling events
- Validation events

## Monitoring Patterns

### Performance Metrics
- CPU usage tracking
- Memory utilization
- I/O operations
- Network traffic
- Model performance
- Profiling metrics
- Validation metrics

### Error Tracking
- Error categorization
- Stack trace collection
- Error rate monitoring
- Model errors
- Profiling errors
- Validation errors

### Health Checks
- Service availability
- Resource utilization
- System status
- Model health
- Profiling health
- Validation health

## Documentation Patterns

### Code Documentation
- Google-style docstrings
- Type hints
- Usage examples
- Model documentation
- Profiling documentation
- Validation documentation

### API Documentation
- OpenAPI/Swagger specs
- Example requests/responses
- Error scenarios
- Model API docs
- Profiling API docs
- Validation API docs

### System Documentation
- Architecture overview
- Component interaction
- Deployment guides
- Model deployment
- Profiling setup
- Validation setup

## Observability Patterns

### Distributed Tracing Architecture
1. **Trace Collection**
   - OpenTelemetry SDK for trace generation
   - OTLP exporter for trace export
   - Configurable collection endpoint
   - Batch processing for efficient trace export
   - Model tracing
   - Profiling tracing
   - Validation tracing

2. **Tool Tracing**
   - Decorator pattern for automatic tool tracing
   - Consistent span naming convention: `mcp.tool.<tool_name>`
   - Automatic error and exception tracking
   - Tool-specific attributes:
     - Tool name
     - Arguments
     - Status
     - Error details
     - Model details
     - Profiling details
     - Validation details

3. **Resource Attribution**
   - Service name and version tracking
   - OpenTelemetry semantic conventions
   - Configurable resource attributes
   - Dynamic resource updates
   - Model resources
   - Profiling resources
   - Validation resources

4. **Error Handling**
   - Exception capture in spans
   - Error attribute propagation
   - Status code tracking
   - Automatic error context collection
   - Model error context
   - Profiling error context
   - Validation error context

### Metrics Architecture
1. **Metrics Collection**
   - OpenTelemetry SDK for metrics generation
   - OTLP exporter for metrics export
   - Configurable collection endpoint
   - Periodic metric export

2. **Tool Metrics**
   - Decorator pattern for automatic metrics collection
   - Standard metric types:
     - Histograms for durations
     - Counters for calls and errors
     - Up/down counters for active sessions
     - Observable gauges for system metrics
   - Consistent naming convention: `mcp.tool.*`
   - Automatic error tracking

3. **System Metrics**
   - Memory usage monitoring via psutil
   - Observable gauge implementation
   - Real-time resource tracking
   - Low-overhead collection

4. **Metric Configuration**
   - Dynamic endpoint configuration
   - Metric recreation on config changes
   - Global meter provider management
   - Metric reader configuration

## Profiling Architecture

### Core Profiling System
- **Global Profiler**: Singleton `MCPProfiler` instance manages profiling sessions
- **Profiling States**: Active/inactive state management with session persistence
- **Stats Management**: Automatic stats collection and file management
- **Tool Integration**: Automatic profiling integration via decorators

### Tool Profiling
- **Decorator Pattern**: `@profile_tool` decorator for automatic profiling
- **Stats Collection**:
  - Execution time tracking
  - Call count monitoring
  - Function-level statistics
  - Cumulative performance data
- **File Management**:
  - Temporary stats files for each profiling session
  - Automatic cleanup on errors
  - Stats file persistence for analysis

### Code Block Profiling
- **Dynamic Code Execution**: Profile arbitrary Python code blocks
- **Context Management**:
  - Isolated execution environment
  - Custom globals dictionary support
  - Temporary file handling for code and stats
- **Results Format**:
  - Human-readable stats output
  - Stats file references
  - Code file preservation

### Integration Points
- **Tool Registration**: Automatic profiling wrapper for all MCP tools
- **Session Management**: Start/stop profiling on demand
- **Stats Analysis**: Tools for examining profiling data
- **Error Handling**: Graceful error management with cleanup

### Best Practices
- **Resource Management**: Automatic cleanup of temporary files
- **State Handling**: Clear state transitions in profiling sessions
- **Data Access**: Structured access to profiling statistics
- **Tool Integration**: Non-intrusive profiling of existing tools 