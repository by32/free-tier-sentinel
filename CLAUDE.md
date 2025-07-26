# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-cloud free-tier planner project that helps users launch cloud resources within free-tier constraints while avoiding provisioning failures. The project consists of:

- **Constraint Database**: Open-source database of quota and free-tier limits across AWS, GCP, Azure, and OCI
- **Python Planner**: Uses integer linear programming (pulp) to find valid, cost-free deployment plans
- **Live Capacity Detection**: Prevents recommending temporarily unavailable instance shapes
- **Provisioning-Retry Engine**: Repeatedly attempts launch steps until success or timeout

## Architecture Components

The system is organized into these main components:

### ✅ Core Planner (`planner/`)
- **Cost Calculator**: ✅ Tracks usage against free-tier limits
- **Resource Recommender**: ✅ Suggests optimal resource configurations
- **Plan Optimizer**: ✅ Uses cost optimization for deployment plans
- **Capacity-Aware Extensions**: ✅ Enhanced components that consider live capacity
- **Dependencies**: Uses `pulp` (ready), `boto3`/`google-cloud-sdk`/`azure-sdk` for cloud APIs

### ✅ Constraint Database (`constraints/`)
- **Schema**: ✅ YAML files defining free-tier limits per cloud provider
- **Validators**: ✅ Ensure constraint data integrity with Pydantic
- **Query System**: ✅ Fluent interface for constraint filtering
- **Real Data**: ✅ 27+ documented constraints across AWS, GCP, and Azure

### ✅ Capacity Detection (`capacity/`)
- **Live Checkers**: ✅ Real-time availability verification per region/AZ (AWS, GCP, Azure)
- **Cache Layer**: ✅ TTL-based caching to avoid repeated API calls
- **Aggregation**: ✅ Concurrent capacity checks across multiple providers
- **Integration**: ✅ Seamlessly integrated with planning components

### 🚧 Provisioning Engine (`provisioning/`) - NEXT PHASE
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

## Project Status & Roadmap

### ✅ Completed Phases (95% Test Coverage)

**Phase 1: Core Data Models** ✅
- Pydantic v2 data models for constraints, resources, plans, and usage
- 15 passing tests with full validation

**Phase 2: Constraint Database System** ✅  
- YAML constraint loading and validation
- Fluent query interface with method chaining
- Real constraint files for AWS, GCP, Azure (27+ documented limits)
- 34 passing tests with integration scenarios

**Phase 3: Planning Engine** ✅
- Cost calculator with free-tier constraint checking
- Resource recommender with confidence scoring  
- Plan optimizer for multi-provider optimization
- 52 passing tests including complex cost calculations

**Phase 4: Live Capacity Detection** ✅
- Multi-provider capacity checkers (AWS, GCP, Azure)
- TTL-based caching system to avoid API rate limits
- Concurrent capacity aggregation with ThreadPoolExecutor
- Integration with planning components (capacity-aware cost calculator, recommender, optimizer)
- 84 passing tests with 87% overall coverage

### 🚧 Next Phase (Ready for Implementation)

**Phase 5: Provisioning Engine**
- Cloud-specific provisioning adapters
- Retry mechanisms with exponential backoff
- State management and rollback capabilities
- Integration with capacity-aware planning

### 🎯 Future Enhancements
- Web UI for interactive planning
- CLI tool for automated deployments  
- Real-time cost tracking and alerts
- Advanced optimization algorithms
- Additional cloud provider support (OCI, DigitalOcean)

### 📊 Current Test Coverage: 87% (84 tests passing)

## Key Design Principles

- **Defensive Security**: This tool helps users stay within legitimate free-tier usage
- **Multi-Cloud**: Abstract cloud provider differences behind common interfaces
- **Resilience**: Handle temporary failures and capacity constraints gracefully
- **Transparency**: Clear reporting of what resources will be created and why
- **Test-Driven Development**: All features built using TDD methodology