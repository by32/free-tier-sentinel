# 🛡️ Free-Tier Sentinel

**Multi-cloud free-tier planner with live capacity detection and provisioning**

[![Tests](https://img.shields.io/badge/tests-152%20passing-brightgreen)](https://github.com/by32/free-tier-sentinel)
[![Coverage](https://img.shields.io/badge/coverage-82%25-green)](https://github.com/by32/free-tier-sentinel)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)

Free-Tier Sentinel helps you maximize cloud free-tier benefits across AWS, GCP, and Azure by intelligently planning resource deployments, monitoring real-time capacity, and preventing costly overages.

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** ([Download Python](https://python.org/downloads/))
- **uv** package manager ([Install uv](https://docs.astral.sh/uv/getting-started/installation/))
- **Git** ([Install Git](https://git-scm.com/downloads))

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/by32/free-tier-sentinel.git
cd free-tier-sentinel

# Install dependencies with uv
uv sync

# Verify installation
uv run pytest --version
```

### 2. Run Tests (Recommended First Step)

```bash
# Run the full test suite to verify everything works
uv run pytest

# Expected output: 152 tests passing with 82% coverage
# ✅ This confirms your environment is set up correctly
```

### 3. Try the CLI

```bash
# Check CLI is working
uv run sentinel --help

# Try dry-run planning (no cloud credentials needed)
uv run sentinel plan --provider aws --region us-east-1 --resource ec2:t2.micro:1 --dry-run
```

**Expected Output:**
```
ℹ️  Dry-run mode: Plan validation results
✅ Plan validation successful
ℹ️  Total resources: 1
ℹ️  Estimated cost: $1.1600
ℹ️  No resources will be provisioned in dry-run mode
```

## 📋 Step-by-Step Usage Guide

### Method 1: Interactive Planning (Easiest)

```bash
# Launch interactive wizard
uv run sentinel plan --interactive

# Follow the prompts:
# 1. Choose provider (aws/gcp/azure)
# 2. Select region
# 3. Configure resources
# 4. Name your plan
# 5. Confirm
```

### Method 2: Configuration Files

1. **Create a plan configuration file:**

```yaml
# my-plan.yaml
plan:
  name: "my-free-tier-deployment"
  description: "Multi-cloud free-tier resources"

resources:
  - provider: aws
    service: ec2
    resource_type: t2.micro
    region: us-east-1
    quantity: 1
    estimated_monthly_usage: 100
    
  - provider: aws
    service: s3
    resource_type: standard_storage
    region: us-east-1
    quantity: 1
    estimated_monthly_usage: 5
    
  - provider: gcp
    service: compute
    resource_type: e2-micro
    region: us-central1
    quantity: 1
    estimated_monthly_usage: 100
```

2. **Validate and create the plan:**

```bash
# Validate plan (dry-run)
uv run sentinel plan --config my-plan.yaml --dry-run

# Create and save plan
uv run sentinel plan --config my-plan.yaml --output my-deployment.json
```

### Method 3: Command Line Arguments

```bash
# Single resource
uv run sentinel plan \
  --provider aws \
  --region us-east-1 \
  --resource ec2:t2.micro:1 \
  --resource s3:standard_storage:1 \
  --dry-run

# Save to file
uv run sentinel plan \
  --provider gcp \
  --region us-central1 \
  --resource compute:e2-micro:1 \
  --output gcp-plan.json
```

## 🎯 Advanced Features Demo

### 1. Cost Tracking and Monitoring

```python
# examples/cost_tracking_demo.py
import uv.run('python -c "
from sentinel.monitoring.cost_tracker import LiveCostTracker, CostAlert
from sentinel.models.core import Resource
from decimal import Decimal
from datetime import datetime, UTC

# Create cost tracker
tracker = LiveCostTracker()

# Create a resource
resource = Resource(
    provider='aws',
    service='ec2', 
    resource_type='t2.micro',
    region='us-east-1',
    quantity=1,
    estimated_monthly_usage=100
)

# Track costs over time
tracker.track_resource_cost(resource, Decimal('0.0116'), datetime.now(UTC))

# Set up cost alert
alert = CostAlert(
    threshold=Decimal('5.00'),
    period='daily',
    notification_method='email',
    recipients=['admin@example.com']
)
tracker.set_cost_alert(alert)

# Check current costs
costs = tracker.get_current_costs()
print(f'Tracking {len(costs)} resources')
print(f'Current cost: ${costs[0].accumulated_cost}')
"')
```

### 2. Advanced Optimization

```python
# examples/optimization_demo.py
import uv.run('python -c "
from sentinel.monitoring.optimization import GeneticAlgorithmOptimizer
from sentinel.models.core import Resource, Plan

# Create suboptimal plan
resource = Resource(
    provider='aws',
    service='ec2',
    resource_type='t3.large',  # Oversized for free tier
    region='us-east-1',
    quantity=3,
    estimated_monthly_usage=100
)

original_plan = Plan(
    name='suboptimal-plan',
    description='Plan that needs optimization',
    resources=[resource]
)

# Optimize with genetic algorithm
optimizer = GeneticAlgorithmOptimizer(population_size=20, generations=50)
optimized_plan = optimizer.optimize_plan(original_plan)

print(f'Original: {original_plan.resources[0].resource_type} x{original_plan.resources[0].quantity}')
print(f'Optimized: {optimized_plan.resources[0].resource_type} x{optimized_plan.resources[0].quantity}')
"')
```

### 3. Infrastructure as Code Export

```bash
# Export to Terraform
uv run python -c "
from sentinel.integration.iac import IaCExporter, IaCFormat
from sentinel.models.core import Resource, Plan

exporter = IaCExporter()
resource = Resource(provider='aws', service='ec2', resource_type='t2.micro', region='us-east-1', quantity=1, estimated_monthly_usage=100)
plan = Plan(name='terraform-export', description='Export to Terraform', resources=[resource])

terraform_code = exporter.export(plan, IaCFormat.TERRAFORM)
print(terraform_code)
" > my-infrastructure.tf

# Export to CloudFormation
uv run python -c "
from sentinel.integration.iac import IaCExporter, IaCFormat
from sentinel.models.core import Resource, Plan

exporter = IaCExporter()
resource = Resource(provider='aws', service='ec2', resource_type='t2.micro', region='us-east-1', quantity=1, estimated_monthly_usage=100)
plan = Plan(name='cf-export', description='Export to CloudFormation', resources=[resource])

cf_template = exporter.export(plan, IaCFormat.CLOUDFORMATION)
print(cf_template)
" > my-infrastructure.yaml
```

### 4. REST API Server

```bash
# Start the API server
uv run python -c "
from sentinel.integration.api import SentinelAPI
import uvicorn

api = SentinelAPI()
uvicorn.run(api.app, host='0.0.0.0', port=8000)
" &

# Test API endpoints
curl http://localhost:8000/health
curl -X POST http://localhost:8000/plans \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "api-test-plan",
    "description": "Plan created via API",
    "resources": [
      {
        "provider": "aws",
        "service": "ec2", 
        "resource_type": "t2.micro",
        "region": "us-east-1",
        "quantity": 1,
        "estimated_monthly_usage": 100
      }
    ]
  }'
```

## 🧪 Development and Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/test_cli.py -v          # CLI tests
uv run pytest tests/test_monitoring.py -v  # Advanced features tests
uv run pytest tests/test_capacity.py -v    # Capacity detection tests

# Run with coverage
uv run pytest --cov=src --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Development Setup

```bash
# Install development dependencies
uv sync --dev

# Run linting and formatting
uv run ruff check src tests
uv run black src tests

# Run type checking
uv run mypy src
```

## 🔧 Configuration

### Environment Variables

```bash
# Optional: Set cloud provider credentials for real provisioning
export AWS_ACCESS_KEY_ID="your-aws-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/gcp-service-account.json"
export AZURE_CLIENT_ID="your-azure-client-id"
export AZURE_CLIENT_SECRET="your-azure-secret"
export AZURE_TENANT_ID="your-azure-tenant"
```

### Configuration Files

Create `~/.sentinel/config.yaml` for default settings:

```yaml
default_provider: aws
default_region: us-east-1
cost_alerts:
  enabled: true
  daily_threshold: 5.00
  email: your-email@example.com
monitoring:
  health_check_interval: 300  # 5 minutes
  cost_tracking: true
```

## 📖 Key Features

### ✅ Completed Features

- **🎯 Smart Planning**: AI-powered resource optimization for free-tier limits
- **📊 Live Monitoring**: Real-time cost tracking and resource health monitoring
- **🔄 Capacity Detection**: Check availability across AWS, GCP, Azure before deployment
- **⚡ Auto-Provisioning**: Deploy resources with retry logic and state management
- **🎨 Rich CLI**: Interactive wizard with beautiful progress displays
- **🔗 CI/CD Integration**: GitHub Actions and GitLab CI pipeline generation
- **📋 IaC Export**: Generate Terraform, CloudFormation, Pulumi, and Ansible code
- **🚀 REST API**: Complete automation API with FastAPI
- **📈 Analytics**: Usage trends, cost predictions, and optimization recommendations
- **🔔 Notifications**: Webhook alerts for deployments and cost overages

### 🛡️ Safety Features

- **Dry-run mode**: Validate plans without provisioning
- **Free-tier validation**: Prevent accidental paid resource deployment
- **Cost alerts**: Real-time notifications when approaching limits
- **Dependency management**: Automatic deployment ordering
- **Rollback capabilities**: Undo deployments on failures

## 🤝 Contributing

1. **Fork and clone the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Write tests first** (TDD methodology)
4. **Implement your feature**
5. **Ensure tests pass**: `uv run pytest`
6. **Submit a pull request**

## 📚 Documentation

- **[ROADMAP.md](ROADMAP.md)**: Development roadmap and completed phases
- **[CLAUDE.md](CLAUDE.md)**: AI development notes and project status
- **[examples/](examples/)**: Complete usage examples and demos
- **[API Documentation](http://localhost:8000/docs)**: Interactive API docs (when server is running)

## 🐛 Troubleshooting

### Common Issues

**Import errors when running examples:**
```bash
# Make sure to use uv run for proper environment
uv run python your-script.py
# NOT: python your-script.py
```

**Tests failing:**
```bash
# Ensure all dependencies are installed
uv sync
# Check Python version (needs 3.11+)
python --version
```

**CLI not found:**
```bash
# Use uv run prefix
uv run sentinel --help
# Or install in development mode
uv pip install -e .
```

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Test-Driven Development (TDD) methodology
- Powered by [FastAPI](https://fastapi.tiangolo.com/), [Click](https://click.palletsprojects.com/), [Rich](https://rich.readthedocs.io/)
- Cloud SDKs: [boto3](https://boto3.amazonaws.com/), [google-cloud](https://cloud.google.com/python), [azure-sdk](https://azure.github.io/azure-sdk-for-python/)

---

**⭐ If you find this project useful, please give it a star!**

---

*Free-Tier Sentinel: Maximize your cloud free-tier benefits with intelligent planning and monitoring* 🚀