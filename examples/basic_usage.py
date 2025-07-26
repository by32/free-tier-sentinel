#!/usr/bin/env python3
"""
Basic usage examples for Free-Tier Sentinel

Run with: uv run python examples/basic_usage.py
"""

from sentinel.models.core import Resource, Plan
from sentinel.cli.plan_manager import PlanManager
from sentinel.cli.dry_run import DryRunValidator
from sentinel.integration.iac import IaCExporter, IaCFormat


def example_1_create_basic_plan():
    """Example 1: Create a basic AWS free-tier plan"""
    print("=== Example 1: Basic AWS Free-Tier Plan ===")
    
    # Create resources
    ec2_instance = Resource(
        provider="aws",
        service="ec2",
        resource_type="t2.micro",
        region="us-east-1",
        quantity=1,
        estimated_monthly_usage=100
    )
    
    s3_storage = Resource(
        provider="aws",
        service="s3",
        resource_type="standard_storage",
        region="us-east-1",
        quantity=1,
        estimated_monthly_usage=5  # 5 GB
    )
    
    # Create plan
    plan = Plan(
        name="aws-free-tier-basic",
        description="Basic AWS free-tier deployment with EC2 and S3",
        resources=[ec2_instance, s3_storage]
    )
    
    print(f"Plan: {plan.name}")
    print(f"Description: {plan.description}")
    print(f"Resources: {len(plan.resources)}")
    print(f"Estimated cost: ${plan.total_estimated_cost}")
    
    for resource in plan.resources:
        print(f"  - {resource.provider} {resource.service} {resource.resource_type}")
    
    return plan


def example_2_validate_plan(plan):
    """Example 2: Validate a plan with dry-run"""
    print("\n=== Example 2: Plan Validation ===")
    
    validator = DryRunValidator()
    result = validator.validate_plan(plan)
    
    print(f"Valid: {result.is_valid}")
    print(f"Total resources: {result.total_resources}")
    print(f"Estimated cost: ${result.estimated_cost}")
    
    if result.validation_warnings:
        print("Warnings:")
        for warning in result.validation_warnings:
            print(f"  - {warning}")
    else:
        print("No warnings - plan looks good!")


def example_3_save_and_load_plan(plan):
    """Example 3: Save and load plans"""
    print("\n=== Example 3: Save/Load Plans ===")
    
    manager = PlanManager()
    
    # Save plan
    from pathlib import Path
    plan_file = Path("example_plan.json")
    manager.save_plan(plan, plan_file)
    print(f"Plan saved to: {plan_file}")
    
    # Load plan
    loaded_plan = manager.load_plan(plan_file)
    print(f"Loaded plan: {loaded_plan.name}")
    print(f"Resources: {len(loaded_plan.resources)}")
    
    # Clean up
    plan_file.unlink()
    print("Temporary file cleaned up")


def example_4_export_to_terraform(plan):
    """Example 4: Export plan to Terraform"""
    print("\n=== Example 4: Export to Terraform ===")
    
    exporter = IaCExporter()
    terraform_code = exporter.export(plan, IaCFormat.TERRAFORM)
    
    print("Generated Terraform code:")
    print("=" * 50)
    print(terraform_code[:500] + "..." if len(terraform_code) > 500 else terraform_code)
    print("=" * 50)


def example_5_multi_cloud_plan():
    """Example 5: Multi-cloud deployment plan"""
    print("\n=== Example 5: Multi-Cloud Plan ===")
    
    resources = [
        # AWS resources
        Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        ),
        
        # GCP resources
        Resource(
            provider="gcp",
            service="compute",
            resource_type="e2-micro",
            region="us-central1",
            quantity=1,
            estimated_monthly_usage=100
        ),
        
        # Azure resources
        Resource(
            provider="azure",
            service="vm",
            resource_type="Standard_B1s",
            region="eastus",
            quantity=1,
            estimated_monthly_usage=100
        )
    ]
    
    multi_plan = Plan(
        name="multi-cloud-free-tier",
        description="Free-tier resources across AWS, GCP, and Azure",
        resources=resources
    )
    
    print(f"Multi-cloud plan: {multi_plan.name}")
    print("Resources by provider:")
    
    by_provider = {}
    for resource in multi_plan.resources:
        if resource.provider not in by_provider:
            by_provider[resource.provider] = []
        by_provider[resource.provider].append(resource)
    
    for provider, provider_resources in by_provider.items():
        print(f"  {provider.upper()}: {len(provider_resources)} resources")
        for resource in provider_resources:
            print(f"    - {resource.service} {resource.resource_type} in {resource.region}")
    
    return multi_plan


def main():
    """Run all examples"""
    print("🛡️  Free-Tier Sentinel - Basic Usage Examples")
    print("=" * 60)
    
    # Example 1: Create basic plan
    plan = example_1_create_basic_plan()
    
    # Example 2: Validate plan
    example_2_validate_plan(plan)
    
    # Example 3: Save and load
    example_3_save_and_load_plan(plan)
    
    # Example 4: Export to Terraform
    example_4_export_to_terraform(plan)
    
    # Example 5: Multi-cloud plan
    multi_plan = example_5_multi_cloud_plan()
    
    print("\n🎉 All examples completed successfully!")
    print("\nNext steps:")
    print("- Try the interactive CLI: uv run sentinel plan --interactive")
    print("- Create your own plan files with YAML configuration")
    print("- Explore advanced features in other example files")


if __name__ == "__main__":
    main()