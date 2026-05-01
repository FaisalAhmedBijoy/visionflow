.PHONY: help install dev test lint format type-check clean docs

help:
	@echo "VisionFlow Development Commands"
	@echo "================================"
	@echo "make install      - Install package in production mode"
	@echo "make dev          - Install in development mode with all deps"
	@echo "make test         - Run tests with coverage"
	@echo "make lint         - Run linters (flake8)"
	@echo "make format       - Format code (black, isort)"
	@echo "make type-check   - Run type checker (mypy)"
	@echo "make check        - Run all checks (format, lint, type-check, test)"
	@echo "make clean        - Remove build artifacts and caches"
	@echo "make docs         - Build documentation"
	@echo "make cli-test     - Test CLI commands"

install:
	pip install -e .

dev:
	pip install -e ".[dev,yolo,ocr,kafka]"

test:
	pytest tests/ -v --cov=visionflow --cov-report=html --cov-report=term-missing

test-quick:
	pytest tests/ --tb=short

lint:
	flake8 visionflow tests

format:
	black visionflow tests
	isort visionflow tests

type-check:
	mypy visionflow

check: format lint type-check test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type d -name .coverage -exec rm -rf {} +
	rm -rf build dist *.egg-info

docs:
	cd docs && make html

cli-test:
	visionflow version
	visionflow init test_config.yaml
	cat test_config.yaml
	rm test_config.yaml
