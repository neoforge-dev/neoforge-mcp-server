# Tech Context

## Stack
- Core: Python 3.11+, FastMCP
- Monitoring: OpenTelemetry, Prometheus
- Security: Process isolation, validation

## Servers
| Server | Tech |
|--------|------|
| Core | FastMCP, Tool registry |
| LLM | TikToken, LLM |
| Neo Dev | venv, pytest |
| Neo Ops | psutil, Docker |
| Neo Local | File ops, uv |
| Neo LLM | LLM models |
| Neo DO | Process control |

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Config
- `.env`: Env vars
- `config/`: Server
- `monitoring/`: Metrics
- `security/`: Policies

## Constraints
- Perf: <100ms resp, <512MB/server
- Scale: Horizontal, stateless
- Security: Sandboxed, validated
- Reliability: Auto-recovery

## Core Deps
```
fastmcp>=1.0.0
opentelemetry-api>=1.0.0
prometheus-client>=0.9.0
psutil>=5.8.0
pytest>=7.0.0
ruff>=0.1.0
```

## Future
1. K8s integration
2. Cloud support
3. More LLMs
4. Enhanced security
5. Advanced monitoring