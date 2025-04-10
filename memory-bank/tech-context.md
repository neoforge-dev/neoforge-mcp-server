# Tech Context

## Core Stack
- **Lang/Framework:** Python 3.11+, FastAPI, Pydantic
- **Testing:** Pytest (+ asyncio, cov, mock)
- **Code Quality:** Ruff, Mypy
- **Config:** PyYAML, python-dotenv
- **Monitoring:** OpenTelemetry SDK, Prometheus client (planned)
- **Logging:** Loguru
- **HTTP:** httpx
- **Key Libs:** psutil, tiktoken, tree-sitter

## Setup
- Activate venv: `source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`

## Config Files
- Secrets: `.env`
- Server Settings: `config/<server_name>.yml`
- API Keys: In `.yml`, managed by `SecurityManager`

## Goals (Summary)
- **Primary:** TDD >90% coverage.
- **Secondary:** Security, Perf (<100ms API), Scalability.