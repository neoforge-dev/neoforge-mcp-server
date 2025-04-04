# System Patterns

## Architecture
- Microservices: HTTP/WS comms, independent scaling
- Event-Driven: Async messaging, event sourcing
- Clean: Separation of concerns, SOLID
- Security-First: Auth boundaries, validation

## Design Patterns

### Core
- Factory: Tool creation
- Strategy: Tool execution
- Observer: Monitoring
- Command: Operations
- Facade: External API

### Tools
- Registry: Tool management
- Builder: Config
- Chain: Processing
- Decorator: Logging
- Adapter: External tools

### Comms
- Pub/Sub: Events
- Gateway: Inter-server
- Circuit Breaker: Resilience
- Bulkhead: Isolation
- Retry: Reliability

### Resources
- Pool: Connections
- Proxy: Access
- Flyweight: Shared
- Singleton: Global
- Dispose: Cleanup

## Server Components
```python
# Core patterns for each server
class BaseServer:
    def __init__(self):
        self.registry = Registry()    # Tool/model registry
        self.manager = Manager()      # Resource management
        self.monitor = Monitor()      # Metrics/logging
```

## Monitoring
- Metrics: Prometheus/Grafana
- Tracing: OpenTelemetry
- Logging: Structured, correlated
- Alerts: Thresholds 