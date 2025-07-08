.PHONY: help install install-dev format lint test bench clean prepush
.DEFAULT_GOAL := help

# Colors for terminal output
BLUE := \033[36m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Pokemon TCG Pocket RL Development Commands$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(RESET) %s\n", $$1, $$2}'

install: ## Install project dependencies
	python3 -m pip install -e .

install-dev: ## Install development dependencies
	python3 -m pip install -e ".[dev]"
	pre-commit install

format: ## Format code with black and ruff
	black src/ tests/
	ruff check src/ tests/ --fix

lint: ## Run linting checks
	ruff check src/ tests/
	black src/ tests/ --check
	mypy src/
	pyright src/

test: ## Run tests with coverage
	pytest -v --cov=src --cov-report=term-missing

test-fast: ## Run tests without coverage (faster)
	pytest -v -x

bench: ## Run performance benchmarks
	python -m src.rules.bench

clean: ## Clean up build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

prepush: format lint test ## Run all checks before pushing (mirrors CI)
	@echo "$(BLUE)✅ All checks passed! Ready to push.$(RESET)"

# Development server targets
serve-api: ## Start the FastAPI inference server
	uvicorn src.serve.api:app --reload --host 0.0.0.0 --port 8000

# Training targets  
train-ppo: ## Start PPO training
	python -m src.train.ppo_loop

train-az: ## Start AlphaZero-style training
	python -m src.train.alphazero_loop

# Data targets
scrape-cards: ## Scrape latest card database
	python -m src.card_db.scraper

# Docker targets
docker-build: ## Build Docker image
	docker build -t pokemon-rl:latest .

docker-run: ## Run Docker container
	docker run -it --rm -p 8000:8000 pokemon-rl:latest 