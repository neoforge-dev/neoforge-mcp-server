# Project Brief: MCP Server Architecture

## Core Objectives
- Build distributed, secure, observable, resilient, performant, scalable, extensible servers.
- Enforce clear separation of concerns.

## Servers & Ports (Primary Reference)
- **Core:** 7443
- **LLM:** 7444
- **NeoDev:** 7445
- **NeoOps:** 7446
- **NeoLocal:** 7447
- **NeoLLM:** 7448
- **NeoDO:** 7449

## Key Requirements
- **Security:** AuthN/Z, input validation, process isolation.
- **Monitoring:** OpenTelemetry (Metrics/Tracing), Prometheus.
- **Comms:** HTTP/WebSocket, Events (TBD).
- **Performance:** Async I/O, caching (TBD).
- **Dev:** Clean arch, TDD (>90% coverage), `BaseServer` migration.

## Current Phase (Q2 2024)
- **Phase 2:** Refactor all servers to use `BaseServer`, Increase Test Coverage.
- **Next:** Phase 3 (Component Development).

## Core External Dependencies
- FastMCP, OpenTelemetry, Tree-sitter, TikToken.
- *See `tech-context.md` & `requirements.txt` for details.* 