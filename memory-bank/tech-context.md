# Terminal Command Runner MCP - Tech Context

## Technology Stack

### Core Technologies
- Python 3.8+
- FastAPI for API server
- Server-Sent Events (SSE) for transport protocol
- Traefik for proxy and routing
- Click for CLI framework
- Rich for terminal UI
- OpenTelemetry for observability
- pytest for testing
- cmd for debugging interface
- JSON for configuration storage
- Anthropic API for code generation
- OpenAI API for code generation
- Transformers for local models
- cProfile for profiling

### Networking Stack
- FastAPI for HTTP server
- Server-Sent Events (SSE) for streaming
- Traefik for reverse proxy and routing
- SSH for secure server management
- Socket connections for health checks
- Firewall configuration with iptables
- tcpdump for network diagnostics
- Port configuration management
- Network monitoring tools

### Monitoring Stack
- OpenTelemetry SDK for metrics collection
- Prometheus for metrics storage and alerting
- AlertManager for alert management
- Grafana for visualization
- Docker Compose for deployment
- psutil for system metrics
- Model performance tracking
- Profiling data collection
- Validation metrics
- Connection status monitoring

### Debugging Stack
- cmd module for CLI interface
- Rich for output formatting
- inspect for introspection
- pdb for debugging support
- threading for synchronization
- functools for decorators
- Model debugging tools
- Profiling analysis
- Validation debugging

### Development Tools
- Black for code formatting
- flake8 for linting
- mypy for type checking
- pytest for testing
- coverage.py for code coverage
- Bandit for security scanning
- Ruff for style checking
- cProfile for profiling
- Model development tools

## Workspace Management
- WorkspaceConfig dataclass for configuration
- WorkspaceManager class for workspace operations
- JSON-based configuration persistence
- Directory-based workspace isolation
- Tool-specific workspace directories
- Environment variable management
- Path management
- Settings management
- Rich console output
- Model workspace management
- Profiling workspace management
- Validation workspace management

## Development Setup

### Prerequisites
1. Python 3.8 or higher
2. pip package manager
3. virtualenv or similar virtual environment tool
4. Docker and Docker Compose
5. CUDA support (optional, for local models)
6. 16GB+ RAM (recommended for local models)

### Installation
1. Create and activate virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Install development dependencies: `pip install -r requirements-dev.txt`
4. Start monitoring stack: `docker-compose up -d`
5. Set up API keys for code generation models
6. Configure local model paths

### Running the Server
1. Start the server: `python server.py [--debug]`
2. Access API at `http://localhost:9001`
3. SSE endpoint at `http://localhost:9001/sse`
4. Access Grafana at `http://localhost:3000`
5. Access Prometheus at `http://localhost:9090`
6. Access AlertManager at `http://localhost:9093`
7. Access profiling dashboard at `http://localhost:9001/profiling`

### Using the CLI
1. Run CLI commands: `python cli.py [command] [options] [--debug]`
2. Available command groups:
   - `command`: Execute and manage commands
   - `file`: File operations
   - `system`: System operations
   - `dev`: Development tools
   - `debug`: Debugging tools
   - `generate`: Code generation tools
   - `validate`: Code validation tools
   - `profile`: Profiling tools

### Debugging Tools
1. Start debugger: Add `--debug` flag
2. Available commands:
   - `list_tools`: Show available tools
   - `inspect`: View tool implementation
   - `break`: Set breakpoints
   - `watch`: Watch variables
   - `info`: Show debug info
   - `step`: Step execution
   - `continue`: Resume execution
   - `locals`: Show variables
   - `stack`: Show call stack
   - `model`: Model debugging
   - `profile`: Profiling analysis
   - `validate`: Validation debugging

## Workspace Commands
```bash
# List workspaces
mcp workspace list

# Create workspace
mcp workspace create <name> [description]

# Delete workspace
mcp workspace delete <name>

# Activate workspace
mcp workspace activate <name>

# Deactivate workspace
mcp workspace deactivate

# Add tool to workspace
mcp workspace tool add <name> <path>

# Remove tool from workspace
mcp workspace tool remove <name>

# Set environment variable
mcp workspace env set <key> <value>

# Add path to workspace
mcp workspace path add <path>

# Remove path from workspace
mcp workspace path remove <path>

# Update settings
mcp workspace settings update <key> <value>

# Show workspace info
mcp workspace info

# Configure model settings
mcp workspace model config <model> <key> <value>

# Set up profiling
mcp workspace profile setup <options>

# Configure validation
mcp workspace validate config <options>
```

## Debugging Commands
```bash
# List available tools
debug list_tools

# Inspect tool implementation
debug inspect <tool_name>

# Set breakpoint
debug break <tool_name> <line_number>

# Watch variable
debug watch <variable_name>

# Show debug info
debug info

# Step through execution
debug step

# Continue execution
debug continue

# Show local variables
debug locals

# Show call stack
debug stack

# Quit debugger
debug quit

# Model debugging
debug model <command> [options]

# Profiling analysis
debug profile <command> [options]

# Validation debugging
debug validate <command> [options]
```

## Technical Constraints

### Performance
- Command execution timeout limits
- Resource usage monitoring
- Profiling overhead management
- Metric collection overhead
- Alert processing latency
- Debug mode overhead
- Workspace switching overhead
- Configuration persistence latency
- Tool isolation impact
- Model inference time limits
- Profiling data size limits
- Validation performance impact

### Security
- Input validation
- Command execution restrictions
- File access controls
- Monitoring access control
- Alert access control
- Debug access control
- Workspace isolation
- Tool access control
- Environment separation
- Model access control
- Profiling data security
- Validation security

### Scalability
- Concurrent command execution
- Resource management
- Connection pooling
- Metric storage scaling
- Alert handling capacity
- Debug session management
- Workspace state consistency
- Tool availability
- Configuration persistence
- Model scaling
- Profiling data scaling
- Validation scaling

## Dependencies

### Core Dependencies
- FastAPI: Web framework
- uvicorn: ASGI server
- Click: CLI framework
- Rich: Terminal UI
- requests: HTTP client
- psutil: System monitoring
- OpenTelemetry: Observability
- anthropic: Claude API
- openai: OpenAI API
- transformers: Local models
- torch: Deep learning
- cProfile: Profiling

### Monitoring Dependencies
- opentelemetry-api: Core API
- opentelemetry-sdk: Implementation
- opentelemetry-exporter-prometheus: Prometheus export
- opentelemetry-exporter-otlp: OTLP export
- prometheus-client: Prometheus integration
- psutil: System metrics
- Model metrics collector
- Profiling metrics collector
- Validation metrics collector

### Debugging Dependencies
- cmd: Command interface
- inspect: Code introspection
- rich: Output formatting
- pdb: Python debugger
- threading: Synchronization
- functools: Decorators
- Model debugging tools
- Profiling analysis tools
- Validation debugging tools

### Development Dependencies
- pytest: Testing framework
- black: Code formatter
- flake8: Linter
- mypy: Type checker
- coverage: Code coverage
- Bandit: Security scanner
- Ruff: Style checker
- cProfile: Profiler
- Model development tools

### Alerting Dependencies
- Prometheus: Alert rules engine
- AlertManager: Alert routing
- Slack API: Notifications
- Email: Alternative notifications
- Templates: Alert formatting
- Model alerting
- Profiling alerts
- Validation alerts

### Workspace Dependencies
- pathlib: Path management
- dataclasses: Workspace configuration
- typing: Type hints
- shutil: Environment management
- json: Configuration storage
- Model workspace management
- Profiling workspace management
- Validation workspace management

## Integration Points

### External Systems
- Command execution system
- File system
- Process management
- System monitoring
- Alert notification services
- Debug interface
- Model APIs
- Profiling system
- Validation system

### Internal Components
- API server
- CLI interface
- Tool registry
- Profiling system
- Metrics collection
- Alert management
- Debug system
- Model management
- Profiling management
- Validation management

### Monitoring Components
- OpenTelemetry SDK
- OpenTelemetry Collector
- Prometheus server
- Grafana dashboard
- AlertManager
- Notification channels
- Metrics collection
- Alert management
- Dashboard system
- Model monitoring
- Profiling monitoring
- Validation monitoring

### Debugging Components
- Interactive console
- Breakpoint manager
- Variable watcher
- History tracker
- Stack inspector
- Tool inspector
- Model debugging tools
- Profiling analysis tools
- Validation debugging tools

## Configuration

### Server Configuration
- Host: localhost (default)
- Port: 9001 (default)
- Debug mode toggle
- Logging level

### CLI Configuration
- Default timeout values
- Output formatting options
- Color scheme customization
- Command history

### Monitoring Configuration
- Metric collection interval
- Retention period
- Dashboard refresh rate
- Alert thresholds
- Export endpoints

### Debug Configuration
- Tool registration
- Breakpoint settings
- Watch variables
- History size
- Output format
- Session persistence

### Alert Configuration
- Rule definitions
- Notification routing
- Channel settings
- Template customization
- Grouping policies

### Workspace Configuration
- Base directory: ~/.mcp/workspaces
- Config file: config.json
- Tool directory: tools/
- Data directory: data/
- Log directory: logs/
- Temp directory: temp/

## Deployment

### Requirements
- Python runtime
- System dependencies
- Configuration files
- Access permissions
- Docker environment
- Debug capabilities

### Process
1. Install dependencies
2. Configure environment
3. Start monitoring stack
4. Configure alerts
5. Enable debugging
6. Start server
7. Verify connectivity

## Monitoring

### System Metrics
- CPU usage
- Memory usage
- Disk usage
- Process count
- Network I/O

### Tool Metrics
- Execution count
- Error rate
- Response time
- Active tools
- Resource usage

### Alert Types
- Resource alerts
- Performance alerts
- Error rate alerts
- Prediction alerts
- Health check alerts

### Alert Channels
- Slack notifications
- Email notifications
- Web hooks
- Custom channels
- Alert history

## Testing

### Test Types
- Unit tests
- Integration tests
- System tests
- Load tests
- Alert tests
- Debug tests

### Test Coverage
- Code coverage targets
- Critical path testing
- Error handling
- Edge cases
- Alert validation
- Debug scenarios

## Documentation

### Code Documentation
- Docstrings
- Type hints
- Comments
- Examples
- Alert descriptions
- Debug instructions

### User Documentation
- API documentation
- CLI usage guide
- Tool descriptions
- Alert response guide
- Debug guide
- Runbook templates

## Future Considerations

### Planned Features
- Interactive debugging
- Workspace management
- Advanced profiling
- Custom tool development
- Alert correlation
- Remote debugging
- Templates
- Sharing
- Versioning
- Migration
- Plugins

### Technical Debt
- Test coverage improvements
- Documentation updates
- Code organization
- Performance optimization
- Alert refinement
- Debug optimization
- Configuration format
- Tool isolation
- Error handling

## API Structure

The API consists of tool functions that can be invoked remotely:

1. **Command Execution**:
   - `execute_command`: Run a command with timeout control
   - `read_output`: Stream output from a running command
   - `force_terminate`: Stop a running command

2. **Process Management**:
   - `list_sessions`: Show active command sessions
   - `list_processes`: List system processes
   - `kill_process`: Terminate a process by PID

3. **Command Control**:
   - `block_command`: Add a command to the blacklist
   - `unblock_command`: Remove a command from the blacklist

4. **File Operations**:
   - `read_file`: Read file contents with size limits
   - `write_file`: Write content to a file
   - `create_directory`: Create a new directory
   - `list_directory`: List directory contents
   - `move_file`: Move or rename files
   - `search_files`: Find files matching a pattern
   - `get_file_info`: Get metadata about a file

5. **Development Tools**:
   - `install_dependency`: Install Python packages using uv
   - `run_tests`: Execute tests with proper isolation
   - `format_code`: Run ruff formatting
   - `lint_code`: Run ruff linting
   - `filter_output`: Process and format long command outputs

6. **Code Analysis**:
   - `analyze_codebase`: Static code analysis
   - `monitor_performance`: System performance tracking
   - `manage_llm_context`: LLM context optimization
   - `enhanced_testing`: Advanced test execution

7. **Utilities**:
   - `system_info`: Get system information
   - `calculate`: Evaluate a mathematical expression
   - `context_length`: Track LLM context usage

## Performance Considerations

- **Output Streaming**: Efficient handling of process output
- **Resource Management**: Proper cleanup of resources for long-running processes
- **Memory Usage**: Careful handling of large file content or command output
- **Threading**: Proper synchronization for concurrent operations
- **Context Length**: Monitoring and managing LLM context usage
- **Test Performance**: Parallel test execution and efficient coverage tracking
- **System Monitoring**: Low-overhead performance metrics collection

## Observability Stack

### Distributed Tracing
- OpenTelemetry integration for distributed tracing
- OTLP exporter configured for trace collection
- Automatic tracing for all MCP tools via decorator pattern
- Configurable service name and version
- Default endpoint: http://localhost:4317

### Dependencies
- OpenTelemetry packages:
  - opentelemetry-api==1.31.1
  - opentelemetry-sdk==1.31.1
  - opentelemetry-exporter-otlp==1.31.1
  - opentelemetry-semantic-conventions==0.52b1

### Metrics Collection
- OpenTelemetry Metrics integration
- OTLP exporter for metrics collection
- Default endpoint: http://localhost:4317
- Key metrics:
  - Tool execution duration (histogram)
  - Tool call count (counter)
  - Error count (counter)
  - Active sessions (up/down counter)
  - Memory usage (observable gauge)

### System Dependencies
- psutil for system metrics collection
- OpenTelemetry metrics packages:
  - opentelemetry-sdk-metrics
  - opentelemetry-exporter-otlp-proto-grpc

### Profiling Tools
- cProfile integration for Python profiling
- Custom MCP profiler for tool-specific profiling
- Features:
  - Global profiling session management
  - Per-tool profiling with stats collection
  - Code block profiling
  - Stats file management
- Profiling data:
  - Execution time
  - Call counts
  - Cumulative statistics
  - Function-level performance

### Development Tools
- Built-in profiling tools:
  - start_profiling: Start global profiling session
  - stop_profiling: Stop profiling and get results
  - get_profiling_stats: Analyze stats files
  - profile_code: Profile arbitrary Python code

## L3 Coding Agent Tools

### Autonomous Execution Tools
- Plan Generation
  - Task breakdown algorithms
  - Dependency resolution
  - Resource estimation
  - Risk assessment
  - Checkpoint planning

- Execution Management
  - State tracking
  - Progress monitoring
  - Error detection
  - Recovery strategies
  - Rollback mechanisms

- Feature Implementation
  - Code scaffolding
  - Template generation
  - Best practices enforcement
  - Integration patterns
  - Testing strategies

### Validation Tools
- Code Quality Analysis
  - Static analysis
  - Dynamic analysis
  - Style checking
  - Complexity metrics
  - Best practices validation

- Test Simulation
  - Unit test generation
  - Integration test simulation
  - Edge case detection
  - Coverage analysis
  - Performance testing

- Impact Analysis
  - Dependency impact
  - Performance impact
  - Security implications
  - Resource utilization
  - Compatibility checking

### Context Awareness Tools
- Codebase Analysis
  - AST parsing
  - Semantic analysis
  - Pattern detection
  - Architecture mapping
  - Dependency tracking

- Context Management
  - State persistence
  - History tracking
  - Pattern learning
  - Knowledge base
  - Context restoration

- System Understanding
  - Architecture analysis
  - Component relationships
  - Interface mapping
  - Data flow analysis
  - Control flow analysis

### Iterative Problem-Solving
- Solution Management
  - Version control
  - Alternative tracking
  - Progress monitoring
  - Success metrics
  - Failure analysis

- Learning System
  - Pattern recognition
  - Solution optimization
  - Feedback integration
  - Knowledge persistence
  - Adaptation strategies

- Optimization Engine
  - Performance analysis
  - Resource optimization
  - Code simplification
  - Refactoring suggestions
  - Best practices application

## Technical Requirements

### Autonomous Execution
- Safe execution environment
- State management system
- Rollback capabilities
- Progress tracking
- Error recovery mechanisms

### Validation System
- Real-time validation
- Test simulation framework
- Impact analysis tools
- Security scanning
- Performance profiling

### Context Management
- Graph database for relationships
- Pattern recognition models
- Knowledge persistence
- State management
- History tracking

### Iterative Learning
- Version control system
- Pattern matching engine
- Learning persistence
- Feedback processing
- Optimization algorithms

## Dependencies

### Core Systems
- Graph databases (Neo4j/TigerGraph)
- Machine learning frameworks (PyTorch/TensorFlow)
- AST parsing tools (ast/astroid)
- Pattern matching engines (regex/automata)
- State management systems

### Analysis Tools
- Static analyzers (pylint/mypy)
- Dynamic analyzers
- Security scanners
- Performance profilers
- Coverage tools

### Learning Systems
- Pattern recognition models
- Optimization algorithms
- Knowledge bases
- Feedback processors
- Adaptation engines

### Integration Tools
- Version control systems
- CI/CD pipelines
- Testing frameworks
- Documentation generators
- Code formatters

## Performance Considerations

### Execution Speed
- Task breakdown optimization
- Parallel execution
- Resource management
- Cache utilization
- State persistence

### Memory Usage
- Context storage optimization
- Pattern database efficiency
- History management
- Cache strategies
- Resource cleanup

### Processing Overhead
- Analysis optimization
- Validation efficiency
- Learning system performance
- Pattern matching speed
- State tracking overhead

## Security Considerations

### Code Execution
- Sandboxed environments
- Permission management
- Resource limits
- Input validation
- Output sanitization

### Data Management
- Secure storage
- Access control
- Encryption
- Audit logging
- Compliance checking

### Integration Security
- API security
- Authentication
- Authorization
- Rate limiting
- Data validation

## Technical Constraints

### Performance
- LLM response times
- Token usage optimization
- Resource management
- Cache implementation

### Security
- API key management
- Code execution isolation
- Web access controls
- Dependency validation

### Scalability
- Model switching
- Parallel processing
- Resource allocation
- Cache management

## Performance Considerations

- **Output Streaming**: Efficient handling of process output
- **Resource Management**: Proper cleanup of resources for long-running processes
- **Memory Usage**: Careful handling of large file content or command output
- **Threading**: Proper synchronization for concurrent operations
- **Context Length**: Monitoring and managing LLM context usage
- **Test Performance**: Parallel test execution and efficient coverage tracking
- **System Monitoring**: Low-overhead performance metrics collection

## Observability Stack

### Distributed Tracing
- OpenTelemetry integration for distributed tracing
- OTLP exporter configured for trace collection
- Automatic tracing for all MCP tools via decorator pattern
- Configurable service name and version
- Default endpoint: http://localhost:4317

### Dependencies
- OpenTelemetry packages:
  - opentelemetry-api==1.31.1
  - opentelemetry-sdk==1.31.1
  - opentelemetry-exporter-otlp==1.31.1
  - opentelemetry-semantic-conventions==0.52b1

### Metrics Collection
- OpenTelemetry Metrics integration
- OTLP exporter for metrics collection
- Default endpoint: http://localhost:4317
- Key metrics:
  - Tool execution duration (histogram)
  - Tool call count (counter)
  - Error count (counter)
  - Active sessions (up/down counter)
  - Memory usage (observable gauge)

### System Dependencies
- psutil for system metrics collection
- OpenTelemetry metrics packages:
  - opentelemetry-sdk-metrics
  - opentelemetry-exporter-otlp-proto-grpc

### Profiling Tools
- cProfile integration for Python profiling
- Custom MCP profiler for tool-specific profiling
- Features:
  - Global profiling session management
  - Per-tool profiling with stats collection
  - Code block profiling
  - Stats file management
- Profiling data:
  - Execution time
  - Call counts
  - Cumulative statistics
  - Function-level performance

### Development Tools
- Built-in profiling tools:
  - start_profiling: Start global profiling session
  - stop_profiling: Stop profiling and get results
  - get_profiling_stats: Analyze stats files
  - profile_code: Profile arbitrary Python code

## Code Generation & Analysis Tools

### Code Generation
- **Models**:
  - API-based:
    - Claude-3-Sonnet (Anthropic)
    - GPT-4 (OpenAI)
  - Local:
    - Code Llama (34B Python)
    - StarCoder
- **Features**:
  - Multi-model support
  - Context-aware generation
  - Token tracking
  - Performance metrics
  - Error handling

### Code Validation
- **Checks**:
  - Syntax validation (AST-based)
  - Style checking (Ruff)
  - Complexity analysis (McCabe)
  - Security scanning (Bandit)
  - Performance analysis
- **Features**:
  - Comprehensive validation suite
  - Human-readable summaries
  - Detailed recommendations
  - Multi-language support (planned)

## Technical Requirements

### System Requirements
- Python 3.8+
- CUDA support (optional, for local models)
- 16GB+ RAM (32GB+ recommended for local models)
- SSD storage for model weights

### Dependencies
- **Core Libraries**:
  - anthropic
  - openai
  - torch
  - transformers
  - bandit
  - ruff
- **Optional Libraries**:
  - pytest (for testing)
  - black (for formatting)
  - mypy (for type checking)

### API Requirements
- Anthropic API key (for Claude)
- OpenAI API key (for GPT-4)
- Internet connection for API models

## Performance Constraints

### Code Generation
- API models:
  - Response time: < 2s
  - Token limit: Model-specific
  - Rate limits: Provider-specific
- Local models:
  - Response time: Hardware-dependent
  - Memory usage: 16GB+ per model
  - GPU memory: 24GB+ recommended

### Code Validation
- Validation time: < 100ms per check
- Memory usage: < 1GB
- CPU usage: Moderate

## Security Considerations

### API Security
- Secure API key storage
- Rate limiting
- Request validation
- Response sanitization

### Code Security
- Sandboxed execution
- Input validation
- Output sanitization
- Dependency scanning

## Implementation Details

### Relationship Builder
- **Core Components**
  - `Graph`: Base data structure for storing nodes and edges
  - `Node`: Represents code elements (functions, classes, variables)
  - `Edge`: Represents relationships between nodes
  - `RelationType`: Enum for relationship types
  - `RelationshipBuilder`: Main class for building relationships

- **Node Types**
  - `function`: Function definitions
  - `method`: Class methods
  - `class`: Class definitions
  - `variable`: Variables and parameters
  - `module`: Imported modules
  - `import`: Imported symbols
  - `attribute`: Class attributes

- **Relationship Types**
  - `CONTAINS`: Parent-child relationships
  - `CALLS`: Function/method calls
  - `INHERITS`: Class inheritance
  - `IMPORTS`: Module imports
  - `REFERENCES`: Variable/attribute references

### Current Implementation Status
- **Working Features**
  - Basic graph operations (add/remove nodes/edges)
  - Node and edge property management
  - Relationship type handling
  - Test infrastructure

- **In Progress**
  - Reference extraction and processing
  - Scope management
  - Error handling improvements
  - Test coverage expansion

- **Known Issues**
  - Node creation during file analysis
  - Edge creation for references
  - Directory analysis completeness
  - Test coverage gaps

### Technical Debt
1. **Error Handling**
   - Need more comprehensive error types
   - Better error recovery mechanisms
   - Improved error logging

2. **Validation**
   - Input validation for node/edge creation
   - Relationship validation rules
   - Property validation

3. **Testing**
   - More edge case coverage
   - Error handling tests
   - Integration tests

4. **Documentation**
   - API documentation
   - Usage examples
   - Error handling guide

## Architecture Patterns

### Model Management
- Factory pattern for model selection
- Strategy pattern for generation
- Observer pattern for metrics
- Decorator pattern for validation

### Error Handling
- Comprehensive error types
- Graceful degradation
- Detailed error messages
- Recovery strategies

### Metrics Collection
- Generation time
- Token usage
- Success rates
- Resource utilization

## Development Guidelines

### Code Style
- PEP 8 compliance
- Type hints required
- Docstrings required
- Comprehensive tests

### Testing Strategy
- Unit tests for core functions
- Integration tests for workflows
- Performance benchmarks
- Security tests

### Documentation
- API documentation
- Usage examples
- Configuration guide
- Troubleshooting guide

## Future Considerations

### Planned Enhancements
- Additional model support
- Language-specific validation
- Performance optimization
- Caching system
- Distributed execution

### Technical Debt
- Token tracking for local models
- Security scanning rules
- Performance analysis patterns
- Environment configuration
- Test coverage

## Server Configuration

### Transport Protocols
- **SSE (Server-Sent Events)**: Primary transport protocol for streaming data from server to client
- **HTTP REST API**: Used for standard request-response communication
- **WebSocket**: Not currently supported but being considered for future implementations
- **SSH**: Used for server management and tunneling

### Port Configuration
- Port 9001: MCP server (previously using port 7443)
- Port 8080: Reserved for additional services
- Port 80: Traefik HTTP entrypoint
- Port 443: Traefik HTTPS entrypoint
- Port 22: SSH access
- Port 8000: Development server

### Proxy Setup
- Traefik as reverse proxy
- Dynamic configuration via config files
- Path-based routing (/mcp for MCP server)
- Middleware for path stripping
- Health checks for services
- Automatic TLS certificate handling
- Load balancing capability

### Firewall Configuration
- iptables for firewall management
- Specific port allowances for required services
- Default deny policy for security
- SSH access always enabled
- Monitoring of connection attempts
- Rate limiting for protection

### SSH Tunnel Setup
```bash
# Create SSH tunnel to access MCP server
ssh -L 9001:localhost:9001 user@server

# Access MCP server locally
curl http://localhost:9001
```

### Server Hosting
- DigitalOcean cloud hosting
- Linux-based OS (Ubuntu)
- Root access for management
- Automated service management
- systemd for service control
- Centralized logging
- Regular backups

## Network Troubleshooting Commands
```bash
# Check if server is running
ps aux | grep mcp

# Test server connectivity
curl -v http://localhost:9001

# Check open ports
ss -tulpn | grep 9001

# Check firewall status
iptables -L -n -v

# Monitor network traffic
tcpdump -i any port 9001 -n

# Trace network route
traceroute host

# Set up SSH tunnel
ssh -L 9001:localhost:9001 user@server

# Test proxy configuration
curl -v http://server/mcp

# Check proxy logs
journalctl -u traefik

# Restart MCP server
kill -9 PID && cd /path/to/server && . .venv/bin/activate && mcp dev server.py &
```

## Development Environment

### Language & Runtime
- Python 3.13.0
- Virtual environment management with venv
- Package management with pip

### Dependencies
- tree-sitter: Language-agnostic parser
- pytest: Testing framework
- pytest-cov: Coverage reporting
- logging: Standard library logging

### Development Tools
- VSCode/Cursor as primary IDE
- Git for version control
- pytest for testing
- Coverage.py for test coverage

## Project Structure

### Core Directories
```
server/
├── code_understanding/
│   ├── __init__.py
│   ├── parser.py
│   ├── analyzer.py
│   ├── extractor.py
│   ├── symbols.py
│   └── build_languages.py
├── core.py
└── llm.py

tests/
├── __init__.py
└── test_parser.py

memory-bank/
├── project-brief.md
├── product-context.md
├── active-context.md
├── system-patterns.md
├── tech-context.md
└── progress.md
```

### Key Files
- `parser.py`: Code parsing with tree-sitter
- `analyzer.py`: Syntax tree analysis
- `extractor.py`: Symbol extraction
- `symbols.py`: Symbol management
- `build_languages.py`: Tree-sitter language building

## Technical Constraints

### Performance
- Memory usage for large codebases
- Parse time for large files
- Graph traversal efficiency
- Cache management

### Security
- Code execution safety
- Input validation
- Resource limits
- Access control

### Scalability
- Incremental analysis
- Parallel processing
- Resource management
- Cache invalidation

## Integration Points

### Tree-sitter
- Language-agnostic parsing
- Syntax tree generation
- Language support management
- Error handling

### MCP Interface
- Command handling
- Response formatting
- Error reporting
- State management

### Testing Framework
- Unit tests
- Integration tests
- Coverage reporting
- Performance testing

## Development Practices

### Code Style
- PEP 8 compliance
- Type hints
- Comprehensive docstrings
- Clear error messages

### Testing
- Unit tests for components
- Integration tests for workflows
- Coverage targets (>80%)
- Performance benchmarks

### Documentation
- Inline documentation
- API documentation
- Usage examples
- Architecture docs

### Version Control
- Feature branches
- Pull requests
- Code review
- Version tagging

## Future Considerations

### Language Support
- Additional tree-sitter parsers
- Language-specific analysis
- Custom parsing rules
- Language detection

### Performance Optimization
- Caching strategies
- Parallel processing
- Memory management
- Resource pooling

### Tool Integration
- IDE plugins
- CI/CD integration
- API endpoints
- Monitoring tools

### Scalability
- Distributed processing
- Load balancing
- Resource scaling
- Data partitioning

# Technical Context

## Technology Stack

### Core Technologies
1. **Python 3.13**
   - Main implementation language
   - Type hints support
   - Async/await support
   - Performance improvements

2. **Tree-sitter**
   - Code parsing
   - Language support
   - Incremental parsing
   - Error recovery

3. **FastAPI**
   - REST API
   - WebSocket support
   - OpenAPI documentation
   - Performance optimization

### Language Support
1. **Python**
   - Tree-sitter Python grammar
   - Type hints
   - Decorators
   - Async/await

2. **JavaScript**
   - Tree-sitter JavaScript grammar
   - ES6+ features
   - Modules
   - TypeScript support

3. **Swift**
   - Tree-sitter Swift grammar
   - Type system
   - Protocols
   - Extensions

### Analysis Tools
1. **Static Analysis**
   - Type inference
   - Control flow analysis
   - Data flow analysis
   - Symbol resolution

2. **Graph Processing**
   - NetworkX
   - Graph visualization
   - Query optimization
   - Path analysis

3. **Performance Tools**
   - Profiling
   - Memory tracking
   - Cache analysis
   - Resource monitoring

## Development Setup

### Environment
1. **Python Environment**
   - Virtual environment
   - Dependency management
   - Development tools
   - Testing framework

2. **Language Support**
   - Tree-sitter setup
   - Grammar compilation
   - Language detection
   - Cross-language testing

3. **Analysis Tools**
   - Static analysis setup
   - Graph processing
   - Performance tools
   - Visualization tools

### Dependencies
1. **Core Dependencies**
   - tree-sitter
   - fastapi
   - pydantic
   - networkx

2. **Language Dependencies**
   - tree-sitter-python
   - tree-sitter-javascript
   - tree-sitter-swift
   - language-specific tools

3. **Analysis Dependencies**
   - type inference tools
   - flow analysis tools
   - graph processing tools
   - visualization tools

### Development Tools
1. **Code Quality**
   - Linters
   - Formatters
   - Type checkers
   - Security scanners

2. **Testing Tools**
   - Unit testing
   - Integration testing
   - Performance testing
   - Coverage tools

3. **Documentation Tools**
   - API documentation
   - Architecture docs
   - User guides
   - Examples

## Technical Constraints

### Performance Requirements
1. **Response Time**
   - API endpoints < 100ms
   - Analysis < 1s per file
   - Graph queries < 50ms
   - Cache hits < 10ms

2. **Resource Usage**
   - Memory < 1GB per analysis
   - CPU < 80% utilization
   - Disk < 10GB cache
   - Network < 100MB/s

3. **Scalability**
   - Support 100k+ files
   - Handle multiple languages
   - Process large graphs
   - Concurrent analysis

### Language Support
1. **Python Features**
   - Type hints
   - Decorators
   - Async/await
   - Metaclasses

2. **JavaScript Features**
   - ES6+ syntax
   - Modules
   - Classes
   - Promises

3. **Swift Features**
   - Type system
   - Protocols
   - Extensions
   - Generics

### Analysis Capabilities
1. **Static Analysis**
   - Type inference
   - Control flow
   - Data flow
   - Symbol resolution

2. **Graph Analysis**
   - Node relationships
   - Edge types
   - Path finding
   - Cycle detection

3. **Performance Analysis**
   - Memory usage
   - CPU usage
   - I/O patterns
   - Cache efficiency

## Testing Requirements

### Unit Testing
1. **Parser Tests**
   - Syntax parsing
   - Error handling
   - Edge cases
   - Performance

2. **Analyzer Tests**
   - Symbol extraction
   - Type inference
   - Flow analysis
   - Context tracking

3. **Graph Tests**
   - Node creation
   - Edge creation
   - Relationships
   - Queries

### Integration Testing
1. **Cross-language Tests**
   - Multi-language projects
   - Reference resolution
   - Type compatibility
   - Performance impact

2. **End-to-end Tests**
   - Complete pipeline
   - Large codebases
   - Real scenarios
   - Benchmarks

### Performance Testing
1. **Scalability Tests**
   - Large projects
   - Multiple languages
   - Complex graphs
   - Resource usage

2. **Optimization Tests**
   - Caching
   - Incremental analysis
   - Parallel processing
   - Resource efficiency

## Documentation Requirements

### API Documentation
1. **Endpoints**
   - REST API
   - WebSocket
   - Graph queries
   - Analysis options

2. **Data Models**
   - Request/response
   - Graph structure
   - Analysis results
   - Error types

3. **Usage Examples**
   - Basic usage
   - Advanced features
   - Performance tips
   - Troubleshooting

### Architecture Documentation
1. **Components**
   - Parser layer
   - Analyzer layer
   - Semantic layer
   - Graph layer

2. **Design Patterns**
   - Language support
   - Analysis patterns
   - Testing patterns
   - Error handling

3. **Implementation Guide**
   - Setup guide
   - Development guide
   - Testing guide
   - Deployment guide

### User Documentation
1. **Getting Started**
   - Installation
   - Configuration
   - Basic usage
   - Examples

2. **Advanced Usage**
   - Language support
   - Analysis options
   - Graph queries
   - Performance tuning

3. **Troubleshooting**
   - Common issues
   - Error messages
   - Performance problems
   - Solutions