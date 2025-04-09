# System Patterns

## Architecture
- Microservices (HTTP/WS)
- Clean Architecture (SoC, DI)
- Security-First

## BaseServer Pattern
- Standardizes setup (Config, Log, Monitor, Security)
- Provides: /health, utils, middleware (CORS, Logging, Errors, Security, Monitor)

## Design Patterns
- Registry: Tool/model mgmt
- Factory/Strategy: Tool creation/execution
- Adapter: External tool integration
- Decorator: Cross-cutting concerns
- Command: Operation encapsulation

## Monitoring
- OpenTelemetry SDK (Metrics/Prometheus, Tracing/OTLP)
- Structured JSON Logging

## Server Structure
```python
class SpecificServer(BaseServer):
    def _setup_routes(self):
        # Server-specific routes
        pass
```

*See `tech-context.md` for specific libraries.* 