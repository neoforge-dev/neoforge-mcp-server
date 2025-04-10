.PHONY: test test-cov test-file clean setup run-servers help docker-up docker-down docker-build lint format check-types

# Variables
PYTHON = python3
PIP = pip3
VENV = .venv
PYTEST = pytest
COVERAGE = coverage
DOCKER_COMPOSE = docker-compose
PYLINT = pylint
BLACK = black
MYPY = mypy

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
	@echo "  make lint         - Run pylint on the codebase"
	@echo "  make format       - Format code with black"
	@echo "  make check-types  - Run mypy type checking"
	@echo "  make help         - Show this help message"

# Set up development environment
setup: clean
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && $(PIP) install -r requirements.txt
	. $(VENV)/bin/activate && $(PIP) install -r requirements-dev.txt

# Run all tests
test: setup
	. $(VENV)/bin/activate && $(PYTEST) -v

# Run tests with coverage
test-cov: setup
	. $(VENV)/bin/activate && $(PYTEST) --cov=server --cov-report=html

# Run specific test file
test-file: setup
	. $(VENV)/bin/activate && $(PYTEST) -v $(FILE)

# Run all servers
run-servers: setup
	. $(VENV)/bin/activate && $(PYTHON) run_servers.py

# Docker commands
docker-up:
	$(DOCKER_COMPOSE) up -d

docker-down:
	$(DOCKER_COMPOSE) down

docker-build:
	$(DOCKER_COMPOSE) build

# --- LLM Server Docker Commands ---
# Define image name and tag
LLM_IMAGE_NAME ?= llm-server
LLM_IMAGE_TAG ?= latest

docker-build-llm:
	@echo "Building LLM server Docker image ($(LLM_IMAGE_NAME):$(LLM_IMAGE_TAG))..."
	docker build -t $(LLM_IMAGE_NAME):$(LLM_IMAGE_TAG) -f llm.Dockerfile .

docker-run-llm: docker-build-llm
	@echo "Running LLM server Docker container ($(LLM_IMAGE_NAME):$(LLM_IMAGE_TAG))..."
	# Run in detached mode (-d), remove container on exit (--rm)
	# Map host port 7444 to container port 7444
	# Pass necessary environment variables (e.g., API keys) using -e
	# Mount volumes if needed (e.g., for local models) using -v
	docker run -d --rm -p 7444:7444 \
		# Example: Pass OpenAI API key if needed by the container
		# -e OPENAI_API_KEY=$(OPENAI_API_KEY) \
		# Example: Mount a local models directory if needed
		# -v $(HOME)/.cache/huggingface:/root/.cache/huggingface \
		--name $(LLM_IMAGE_NAME) $(LLM_IMAGE_NAME):$(LLM_IMAGE_TAG)

docker-stop-llm:
	@echo "Stopping LLM server Docker container ($(LLM_IMAGE_NAME))..."
	docker stop $(LLM_IMAGE_NAME) || true # Ignore error if already stopped

# --- End LLM Server Docker Commands ---

# Code quality commands
lint: setup
	. $(VENV)/bin/activate && $(PYLINT) server tests

format: setup
	. $(VENV)/bin/activate && $(BLACK) server tests

check-types: setup
	. $(VENV)/bin/activate && $(MYPY) server tests

# Clean up generated files
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf *.egg-info
	rm -rf build
	rm -rf dist
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +

# Default target
.DEFAULT_GOAL := help 