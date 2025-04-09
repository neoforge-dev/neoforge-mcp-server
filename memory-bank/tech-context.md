# Tech Context

## Core Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Testing:** Pytest (+ asyncio, cov)
- **Lint/Type:** Ruff, Mypy
- **Monitoring:** OpenTelemetry SDK, Prometheus Client
- **Config:** PyYAML, Pydantic, python-dotenv
- **Other Key Libs:** `psutil`, `tiktoken`, `tree-sitter`, `httpx`.
- *See `requirements.txt` for full list/versions.*

## Setup
```bash
# 1. venv
source venv/bin/activate
# 2. Install
pip install -r requirements.txt
# 3. Tree-sitter (If needed)
# python server/code_understanding/build_languages.py
```

## Configuration
- **Secrets:** `.env`
- **Servers:** `config/<server_name>.yml`
- **Policies:** `server/utils/security.py` (code)

## Key Constraints/Goals (Current Focus)
- **Testing:** TDD, >90% coverage.
- **Security:** Input validation, AuthN/Z, secure defaults.
- **Performance:** Goals exist (<100ms API, <512MB RAM), monitor during refactor.
- **Scalability:** Design for horizontal scaling.

## Servers
- See `project-brief.md` for server list and ports.

## Future Considerations
- Kubernetes integration.
- Cloud deployment support.
- Additional LLM integrations.
- Advanced security features (e.g., WAF).
- Enhanced monitoring dashboards/alerts.