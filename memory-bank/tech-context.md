# Tech Context

## Stack
- Python 3.11+, FastAPI
- Pytest (+ asyncio, cov)
- Ruff, Mypy
- OpenTelemetry, Prometheus
- PyYAML, Pydantic, python-dotenv
- Key Libs: psutil, tiktoken, tree-sitter, httpx

## Setup
```bash
source venv/bin/activate
pip install -r requirements.txt
```

## Config
- Secrets: .env
- Servers: config/<server_name>.yml
- Security: server/utils/security.py

## Goals
- TDD >90% coverage
- Security (Val, AuthN/Z)
- Perf (<100ms API, <512MB RAM)
- Scalability design

## Current Technical Goals
- TDD >90% coverage.
- Security (Val, AuthN/Z).
- Perf (<100ms API, <512MB RAM goal).
- Scalability design.
*See `project-brief.md` & `product-context.md` for more details.*

## Future Considerations
- K8s Integration
- Cloud Deployment
- More LLM Integrations
- Advanced Security (e.g., WAF)
- Enhanced Monitoring (Dashboards/Alerts)