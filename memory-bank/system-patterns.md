# System Patterns

## Architecture
- Microservices (HTTP/WS)
- Clean Architecture (SoC, DI)
- Security-First

## BaseServer Pattern
- Standardizes setup (Config, Log, Monitor)
- Provides: /health, utils, middleware

## Design Patterns
- Registry: Tool/model mgmt
- Factory/Strategy: Tool creation
- Adapter: External tools
- Decorator: Cross-cutting
- Command: Operations

## Monitoring
- OpenTelemetry (Metrics/Tracing)
- JSON Logging

## Server Structure
```python
class SpecificServer(BaseServer):
    def _setup_routes(self):
        pass
```

*See `tech-context.md` for specific libraries.* 