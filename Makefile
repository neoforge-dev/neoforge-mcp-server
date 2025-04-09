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