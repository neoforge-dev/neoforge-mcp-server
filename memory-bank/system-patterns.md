# System Patterns

## Core Architecture
- **Style:** Microservices (HTTP/WS).
- **Principles:** Clean Architecture (Separation of Concerns, DI), Security-First.

## Base Server Pattern (`server.utils.base_server.BaseServer`)
- **Purpose:** Standardize setup (Config, Log, Monitor, Security) & common middleware across servers.
- **Key Features:** Manages shared utils, adds standard middleware (CORS, Logging, ErrorHandling, Security, Monitoring), `/health` endpoint.

## Key Design Patterns (Selected)
- **Registry:** Tool/model mgmt (`server.core`, `server.llm`).
- **Factory/Strategy:** Tool creation/execution (`server.core`).
- **Adapter:** External tool integration (`server.code_understanding`).
- **Decorator:** Used for cross-cutting concerns (e.g., error handling via `@handle_exceptions`).
- **Command:** Encapsulating operations (e.g., `CommandExecutor`).

## Monitoring Approach (via `BaseServer` & Utils)
- **Metrics:** Prometheus (via OpenTelemetry SDK).
- **Tracing:** OpenTelemetry SDK (OTLP Exporter).
- **Logging:** Structured JSON (correlated via trace IDs where possible).

## Server Component Structure (Conceptual)
```python
# BaseServer manages shared components
class SpecificServer(BaseServer):
    def _setup_routes(self):
        # Add server-specific routes here
        pass
    # Other server-specific logic
```

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