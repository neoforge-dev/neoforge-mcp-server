# Product Context: MCP Platform

## Purpose
- AI-enhanced dev/ops platform.
- **Focus:** SoC, scalability, security, monitoring.

## Key Goals (Metrics)
- **Performance:** <100ms response time
- **Reliability:** 99.9% uptime
- **Security:** Zero critical vulnerabilities
- **Quality:** >90% test coverage

## Server Roles (Ports)
- **Core (7443):** Orchestration, Tooling
- **LLM (7444):** Model Mgmt, Generation
- **NeoDev (7445):** Dev Tools
- **NeoOps (7446):** Process Mgmt, Resource Mgmt
- **NeoLocal (7447):** Local Operations
- **NeoLLM (7448):** Local Model Serving
- **NeoDO (7449):** Direct Execution Layer

## Basic Flow
- Request -> Auth -> Process -> Response -> Monitor 