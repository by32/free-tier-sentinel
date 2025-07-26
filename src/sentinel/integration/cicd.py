"""CI/CD pipeline integration features."""

from abc import ABC, abstractmethod
from typing import Dict, Any

from sentinel.models.core import Plan


class CICDIntegration(ABC):
    """Abstract base class for CI/CD integrations."""
    
    @abstractmethod
    def generate_pipeline_config(self, plan: Plan) -> str:
        """Generate pipeline configuration for the plan."""
        raise NotImplementedError("Subclasses must implement generate_pipeline_config")
    
    @abstractmethod
    def validate_plan_in_pipeline(self, plan: Plan) -> bool:
        """Validate plan within CI/CD pipeline context."""
        raise NotImplementedError("Subclasses must implement validate_plan_in_pipeline")
    
    @abstractmethod
    def deploy_from_pipeline(self, plan: Plan, environment: str) -> Dict[str, Any]:
        """Deploy plan from CI/CD pipeline."""
        raise NotImplementedError("Subclasses must implement deploy_from_pipeline")


class GitHubActionsIntegration(CICDIntegration):
    """GitHub Actions integration for Free-Tier Sentinel."""
    
    def generate_pipeline_config(self, plan: Plan) -> str:
        """Generate GitHub Actions workflow YAML."""
        workflow_yaml = f"""name: Free-Tier Sentinel Deployment

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Free-Tier Sentinel
      run: |
        pip install free-tier-sentinel
    
    - name: Validate deployment plan
      run: |
        sentinel plan --config plan.yaml --dry-run
    
    - name: Check capacity availability
      run: |
        sentinel plan --config plan.yaml --dry-run --check-capacity

  deploy:
    runs-on: ubuntu-latest
    needs: validate
    if: github.ref == 'refs/heads/main'
    environment: production
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install Free-Tier Sentinel
      run: |
        pip install free-tier-sentinel
    
    - name: Deploy resources
      env:
        AWS_ACCESS_KEY_ID: ${{{{ secrets.AWS_ACCESS_KEY_ID }}}}
        AWS_SECRET_ACCESS_KEY: ${{{{ secrets.AWS_SECRET_ACCESS_KEY }}}}
        GCP_SERVICE_ACCOUNT_KEY: ${{{{ secrets.GCP_SERVICE_ACCOUNT_KEY }}}}
        AZURE_CLIENT_ID: ${{{{ secrets.AZURE_CLIENT_ID }}}}
        AZURE_CLIENT_SECRET: ${{{{ secrets.AZURE_CLIENT_SECRET }}}}
        AZURE_TENANT_ID: ${{{{ secrets.AZURE_TENANT_ID }}}}
      run: |
        sentinel provision --plan-file plan.yaml --progress
    
    - name: Verify deployment
      run: |
        sentinel status --all
"""
        return workflow_yaml
    
    def validate_plan_in_pipeline(self, plan: Plan) -> bool:
        """Validate plan for GitHub Actions deployment."""
        # Check if plan is suitable for CI/CD
        if len(plan.resources) == 0:
            return False
        
        # Ensure all resources are free-tier compatible
        free_tier_types = {"t2.micro", "t3.micro", "e2-micro", "f1-micro", "Standard_B1s"}
        for resource in plan.resources:
            if resource.resource_type not in free_tier_types:
                return False
        
        return True
    
    def deploy_from_pipeline(self, plan: Plan, environment: str) -> Dict[str, Any]:
        """Deploy plan from GitHub Actions pipeline."""
        # Mock deployment result
        return {
            "status": "success",
            "environment": environment,
            "deployment_id": f"gh-deploy-{hash(plan.name) % 10000}",
            "resources_deployed": len(plan.resources),
            "pipeline_run_id": "github-actions-run-123"
        }


class GitLabCIIntegration(CICDIntegration):
    """GitLab CI integration for Free-Tier Sentinel."""
    
    def generate_pipeline_config(self, plan: Plan) -> str:
        """Generate GitLab CI YAML configuration."""
        gitlab_yaml = f"""stages:
  - validate
  - deploy

variables:
  PYTHON_VERSION: "3.11"

validate_plan:
  stage: validate
  image: python:$PYTHON_VERSION
  script:
    - pip install free-tier-sentinel
    - sentinel plan --config plan.yaml --dry-run
    - sentinel plan --config plan.yaml --dry-run --check-capacity
  only:
    - main
    - merge_requests

deploy_resources:
  stage: deploy
  image: python:$PYTHON_VERSION
  script:
    - pip install free-tier-sentinel
    - sentinel provision --plan-file plan.yaml --progress
    - sentinel status --all
  environment:
    name: production
  only:
    - main
  when: manual
"""
        return gitlab_yaml
    
    def validate_plan_in_pipeline(self, plan: Plan) -> bool:
        """Validate plan for GitLab CI deployment."""
        return len(plan.resources) > 0
    
    def deploy_from_pipeline(self, plan: Plan, environment: str) -> Dict[str, Any]:
        """Deploy plan from GitLab CI pipeline."""
        return {
            "status": "success",
            "environment": environment,
            "deployment_id": f"gitlab-deploy-{hash(plan.name) % 10000}",
            "resources_deployed": len(plan.resources),
            "pipeline_id": "gitlab-ci-pipeline-456"
        }