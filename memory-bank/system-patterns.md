# System Patterns

## Architecture
- **Style:** Microservices (FastAPI, HTTP/WS).
- **Principles:** Clean Architecture (SoC, DI), Security-First.
- **`BaseServer`:** Core setup (Config, Loguru, OTel, Middleware, `/health`).

## Core Design Patterns
- **Registry:** Tool/model management.
- **Factory/Strategy:** Dynamic instantiation (e.g., adapters).
- **Adapter:** External library wrapping (e.g., parsers).
- **Decorator:** Cross-cutting concerns (e.g., `@handle_exceptions`).
- **Dependency Injection:** FastAPI (`Depends`) for security/state.

## Monitoring & Logging
- OpenTelemetry (Metrics/Tracing).
- Structured JSON Logging (Loguru).

## Server Implementation Steps
1. Inherit `BaseServer`.
2. Implement `register_routes`.
3. Access managers via `request.state` or `Depends`.

*Note: Server modularity review planned (Phase 2 - see `active-context.md`).*
*Libraries: `tech-context.md`* 