.PHONY: help install test test-unit test-integration test-cov lint fmt clean

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install package with dev dependencies
	pip install -e ".[dev]"

test:  ## Run all tests
	pytest

test-unit:  ## Run unit tests only (skip integration)
	pytest -m "not integration"

test-integration:  ## Run integration tests only
	pytest -m "integration"

test-cov:  ## Run tests with coverage report
	pytest --cov=crane --cov-report=term-missing

lint:  ## Run linter
	ruff check src/ tests/

fmt:  ## Format code
	ruff format src/ tests/

clean:  ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
