.PHONY: test test-cov test-file clean setup run-servers help docker-up docker-down docker-build lint format check-types docker-build-llm docker-run-llm docker-stop-llm test-core test-llm test-neod test-neoo test-neodo test-neolocal test-neollm test-all

# Default target
help:
	@echo "Available commands:"
	@echo "  make setup        - Set up the development environment"
	@echo "  make test         - Run all tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make test-file    - Run a specific test file (e.g., make test-file FILE=tests/test_command_execution.py)"
	@echo "  make run-servers  - Run all servers"
	@echo "  make clean        - Clean up generated files"
	@echo "  make docker-up    - Start Docker services"
	@echo "  make docker-down  - Stop Docker services"
	@echo "  make docker-build - Build Docker services"
	@echo "  make docker-build-llm - Build LLM server Docker image"
	@echo "  make docker-run-llm  - Run LLM server Docker container"
	@echo "  make docker-stop-llm - Stop LLM server Docker container"
	@echo "  make lint         - Run ruff linting on the codebase"
	@echo "  make format       - Format code with ruff"
	@echo "  make check-types  - Run mypy type checking"
	@echo "  make test-core    - Run tests for the Core MCP server"
	@echo "  make test-llm     - Run tests for the LLM MCP server"
	@echo "  make test-neod    - Run tests for the NeoD MCP server"
	@echo "  make test-neoo    - Run tests for the NeoOps MCP server"
	@echo "  make test-neodo   - Run tests for the NeoDO MCP server"
	@echo "  make test-neolocal - Run tests for the NeoLocal MCP server"
	@echo "  make test-neollm  - Run tests for the NeoLLM MCP server"
	@echo "  make test-all     - Run all server tests"
	@echo "  make help         - Show this help message"

# Set up development environment
setup: clean
	CMAKE_ARGS="-DCMAKE_POLICY_VERSION_MINIMUM=3.5" uv sync --all-extras # Include optional dependencies for tests
	# uv pip install "itsdangerous>=2.0" -- Removed workaround
	# uv pip install "slowapi>=0.1.9" -- Removed workaround
	# uv pip install "structlog>=23.2.0" -- Removed workaround

# Run all tests
test: setup
	uv run pytest -v --log-cli-level=DEBUG

# Run tests with coverage
test-cov: setup
	uv run pytest --cov=server --cov-report=html

# Run specific test file
test-file: setup
	uv run pytest -v $(FILE)

# Run all servers
run-servers: setup
	uv run python3 run_servers.py

# Docker commands
docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-build:
	docker-compose build

# --- LLM Server Docker Commands ---
# Define image name and tag
LLM_IMAGE_NAME ?= llm-server
LLM_IMAGE_TAG ?= latest

docker-build-llm:
	@echo "Building LLM server Docker image ($(LLM_IMAGE_NAME):$(LLM_IMAGE_TAG))..."
	docker build -t $(LLM_IMAGE_NAME):$(LLM_IMAGE_TAG) -f llm.Dockerfile .

docker-run-llm: docker-build-llm
	@echo "Running LLM server Docker container ($(LLM_IMAGE_NAME):$(LLM_IMAGE_TAG))..."
	docker run -d --rm -p 7444:7444 \
		--name $(LLM_IMAGE_NAME) $(LLM_IMAGE_NAME):$(LLM_IMAGE_TAG)

docker-stop-llm:
	@echo "Stopping LLM server Docker container ($(LLM_IMAGE_NAME))..."
	docker stop $(LLM_IMAGE_NAME) || true # Ignore error if already stopped

# --- End LLM Server Docker Commands ---

# Code quality commands
lint: setup
	uv run ruff check server tests

format: setup
	uv run ruff format server tests

check-types: setup
	uv run mypy server tests

# Clean up generated files
clean:
	uv clean

# Per-server test targets
test-core:
	uv run pytest -v tests/core --log-cli-level=DEBUG

test-llm:
	uv run pytest -v tests/llm --log-cli-level=DEBUG

test-neod:
	uv run pytest -v tests/neod --log-cli-level=DEBUG

test-neoo:
	uv run pytest -v tests/neoo --log-cli-level=DEBUG

test-neodo:
	uv run pytest -v tests/neodo --log-cli-level=DEBUG

test-neolocal:
	uv run pytest -v tests/neolocal --log-cli-level=DEBUG

test-neollm:
	uv run pytest -v tests/test_neollm.py --log-cli-level=DEBUG

test-all:
	uv run pytest -v tests --log-cli-level=DEBUG

# Default target
.DEFAULT_GOAL := help