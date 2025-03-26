# Active Development Context

## Current Focus
- Implementing advanced MCP tools for development workflow optimization
- Enhancing code analysis and performance monitoring capabilities
- Improving LLM context management and testing infrastructure
- Implementing metrics collection system
- Adding profiling tools
- Enhancing error tracking and reporting
- Implementing monitoring dashboards
- Implementing comprehensive profiling capabilities
- Adding profiling tools for performance analysis
- Integrating profiling with existing MCP tools

## Recent Changes
1. Added new MCP tools:
   - `analyze_codebase`: Advanced static analysis
   - `monitor_performance`: System metrics tracking
   - `manage_llm_context`: LLM context optimization
   - `enhanced_testing`: Improved test execution

2. Enhanced existing tools:
   - Improved dependency management with `uv`
   - Added code quality checks with `ruff`
   - Implemented smart output filtering
   - Added performance monitoring

3. Updated documentation:
   - Enhanced tech-context.md with new tools
   - Updated .neorules with new patterns
   - Added comprehensive testing guidelines

4. Added OpenTelemetry integration for distributed tracing
   - Automatic tracing for all MCP tools
   - Configurable trace collection endpoint
   - Service name and version tracking
   - Error and exception tracking in spans

5. Added OpenTelemetry metrics integration
   - Tool execution metrics (duration, calls, errors)
   - System resource monitoring (memory usage)
   - Configurable metrics collection endpoint
   - Automatic metrics for all tools

6. Added cProfile integration for Python profiling
- Implemented custom MCP profiler
- Created profiling tools (start_profiling, stop_profiling, get_profiling_stats, profile_code)
- Added automatic profiling to all MCP tools
- Updated documentation with profiling architecture

## Active Decisions
1. Code Analysis:
   - Using static analysis for security and complexity
   - Implementing cyclomatic complexity tracking
   - Monitoring performance metrics

2. Testing Strategy:
   - Parallel test execution with pytest-xdist
   - Coverage tracking with pytest-cov
   - Test categorization (unit/integration)

3. LLM Integration:
   - Smart context management
   - Token usage optimization
   - Priority-based content filtering

4. Using OpenTelemetry as the primary observability framework
5. OTLP protocol for trace and metrics export
6. Automatic tool wrapping for consistent tracing and metrics
7. System resource monitoring with psutil

8. Using cProfile for core profiling functionality
9. Maintaining temporary files for stats persistence
10. Automatic profiling integration via decorators
11. Structured profiling results format

## Next Steps
1. Infrastructure Enhancement:
   - Add distributed tracing support
   - Implement metrics collection pipeline
   - Add profiling tools
   - Set up monitoring dashboards
   - Configure alerting system
   - Enhance error tracking

2. Developer Experience:
   - Create CLI interface for MCP tools
   - Add interactive debugging features
   - Implement workspace management

3. Testing Infrastructure:
   - Add load testing capabilities
   - Implement mutation testing
   - Add property-based testing

4. Test profiling tools with various scenarios
5. Add profiling data visualization
6. Consider adding memory profiling
7. Implement profiling data export formats

## Known Issues
1. Performance:
   - Need to optimize large file operations
   - Improve concurrent process handling
   - Enhance memory management for large outputs

2. Testing:
   - Need more comprehensive integration tests
   - Coverage gaps in edge cases
   - Test isolation improvements needed

3. Documentation:
   - Need API examples for new tools
   - Missing performance benchmarks
   - Need more detailed setup guides

4. Need to implement metrics collection
5. Profiling tools not yet integrated
6. Error tracking needs enhancement
7. Need monitoring dashboards
8. Need alerting system 