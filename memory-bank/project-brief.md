# MCP Server Architecture

## Core Objectives
- Distributed architecture, clear separation
- Secure comms, monitoring, error handling
- High performance, scalability, extensibility

## Servers
| Server | Port | Purpose |
|--------|------|---------|
| Core | 7443 | Base functionality |
| LLM | 7444 | LLM integration |
| Neo Dev | 7445 | Dev tools |
| Neo Ops | 7446 | Resource mgmt |
| Neo Local | 7447 | Local ops |
| Neo LLM | 7448 | Local LLM |
| Neo DO | 7449 | Direct ops |

## Requirements
- Security: Auth, validation, isolation
- Monitoring: OpenTelemetry, Prometheus
- Comms: HTTP/WS, events
- Performance: Async, caching
- Dev: Clean arch, testing

## Phase
1. Core ✅
2. Enhanced (Current)
3. Components (Next)
4. Optimize (Future)

## Core Deps
FastMCP, OpenTelemetry, Tree-sitter, TikToken 