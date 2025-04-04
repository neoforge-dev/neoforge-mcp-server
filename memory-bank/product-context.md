# Product Context

## Purpose
Distributed system for dev/ops tasks with AI integration

## Problems Solved
- Poor separation of concerns
- Limited scalability/maintenance
- Inefficient resources
- Security gaps
- Limited monitoring

## User Goals
- Devs: Quick tools, code gen, clear feedback
- Ops: Monitoring, maintenance, resource mgmt
- Security: Controls, audits, policies
- Users: Fast service, clear errors

## Core Features
- Security: Auth, validation, isolation
- Monitoring: OpenTelemetry, Prometheus
- Comms: HTTP/WS, events
- Performance: Async, caching, scaling

## Success Metrics
- Perf: <100ms resp, 99.9% uptime, <1% errors
- Security: No critical vulns, full validation
- Dev: 90% coverage, clean code
- Users: Quick response, clear errors

## Servers
1. Core (7443): Tool mgmt, coordination
2. LLM (7444): Model ops, code gen
3. Neo Dev (7445): Dev tools, workspaces
4. Neo Ops (7446): Process/resource monitoring
5. Neo Local (7447): Local system ops
6. Neo LLM (7448): Local model ops
7. Neo DO (7449): Direct execution

## Flow
1. Request → Server
2. Validate + Auth
3. Process
4. Return
5. Log/Monitor

## Future
- Scale: Horizontal, load balance
- Features: New tools, security
- Integrate: More LLMs, services
- UX: Better feedback, docs 