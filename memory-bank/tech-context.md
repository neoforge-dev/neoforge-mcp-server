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

## Future
- K8s Integration
- Cloud Deployment
- More LLM Integrations
- Enhanced Security
- Advanced Monitoring