# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multi-cloud free-tier planner project that helps users launch cloud resources within free-tier constraints while avoiding provisioning failures. The project consists of:

- **Constraint Database**: Open-source database of quota and free-tier limits across AWS, GCP, Azure, and OCI
- **Python Planner**: Uses integer linear programming (pulp) to find valid, cost-free deployment plans
- **Live Capacity Detection**: Prevents recommending temporarily unavailable instance shapes
- **Provisioning-Retry Engine**: Repeatedly attempts launch steps until success or timeout
- **Real-time Monitoring**: Cost tracking, health monitoring, and usage analytics
- **Advanced Optimization**: AI-powered algorithms including genetic algorithms and simulated annealing
- **Enterprise Integrations**: CI/CD pipelines, Infrastructure as Code export, and API server

## Architecture Components

The system is organized into these main components:

### ✅ Core Planner (`planner/`)
- **Cost Calculator**: ✅ Tracks usage against free-tier limits with overage pricing
- **Resource Recommender**: ✅ Suggests optimal resource configurations with confidence scoring
- **Plan Optimizer**: ✅ Uses cost optimization for deployment plans across multiple providers
- **Capacity-Aware Extensions**: ✅ Enhanced components that consider live capacity data
- **Dependencies**: Uses `pulp` for optimization, cloud SDKs for API integration

### ✅ Constraint Database (`constraints/`)
- **Schema**: ✅ YAML files defining free-tier limits per cloud provider with validation
- **Validators**: ✅ Ensure constraint data integrity with Pydantic v2
- **Query System**: ✅ Fluent interface for constraint filtering with method chaining
- **Real Data**: ✅ 27+ documented constraints across AWS, GCP, and Azure with actual limits

### ✅ Capacity Detection (`capacity/`)
- **Live Checkers**: ✅ Real-time availability verification per region/AZ (AWS, GCP, Azure)
- **Cache Layer**: ✅ TTL-based caching system to minimize API calls and improve performance
- **Aggregation**: ✅ Concurrent capacity checks across multiple providers using ThreadPoolExecutor
- **Integration**: ✅ Seamlessly integrated with all planning components for capacity awareness

### ✅ Provisioning Engine (`provisioning/`)
- **Cloud Adapters**: ✅ Provider-specific provisioning logic with standardized interfaces
- **Retry Mechanisms**: ✅ Exponential backoff and circuit breakers for resilient deployments
- **State Management**: ✅ Track deployment progress and rollback capability with persistent state

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

### ✅ User Interface & CLI (`cli/`)
- **Interactive Wizard**: ✅ Step-by-step plan creation with rich formatting and validation
- **Configuration Support**: ✅ YAML and JSON configuration file loading with comprehensive validation
- **Plan Management**: ✅ Save, load, and validate deployment plans with dry-run capabilities
- **Rich Output**: ✅ Colored terminal output using Rich library for enhanced user experience

### ✅ Monitoring & Analytics (`monitoring/`)
- **Cost Tracking**: ✅ Real-time cost monitoring with configurable alerts and thresholds
- **Health Monitoring**: ✅ Resource health checks with status tracking and alerting
- **Usage Analytics**: ✅ Comprehensive usage reporting with trend analysis and future predictions
- **Dependency Management**: ✅ Resource dependency tracking with deployment order optimization

### ✅ Advanced Features (`monitoring/optimization/`)
- **Genetic Algorithms**: ✅ AI-powered plan optimization using evolutionary algorithms
- **Simulated Annealing**: ✅ Advanced optimization for complex deployment scenarios
- **Multi-objective Optimization**: ✅ Balance cost, performance, and availability constraints

### ✅ Enterprise Integrations (`integration/`)
- **CI/CD Pipelines**: ✅ GitHub Actions workflow generation with automated deployments
- **Infrastructure as Code**: ✅ Export to Terraform, CloudFormation, Pulumi, and Ansible
- **REST API**: ✅ FastAPI-based API server with comprehensive endpoints for all functionality
- **Webhook Notifications**: ✅ Event-driven notifications with HMAC signature verification

## Project Status & Roadmap

### ✅ ALL PHASES COMPLETED (82% Test Coverage)

**Phase 1: Core Data Models** ✅ (15 tests)
- Pydantic v2 data models with field validation and __hash__ methods
- Complete test coverage for all data model edge cases

**Phase 2: Constraint Database System** ✅ (34 tests)
- YAML constraint loading with comprehensive validation
- Fluent query interface with advanced filtering capabilities
- Real constraint files with 27+ documented free-tier limits

**Phase 3: Planning Engine** ✅ (52 tests)
- Cost calculator with overage pricing for free-tier resources
- Resource recommender with confidence scoring and capacity awareness
- Plan optimizer using integer linear programming (PuLP)

**Phase 4: Live Capacity Detection** ✅ (84 tests)
- Multi-provider capacity checkers with concurrent execution
- TTL-based caching system for performance optimization
- Complete integration with all planning components

**Phase 5: Provisioning Engine** ✅ (104 tests)
- Cloud-specific adapters with standardized interfaces
- Retry mechanisms using exponential backoff and circuit breakers
- State management with rollback capabilities and error handling

**Phase 6: User Interface & CLI** ✅ (125 tests)
- Interactive planning wizard with rich terminal output
- Configuration file support (YAML/JSON) with validation
- Comprehensive CLI with all major functionality

**Phase 7: Advanced Features** ✅ (152 tests)
- Real-time monitoring (cost tracking, health monitoring, analytics)
- AI-powered optimization (genetic algorithms, simulated annealing)
- Enterprise integrations (CI/CD, IaC export, API server, webhooks)

### 🎉 Project Status: PRODUCTION READY

### 📊 Final Test Coverage: 82% (152 tests passing)

## Files Structure & Documentation

### Key Implementation Files
- `src/sentinel/models/core.py` - Core Pydantic v2 data models with validation
- `src/sentinel/constraints/` - YAML constraint database with fluent query interface
- `src/sentinel/planner/` - Cost calculation, resource recommendation, and optimization
- `src/sentinel/capacity/` - Live capacity detection with concurrent API calls
- `src/sentinel/provisioning/` - Cloud provisioning adapters with retry logic
- `src/sentinel/cli/` - Interactive CLI with rich formatting and configuration support
- `src/sentinel/monitoring/` - Real-time cost tracking, health monitoring, analytics
- `src/sentinel/integration/` - CI/CD, IaC export, API server, webhook notifications

### Documentation Files
- `README.md` - Comprehensive usage guide with installation and examples
- `QUICK_START.md` - 5-minute setup guide for immediate hands-on experience
- `ROADMAP.md` - Complete feature roadmap with implementation status
- `examples/` - Working code examples and sample configuration files

### Sample Plans & Examples
- `examples/sample_plans/basic-aws.yaml` - Simple AWS free-tier deployment
- `examples/sample_plans/multi-cloud.yaml` - Multi-cloud free-tier resources
- `examples/basic_usage.py` - Basic API usage examples with CLI integration
- `examples/advanced_features.py` - Advanced features demo with all monitoring capabilities

## Development Commands

### Essential Commands for Claude Code
```bash
# Test everything
uv run pytest                     # Run all 152 tests

# Lint and type check
uv run ruff check src/ tests/     # Code linting
uv run mypy src/                  # Type checking

# CLI usage
uv run sentinel --help           # Main help
uv run sentinel plan --interactive # Interactive wizard
uv run sentinel plan --config examples/sample_plans/basic-aws.yaml --dry-run

# Install dependencies
uv sync                          # Install all dependencies
uv add package-name              # Add new dependency
```

## Key Design Principles

- **Defensive Security**: This tool helps users stay within legitimate free-tier usage
- **Multi-Cloud**: Abstract cloud provider differences behind common interfaces
- **Resilience**: Handle temporary failures and capacity constraints gracefully
- **Transparency**: Clear reporting of what resources will be created and why
- **Test-Driven Development**: All features built using TDD methodology (Red-Green-Refactor)
- **Production Ready**: Comprehensive error handling, monitoring, and enterprise integrations