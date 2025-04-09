# Project Brief: MCP Server Architecture

## Core Objective
- Distributed, secure, observable servers using clean architecture and TDD

## Servers & Ports
- Core (7443), LLM (7444), NeoDev (7445), NeoOps (7446), NeoLocal (7447), NeoLLM (7448), NeoDO (7449)

## Key Requirements
- Security: AuthN/Z, Input Validation, Process Isolation
- Monitoring: OpenTelemetry, Prometheus
- Comms: HTTP/WebSocket
- Performance: Async I/O
- Dev: Clean Arch, TDD (>90% coverage)

## Current Phase
- Phase 2: BaseServer migration, Test Coverage >90%
- Next: Phase 3 (Component Development)

*See `tech-context.md` for stack/libs & `system-patterns.md` for architecture details.* 