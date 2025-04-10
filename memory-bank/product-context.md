# Product Context

## Purpose & Goals
- **System:** AI-enhanced dev/ops platform.
- **Focus:** SoC, scalability, security, monitoring.
- **Goals:** <100ms resp, 99.9% uptime, no critical vulns, >90% test coverage.

## Server Roles (Ports)
- Core (7443): Coordination, Tool Mgmt
- LLM (7444): Model Ops, Code Gen
- NeoDev (7445): Dev Tools
- NeoOps (7446): Process/Resource
- NeoLocal (7447): Local Ops
- NeoLLM (7448): Local Models
- NeoDO (7449): Direct Exec

## Basic Flow
- Request -> Validate/Auth -> Process -> Response -> Monitor

## Future
- Scaling, Features, Integrations, UX. 