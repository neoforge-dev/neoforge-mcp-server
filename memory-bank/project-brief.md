# Project Brief: MCP Server Architecture

## Core Objective
- Build distributed, secure, observable MCP servers.
- Use clean architecture & TDD.

## Servers & Ports
- Core(7443), LLM(7444), NeoDev(7445), NeoOps(7446), NeoLocal(7447), NeoLLM(7448), NeoDO(7449)

## Key Requirements
- Security: AuthN/Z, Input Validation, Isolation
- Monitoring: OTel, Prometheus (planned)
- Comms: HTTP/WebSocket
- Performance: Async I/O
- Dev Standards: Clean Arch, TDD (>90% coverage)

## Current Focus
- See `active-context.md`.

*Tech stack: `tech-context.md` | Architecture: `system-patterns.md`* 