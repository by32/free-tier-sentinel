# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-cloud free-tier planner project that helps users launch cloud resources within free-tier constraints while avoiding provisioning failures. The project consists of:

- **Constraint Database**: Open-source database of quota and free-tier limits across AWS, GCP, Azure, and OCI
- **Python Planner**: Uses integer linear programming (pulp) to find valid, cost-free deployment plans
- **Live Capacity Detection**: Prevents recommending temporarily unavailable instance shapes
- **Provisioning-Retry Engine**: Repeatedly attempts launch steps until success or timeout

## Architecture Components (Planned)

Based on the project brief, the system will be organized into these main components:

### Core Planner (`planner/`)
- **Cost Calculator**: Tracks usage against free-tier limits
- **Shape Recommender**: Suggests optimal instance configurations
- **Constraint Solver**: Uses integer linear programming for plan optimization
- **Dependencies**: Will use `pulp` for optimization, `boto3`/`google-cloud-sdk`/`azure-sdk` for cloud APIs

### Constraint Database (`constraints/`)
- **Schema**: YAML/JSON files defining free-tier limits per cloud provider
- **Validators**: Ensure constraint data integrity
- **Updaters**: Keep limits current as providers change offerings

### Capacity Detection (`capacity/`)
- **Live Checkers**: Real-time availability verification per region/AZ
- **Cache Layer**: Avoid repeated API calls for capacity checks
- **Fallback Logic**: Handle temporary outages gracefully

### Provisioning Engine (`provisioning/`)
- **Cloud Adapters**: Provider-specific provisioning logic
- **Retry Mechanisms**: Exponential backoff and circuit breakers
- **State Management**: Track deployment progress and rollback capability

## Development Setup

This project uses UV for fast, reliable package management:

```bash
# Install dependencies (creates virtual environment automatically)
uv sync

# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Lint and format code
uv run ruff check src/ tests/
uv run black src/ tests/

# Type checking
uv run mypy src/

# Run the planner
uv run sentinel --config config.yaml

# Add new dependencies
uv add package-name
uv add --dev package-name  # for dev dependencies
```

## Key Design Principles

- **Defensive Security**: This tool helps users stay within legitimate free-tier usage
- **Multi-Cloud**: Abstract cloud provider differences behind common interfaces
- **Resilience**: Handle temporary failures and capacity constraints gracefully
- **Transparency**: Clear reporting of what resources will be created and why