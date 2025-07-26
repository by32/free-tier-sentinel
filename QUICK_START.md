# ⚡ Quick Start Guide

**Get up and running with Free-Tier Sentinel in 5 minutes!**

## 🎯 Prerequisites Check

Before starting, ensure you have:
- ✅ Python 3.11+ installed
- ✅ uv package manager installed  
- ✅ Git installed

```bash
# Check versions
python --version    # Should be 3.11+
uv --version       # Should show uv version
git --version      # Should show git version
```

## 🚀 5-Minute Setup

### Step 1: Clone and Install (2 minutes)

```bash
# Clone the repository
git clone https://github.com/by32/free-tier-sentinel.git
cd free-tier-sentinel

# Install all dependencies
uv sync

# This installs:
# - Core dependencies (pydantic, click, rich, etc.)
# - Cloud SDKs (boto3, google-cloud, azure)
# - Testing tools (pytest, coverage)
# - API framework (fastapi, uvicorn)
```

### Step 2: Verify Installation (1 minute)

```bash
# Test that everything works
uv run pytest tests/test_models.py -v

# Expected: All tests pass
# ✅ If this works, your environment is perfect!

# Test CLI
uv run sentinel --help

# Expected: CLI help text with available commands
```

### Step 3: First Dry Run (1 minute)

```bash
# Plan a simple free-tier deployment
uv run sentinel plan \
  --provider aws \
  --region us-east-1 \
  --resource ec2:t2.micro:1 \
  --dry-run

# Expected output:
# ✅ Plan validation successful
# ℹ️  Total resources: 1
# ℹ️  Estimated cost: $1.1600
# ℹ️  No resources will be provisioned in dry-run mode
```

### Step 4: Interactive Planning (1 minute)

```bash
# Try the interactive wizard
uv run sentinel plan --interactive

# Follow prompts:
# 1. Choose provider: aws
# 2. Choose region: us-east-1  
# 3. Add compute instances? y
# 4. Choose instance type: t2.micro
# 5. Number of instances: 1
# 6. Usage hours: 100
# 7. Add storage? n
# 8. Plan name: my-first-plan
# 9. Description: My first free-tier plan
# 10. Create plan? y
```

## 🎉 You're Ready!

**Congratulations! You now have a working Free-Tier Sentinel installation.**

## 🎯 What to Try Next

### Option A: Create a Real Plan File

```bash
# Create plan.yaml
cat << EOF > plan.yaml
plan:
  name: "my-multi-cloud-setup"
  description: "Free-tier resources across providers"

resources:
  - provider: aws
    service: ec2
    resource_type: t2.micro
    region: us-east-1
    quantity: 1
    estimated_monthly_usage: 100
    
  - provider: gcp
    service: compute
    resource_type: e2-micro
    region: us-central1
    quantity: 1
    estimated_monthly_usage: 100
EOF

# Validate it
uv run sentinel plan --config plan.yaml --dry-run
```

### Option B: Try Advanced Features

```bash
# Export to Terraform
uv run python -c "
from sentinel.integration.iac import IaCExporter, IaCFormat
from sentinel.models.core import Resource, Plan

exporter = IaCExporter()
resource = Resource(
    provider='aws', 
    service='ec2', 
    resource_type='t2.micro', 
    region='us-east-1', 
    quantity=1, 
    estimated_monthly_usage=100
)
plan = Plan(name='terraform-demo', description='Demo plan', resources=[resource])

print(exporter.export(plan, IaCFormat.TERRAFORM))
"
```

### Option C: Start the API Server

```bash
# Terminal 1: Start API server
uv run python -c "
from sentinel.integration.api import SentinelAPI
import uvicorn

api = SentinelAPI()
uvicorn.run(api.app, host='0.0.0.0', port=8000)
" &

# Terminal 2: Test API
curl http://localhost:8000/health
```

## 🔧 Troubleshooting

**CLI not found?**
```bash
# Always use 'uv run' prefix
uv run sentinel --help
```

**Import errors?**
```bash
# Reinstall dependencies
uv sync --reinstall
```

**Tests failing?**
```bash
# Check Python version
python --version  # Must be 3.11+

# Update dependencies
uv lock --upgrade
uv sync
```

## 📚 Next Steps

- **Read the full [README.md](README.md)** for comprehensive usage
- **Check [ROADMAP.md](ROADMAP.md)** to see all implemented features
- **Browse [examples/](examples/)** for advanced usage patterns
- **Run the full test suite**: `uv run pytest`

## 🎯 Key Commands Reference

```bash
# Planning
uv run sentinel plan --interactive                    # Interactive wizard
uv run sentinel plan --config plan.yaml --dry-run    # Validate from file
uv run sentinel plan --provider aws --region us-east-1 --resource ec2:t2.micro:1 --dry-run

# Help
uv run sentinel --help           # Main help
uv run sentinel plan --help      # Plan command help
uv run sentinel provision --help # Provision command help

# Testing
uv run pytest                    # Run all tests
uv run pytest tests/test_cli.py  # Test CLI only
uv run pytest --cov=src         # With coverage

# Development
uv sync                          # Install/update dependencies
uv run ruff check src           # Lint code
uv run mypy src                 # Type checking
```

**Happy cloud planning! 🚀**