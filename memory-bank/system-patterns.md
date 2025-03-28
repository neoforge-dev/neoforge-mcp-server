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

#### Core Components

1. CodeParser
```python
class CodeParser:
    """Parses source code into syntax trees using tree-sitter."""
    
    def __init__(self):
        self.parser = None
        self.language = None
        
    def setup_language(self, language: str):
        """Set up parser for a specific language."""
        pass
        
    def parse(self, source_code: str) -> Tree:
        """Parse source code into a syntax tree."""
        pass
```

2. CodeAnalyzer
```python
class CodeAnalyzer:
    """Analyzes code using tree-sitter syntax trees."""
    
    def __init__(self):
        self.reset_state()
        
    def analyze_tree(self, tree: Tree) -> Dict[str, List[Dict[str, Any]]]:
        """Analyze a syntax tree and extract code information."""
        pass
        
    def _extract_imports(self, node: Node) -> List[Dict[str, Any]]:
        """Extract import statements."""
        pass
        
    def _extract_functions(self, node: Node) -> List[Dict[str, Any]]:
        """Extract function definitions."""
        pass
        
    def _extract_classes(self, node: Node) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        pass
```

3. SymbolExtractor
```python
class SymbolExtractor:
    """Extracts symbols from syntax trees."""
    
    def __init__(self):
        self.current_scope = None
        self.symbols = {}
        self.references = {}
        
    def extract_symbols(self, tree: Tree) -> Dict[str, Any]:
        """Extract symbols from a syntax tree."""
        pass
        
    def _process_node(self, node: Node, parent_scope: Optional[str] = None):
        """Process a syntax tree node and extract symbols."""
        pass
```

#### Design Patterns

1. **Modular Architecture**
   - Separate concerns into Parser, Analyzer, and Extractor
   - Each component has a single responsibility
   - Easy to extend and maintain

2. **State Management**
   - Components maintain internal state
   - State is reset between operations
   - Scope tracking for accurate symbol resolution

3. **Error Handling**
   - Comprehensive try-except blocks
   - Detailed error logging
   - Graceful fallbacks for failures

4. **Visitor Pattern**
   - Tree traversal using visitor pattern
   - Node type-specific processing
   - Maintains context during traversal

5. **Builder Pattern**
   - Incremental construction of analysis results
   - Separate builders for different aspects
   - Clean separation of building logic

#### Data Structures

1. **Syntax Tree**
```python
class Tree:
    """Represents a syntax tree."""
    def __init__(self, root_node: Node):
        self.root_node = root_node
```

2. **Node**
```python
class Node:
    """Represents a syntax tree node."""
    def __init__(self, type: str, text: str = "", children: List["Node"] = None):
        self.type = type
        self.text = text
        self.children = children or []
```

3. **Symbol Table**
```python
SymbolTable = Dict[str, Dict[str, Any]]
"""
{
    'symbol_name': {
        'type': str,  # 'function', 'class', 'variable', 'import'
        'scope': str,  # Scope where symbol is defined
        'start': Tuple[int, int],  # Start position
        'end': Tuple[int, int],  # End position
        'params': List[str],  # For functions
        'bases': List[str],  # For classes
    }
}
"""
```

4. **Reference Table**
```python
ReferenceTable = Dict[str, List[Dict[str, Any]]]
"""
{
    'symbol_name': [
        {
            'scope': str,  # Scope where reference occurs
            'start': Tuple[int, int],  # Start position
            'end': Tuple[int, int],  # End position
        }
    ]
}
"""
```

#### Future Extensions

1. **Language Support**
```python
class LanguageParser:
    """Base class for language-specific parsers."""
    
    def parse(self, source: str) -> Tree:
        """Parse source code into a syntax tree."""
        pass

class PythonParser(LanguageParser):
    """Python-specific parser implementation."""
    pass

class JavaScriptParser(LanguageParser):
    """JavaScript-specific parser implementation."""
    pass
```

2. **Relationship Graph**
```python
class RelationshipGraph:
    """Builds and manages code relationship graphs."""
    
    def __init__(self):
        self.nodes = {}
        self.edges = []
        
    def add_relationship(self, source: str, target: str, type: str):
        """Add a relationship between symbols."""
        pass
        
    def get_dependencies(self, symbol: str) -> List[str]:
        """Get dependencies for a symbol."""
        pass
```

3. **Semantic Mapper**
```python
class SemanticMapper:
    """Maps code to semantic representations."""
    
    def __init__(self, model: str = "default"):
        self.model = model
        
    def embed_code(self, code: str) -> np.ndarray:
        """Generate embeddings for code."""
        pass
        
    def find_similar(self, query: str, threshold: float = 0.8) -> List[str]:
        """Find semantically similar code."""
        pass
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

## Code Understanding Tool Architecture

The Code Understanding Tool follows a layered architecture with the following components:

### Parser Layer
- **CodeParser** (`parser.py`)
  - Handles code parsing using tree-sitter (with fallback to AST)
  - Provides a unified interface for accessing syntax trees
  - Abstracts away differences between tree-sitter and AST
  - Uses mock objects for testing when tree-sitter is unavailable

### Analyzer Layer
- **CodeAnalyzer** (`analyzer.py`)
  - Extracts high-level code structures (imports, functions, classes, variables)
  - Provides a simplified view of code for quick analysis
  - Focuses on structural elements rather than detailed semantics

### Symbol Extraction Layer
- **SymbolExtractor** (`symbols.py` and `extractor.py`)
  - Extracts detailed symbol information from syntax trees
  - Handles scoping rules for proper symbol resolution
  - Tracks symbol references for relationship building
  - Maintains a scope hierarchy during tree traversal

### Relationship Graph Layer (Planned)
- **RelationshipExtractor** (`relationships.py`)
  - Identifies relationships between symbols (calls, inherits, imports, etc.)
  - Builds a graph representation of code relationships
  - Supports queries for finding dependencies and impacts

### Graph Representation Layer (Planned)
- **CodeGraph** (`graph.py`)
  - Provides a graph data structure for representing code relationships
  - Supports queries for navigating the code structure
  - Enables visualization and export capabilities

## Design Patterns

The Code Understanding Tool uses several design patterns:

1. **Visitor Pattern**
   - Tree traversal via `_process_node` methods
   - Node-specific processing methods for different node types
   - Maintains context during traversal (scope, etc.)

2. **Strategy Pattern**
   - Different strategies for processing different node types
   - Allows for language-specific extensions

3. **Composite Pattern**
   - Tree structure representation of code
   - Uniform interface for working with nodes

4. **Adapter Pattern**
   - Tree-sitter to internal representation adaptation
   - AST to internal representation adaptation
   - Mock objects for testing

5. **Factory Method**
   - Creating appropriate node handlers based on node type
   - Extensible for new languages or node types

## Error Handling Pattern

The code follows a consistent error handling approach:

1. Top-level methods have try-except blocks
2. Errors are logged with appropriate context
3. Fallback values are provided to maintain system stability
4. Error information is propagated to the caller for informed decisions
5. Custom error types for specific error scenarios

## Testing Strategy

The testing approach includes:

1. Mocking syntax trees for deterministic testing
2. Unit tests for individual components
3. Integration tests for end-to-end functionality
4. Error handling tests to ensure robustness
5. Parameterized tests for language-specific behavior

## Relationship Builder Patterns

### Node Creation Pattern
```python
def create_node(self, name: str, type: str, context: Context) -> Node:
    """Create a node with proper context and validation."""
    # Check if node already exists
    existing = self._find_existing_node(name, type)
    if existing:
        return existing
        
    # Create new node with context
    node = Node(
        name=name,
        type=type,
        file_path=context.file_path,
        start_line=context.start_line,
        end_line=context.end_line,
        properties=context.properties
    )
    
    # Validate and store
    self._validate_node(node)
    self._store_node(node)
    return node
```

### Edge Creation Pattern
```python
def create_edge(self, source: Node, target: Node, type: RelationType, context: Context) -> Edge:
    """Create an edge with proper validation and properties."""
    # Validate nodes exist
    if not self._node_exists(source) or not self._node_exists(target):
        raise ValueError("Source or target node does not exist")
        
    # Create edge with context
    edge = Edge(
        source=source,
        target=target,
        type=type,
        properties={
            'line_number': context.line_number,
            'scope': context.scope
        }
    )
    
    # Validate and store
    self._validate_edge(edge)
    self._store_edge(edge)
    return edge
```

### Reference Processing Pattern
```python
def process_reference(self, ref: Reference, context: Context) -> None:
    """Process a code reference with proper scoping."""
    try:
        # Find or create nodes
        source_node = self._get_scope_node(ref.scope)
        target_node = self._get_target_node(ref.name, ref.type)
        
        # Create relationship
        self.create_edge(
            source=source_node,
            target=target_node,
            type=self._get_relation_type(ref),
            context=context
        )
    except Exception as e:
        self._handle_reference_error(e, ref)
```

### Error Handling Pattern
```python
def _handle_reference_error(self, error: Exception, ref: Reference) -> None:
    """Handle errors during reference processing."""
    logger.error(f"Failed to process reference {ref.name}: {str(error)}")
    
    if isinstance(error, NodeNotFoundError):
        # Create placeholder node
        self._create_placeholder_node(ref)
    elif isinstance(error, ValidationError):
        # Log validation failure
        self._log_validation_failure(error)
    else:
        # Unexpected error
        raise ProcessingError(f"Failed to process reference: {str(error)}")
```

### Validation Patterns

1. **Node Validation**
```python
def _validate_node(self, node: Node) -> None:
    """Validate node properties and relationships."""
    if not node.name:
        raise ValidationError("Node must have a name")
        
    if not node.type:
        raise ValidationError("Node must have a type")
        
    if node.type not in VALID_NODE_TYPES:
        raise ValidationError(f"Invalid node type: {node.type}")
```

2. **Edge Validation**
```python
def _validate_edge(self, edge: Edge) -> None:
    """Validate edge properties and relationships."""
    if not edge.source or not edge.target:
        raise ValidationError("Edge must have source and target")
        
    if edge.type not in RelationType:
        raise ValidationError(f"Invalid edge type: {edge.type}")
        
    if edge.source.id == edge.target.id:
        raise ValidationError("Self-referential edges not allowed")
```

### Testing Patterns

1. **Fixture Pattern**
```python
@pytest.fixture
def sample_context():
    """Create a test context with common test data."""
    return Context(
        file_path="test.py",
        start_line=1,
        end_line=10,
        scope="global",
        properties={}
    )
```

2. **Test Case Pattern**
```python
def test_process_reference(builder, sample_context):
    """Test reference processing with validation."""
    # Arrange
    ref = Reference(name="test", type="call", scope="main")
    
    # Act
    builder.process_reference(ref, sample_context)
    
    # Assert
    graph = builder.get_relationships()
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0
    
    # Verify relationships
    edge = next(iter(graph.edges))
    assert edge.source.name == "main"
    assert edge.target.name == "test"
    assert edge.type == RelationType.CALLS
```

## Architecture Overview

### Core Components
1. **Parser Layer**
   - Language-specific parsers (Python, JavaScript, Swift)
   - Tree-sitter integration
   - Abstract syntax tree (AST) generation
   - Error handling and recovery

2. **Analyzer Layer**
   - Code structure analysis
   - Symbol extraction
   - Type inference
   - Control flow analysis
   - Data flow analysis

3. **Semantic Layer**
   - Type system
   - Context tracking
   - Symbol resolution
   - Cross-language references
   - Impact analysis

4. **Graph Layer**
   - Relationship building
   - Graph representation
   - Query interface
   - Visualization support

## Design Patterns

### Language Support Patterns
1. **Adapter Pattern**
   - Language-specific parser adapters
   - Unified AST representation
   - Common symbol interface
   - Cross-language type mapping

2. **Strategy Pattern**
   - Language-specific analysis strategies
   - Parser selection strategy
   - Type inference strategy
   - Reference resolution strategy

3. **Factory Pattern**
   - Language-specific component creation
   - Parser factory
   - Analyzer factory
   - Graph factory

### Semantic Analysis Patterns
1. **Visitor Pattern**
   - AST traversal
   - Type inference
   - Control flow analysis
   - Data flow analysis

2. **Observer Pattern**
   - Analysis progress tracking
   - Error reporting
   - Performance monitoring
   - Cache invalidation

3. **Builder Pattern**
   - Semantic graph construction
   - Type system building
   - Context building
   - Relationship building

### Testing Patterns
1. **Mock Pattern**
   - Parser mocking
   - File system mocking
   - Cache mocking
   - Performance mocking

2. **Factory Pattern**
   - Test data generation
   - Mock object creation
   - Test scenario building
   - Performance test setup

3. **Strategy Pattern**
   - Test execution strategy
   - Coverage strategy
   - Performance strategy
   - Language-specific test strategy

## Implementation Guidelines

### Language Support
1. **Parser Implementation**
   - Use tree-sitter for all languages
   - Implement language detection
   - Create unified AST representation
   - Handle language-specific errors

2. **Symbol Extraction**
   - Language-specific scope rules
   - Cross-language references
   - Type information extraction
   - Context preservation

3. **Type System**
   - Language-specific type rules
   - Type inference algorithms
   - Type compatibility checking
   - Cross-language type mapping

### Semantic Analysis
1. **Control Flow**
   - CFG construction
   - Path analysis
   - Reachability analysis
   - Dead code detection

2. **Data Flow**
   - Variable tracking
   - Value propagation
   - Use-def chains
   - Live variable analysis

3. **Context Analysis**
   - Scope tracking
   - Symbol resolution
   - Type context
   - Call context

## Testing Strategy

### Unit Testing
1. **Parser Tests**
   - Language-specific syntax
   - Error handling
   - Edge cases
   - Performance

2. **Analyzer Tests**
   - Symbol extraction
   - Type inference
   - Control flow
   - Data flow

3. **Graph Tests**
   - Node creation
   - Edge creation
   - Relationship building
   - Query interface

### Integration Testing
1. **Cross-language Tests**
   - Multi-language projects
   - Reference resolution
   - Type compatibility
   - Performance impact

2. **End-to-end Tests**
   - Complete analysis pipeline
   - Large codebases
   - Real-world scenarios
   - Performance benchmarks

### Performance Testing
1. **Scalability Tests**
   - Large codebases
   - Multiple languages
   - Complex relationships
   - Memory usage

2. **Optimization Tests**
   - Caching effectiveness
   - Incremental analysis
   - Parallel processing
   - Resource utilization

## Error Handling

### Error Types
1. **Parser Errors**
   - Syntax errors
   - Grammar errors
   - File access errors
   - Encoding errors

2. **Analysis Errors**
   - Type errors
   - Scope errors
   - Reference errors
   - Context errors

3. **Graph Errors**
   - Node errors
   - Edge errors
   - Cycle errors
   - Query errors

### Recovery Strategies
1. **Parser Recovery**
   - Error location
   - Partial parsing
   - Error reporting
   - Recovery suggestions

2. **Analysis Recovery**
   - Partial analysis
   - Error isolation
   - Context preservation
   - Incremental updates

3. **Graph Recovery**
   - Partial graph
   - Error isolation
   - State preservation
   - Incremental updates

## Performance Considerations

### Optimization Strategies
1. **Caching**
   - Parse results
   - Analysis results
   - Graph state
   - Type information

2. **Incremental Analysis**
   - Changed files
   - Affected symbols
   - Updated relationships
   - Modified types

3. **Parallel Processing**
   - File parsing
   - Symbol analysis
   - Graph building
   - Type inference

### Resource Management
1. **Memory Usage**
   - AST size
   - Graph size
   - Cache size
   - Temporary objects

2. **CPU Usage**
   - Parse time
   - Analysis time
   - Graph time
   - Query time

3. **I/O Usage**
   - File access
   - Cache access
   - Graph storage
   - Result output 