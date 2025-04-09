# Product Context

## Purpose
- Distributed system for AI-enhanced dev/ops tasks.

## Problems Solved (Arch)
- Improves: Separation of concerns, scalability, maintainability, security, monitoring.

## Key Success Metrics (Goals)
- **Performance:** <100ms response, 99.9% uptime, <1% errors.
- **Security:** No critical vulns, full input validation.
- **Dev:** >90% test coverage, clean code standards.

## Servers (Function & Port)
- **Core (7443):** Tool mgmt, coordination
- **LLM (7444):** Model ops, code gen
- **NeoDev (7445):** Dev tools, workspaces
- **NeoOps (7446):** Process/resource monitoring
- **NeoLocal (7447):** Local system ops
- **NeoLLM (7448):** Local model ops
- **NeoDO (7449):** Direct execution
*(`project-brief.md` is primary port reference)*

## Basic Request Flow
1. Receive Request
2. Validate + AuthN/Z
3. Process Logic
4. Send Response
5. Log/Monitor

## Future Considerations
- Scaling (Load Balancing)
- Feature Expansion (Tools, Security)
- Integrations (LLMs, Services)
- UX Improvements 