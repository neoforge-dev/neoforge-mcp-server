# System Patterns

## Architecture & BaseServer
- **Style:** Microservices (HTTP/WS) via FastAPI.
- **Principles:** Clean Architecture (SoC, DI), Security-First.
- **`BaseServer`:** Standardizes Config, Logging(Loguru), Monitoring(OTel), Middleware(Error, CORS, Gzip, RateLimit), `/health` route.

## Core Design Patterns
- **Registry:** Tool/model management.
- **Factory/Strategy:** Dynamic adapter/instance creation.
- **Adapter:** Wrap external libs/tools.
- **Decorator:** Cross-cutting concerns (e.g., `@handle_exceptions`).
- **Dependency Injection:** FastAPI (`Depends`) for security, state.

## Monitoring & Logging
- OpenTelemetry (Metrics/Tracing).
- Structured JSON Logging (Loguru).

## Server Implementation Pattern
1. Inherit `BaseServer`.
2. Implement `register_routes` for specific endpoints.
3. Access managers via `request.state` or `Depends`.

*Libraries: `tech-context.md`* 