# Pokemon TCG Pocket RL Engine

A research-grade reinforcement learning engine that learns to play Pokémon TCG Pocket like a chess engine.

## Architecture

This project implements a complete RL pipeline for Pokemon TCG Pocket:

- **Card DB** (`src/card_db/`) - Immutable card data structures and parsing
- **Rules Engine** (`src/rules/`) - Deterministic game simulator (~100ns/step target)  
- **Environment** (`src/env/`) - Gym-compatible wrapper with action masks
- **Networks** (`src/net/`) - PyTorch policy-value networks
- **Training** (`src/train/`) - Lightning loops distributed via Ray
- **Serving** (`src/serve/`) - FastAPI inference service with ONNX

## Quick Start

```bash
# Install dependencies
make install-dev

# Run tests
make test

# Format code
make format

# Run all checks
make prepush
```

## Development

This project follows strict code quality standards:

- **Python 3.11** with mandatory type hints
- **Line length 100** with Black + Ruff formatting
- **≥90% test coverage** especially for rules engine
- **Performance target**: ≤150μs per game step

See the Makefile for all available development commands.

## Project Status

🚧 **Week 1**: Setting up card database and core data structures 