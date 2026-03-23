.PHONY: help lint format test check clean run install

# Default target
help:
	@echo "Discord Brackets Bot - Development Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  make lint       - Run ruff and pyright type checkers"
	@echo "  make format     - Auto-format code with ruff"
	@echo "  make test       - Run pytest test suite"
	@echo "  make check      - Run all checks (lint + test)"
	@echo "  make install    - Install dependencies with uv sync"
	@echo "  make run        - Run the bot"
	@echo "  make clean      - Remove cache files"
	@echo ""

# Run all linters
lint: install
	uv run ruff check
	uv run pyright . --pythonversion 3.13

# Auto-format code
format: install
	uv run ruff check --fix
	uv run ruff format

# Run tests
test: install
	uv run pytest tests/ -v

# Run all checks
check: lint test
	@echo "✓ All checks passed!"

# Install dependencies from lock file
install:
	uv sync --all-extras

# Run the bot
run: install
	uv run main.py

# Clean cache and generated files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"
