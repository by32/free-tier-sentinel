"""Interactive planning wizard and command-line planning utilities."""

import click
from typing import List, Optional
from datetime import datetime, UTC

from sentinel.models.core import Resource, Plan


SUPPORTED_PROVIDERS = {
    'aws': {
        'name': 'Amazon Web Services',
        'regions': ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'],
        'services': {
            'ec2': ['t2.micro', 't3.micro', 't2.small', 't3.small'],
            's3': ['standard_storage']
        }
    },
    'gcp': {
        'name': 'Google Cloud Platform',
        'regions': ['us-central1', 'us-west1', 'europe-west1', 'asia-east1'],
        'services': {
            'compute': ['e2-micro', 'e2-small', 'f1-micro'],
            'storage': ['standard_storage']
        }
    },
    'azure': {
        'name': 'Microsoft Azure',
        'regions': ['eastus', 'westus2', 'westeurope', 'southeastasia'],
        'services': {
            'vm': ['Standard_B1s', 'Standard_B2s'],
            'storage': ['standard_storage']
        }
    }
}


class InteractivePlanner:
    """Interactive wizard for creating deployment plans."""
    
    def __init__(self):
        self.resources: List[Resource] = []
    
    def create_plan(self) -> Plan:
        """Launch interactive wizard to create a deployment plan."""
        click.echo("Welcome to Free-Tier Sentinel Interactive Planner!")
        click.echo("This wizard will help you create a deployment plan for free-tier cloud resources.\n")
        
        # Select provider
        provider = self._select_provider()
        
        # Select region
        region = self._select_region(provider)
        
        # Configure resources
        self._configure_resources(provider, region)
        
        # Create plan metadata
        plan_name = click.prompt("Enter plan name", default="free-tier-deployment")
        plan_description = click.prompt("Enter plan description", default="Free-tier resource deployment")
        
        # Confirm plan
        if self._confirm_plan(plan_name, plan_description):
            return Plan(
                name=plan_name,
                description=plan_description,
                resources=self.resources
            )
        else:
            click.echo("Plan creation cancelled.")
            raise click.Abort()
    
    def _select_provider(self) -> str:
        """Interactive provider selection."""
        click.echo("Available cloud providers:")
        for key, info in SUPPORTED_PROVIDERS.items():
            click.echo(f"  {key}: {info['name']}")
        
        while True:
            provider = click.prompt("Choose a provider", type=click.Choice(list(SUPPORTED_PROVIDERS.keys())))
            if self.validate_provider(provider):
                return provider
            click.echo("Invalid provider. Please try again.")
    
    def _select_region(self, provider: str) -> str:
        """Interactive region selection."""
        regions = SUPPORTED_PROVIDERS[provider]['regions']
        click.echo(f"\nAvailable regions for {provider}:")
        for region in regions:
            click.echo(f"  {region}")
        
        while True:
            region = click.prompt("Choose a region", type=click.Choice(regions))
            if self.validate_region(provider, region):
                return region
            click.echo("Invalid region. Please try again.")
    
    def _configure_resources(self, provider: str, region: str):
        """Interactive resource configuration."""
        configurator = ResourceConfigurator()
        services = SUPPORTED_PROVIDERS[provider]['services']
        
        click.echo(f"\nConfiguring resources for {provider} in {region}")
        
        # Configure EC2/Compute instances
        if 'ec2' in services or 'compute' in services or 'vm' in services:
            if click.confirm("Add compute instances?", default=True):
                service_name = 'ec2' if 'ec2' in services else ('compute' if 'compute' in services else 'vm')
                resource = configurator.configure_compute_instance(provider, region, service_name)
                self.resources.append(resource)
        
        # Configure storage
        if any(s in services for s in ['s3', 'storage']):
            if click.confirm("Add storage bucket?", default=False):
                service_name = 's3' if 's3' in services else 'storage'
                resource = configurator.configure_storage_bucket(provider, region, service_name)
                self.resources.append(resource)
    
    def _confirm_plan(self, plan_name: str, plan_description: str) -> bool:
        """Confirm the plan before creation."""
        click.echo(f"\nPlan Summary:")
        click.echo(f"Name: {plan_name}")
        click.echo(f"Description: {plan_description}")
        click.echo(f"Resources:")
        
        for resource in self.resources:
            click.echo(f"  - {resource.provider} {resource.service} {resource.resource_type} "
                      f"(qty: {resource.quantity}, region: {resource.region})")
        
        return click.confirm("\nCreate this plan?", default=True)
    
    def validate_provider(self, provider: str) -> bool:
        """Validate provider selection."""
        return provider in SUPPORTED_PROVIDERS
    
    def validate_region(self, provider: str, region: str) -> bool:
        """Validate region for the selected provider."""
        if provider not in SUPPORTED_PROVIDERS:
            return False
        return region in SUPPORTED_PROVIDERS[provider]['regions']


class ResourceConfigurator:
    """Helper class for configuring individual resources."""
    
    def configure_compute_instance(self, provider: str, region: str, service: str) -> Resource:
        """Configure a compute instance resource."""
        services = SUPPORTED_PROVIDERS[provider]['services']
        instance_types = services.get(service, ['t2.micro'])
        
        click.echo(f"\nConfiguring {service} instance:")
        click.echo(f"Available instance types: {', '.join(instance_types)}")
        
        instance_type = click.prompt("Choose instance type", 
                                   type=click.Choice(instance_types),
                                   default=instance_types[0])
        
        quantity = click.prompt("Number of instances", type=int, default=1)
        usage = click.prompt("Estimated monthly usage (hours)", type=int, default=100)
        
        return Resource(
            provider=provider,
            service=service,
            resource_type=instance_type,
            region=region,
            quantity=quantity,
            estimated_monthly_usage=usage
        )
    
    def configure_storage_bucket(self, provider: str, region: str, service: str) -> Resource:
        """Configure a storage bucket resource."""
        click.echo(f"\nConfiguring {service} storage:")
        
        storage_gb = click.prompt("Storage size (GB)", type=int, default=5)
        
        return Resource(
            provider=provider,
            service=service,
            resource_type="standard_storage",
            region=region,
            quantity=1,
            estimated_monthly_usage=storage_gb
        )
    
    def configure_ec2_instance(self, provider: str, region: str) -> Resource:
        """Legacy method for EC2 configuration (for test compatibility)."""
        return self.configure_compute_instance(provider, region, 'ec2')


class CommandLinePlanner:
    """Create plans from command-line arguments."""
    
    def create_plan_from_args(self, provider: str, region: str, resource_specs: tuple) -> Plan:
        """Create a plan from command-line resource specifications."""
        resources = []
        
        for spec in resource_specs:
            # Parse resource specification: service:type:quantity
            parts = spec.split(':')
            if len(parts) != 3:
                raise ValueError(f"Invalid resource specification: {spec}. Expected format: service:type:quantity")
            
            service, resource_type, quantity_str = parts
            try:
                quantity = int(quantity_str)
            except ValueError:
                raise ValueError(f"Invalid quantity in resource specification: {spec}")
            
            resource = Resource(
                provider=provider,
                service=service,
                resource_type=resource_type,
                region=region,
                quantity=quantity,
                estimated_monthly_usage=100  # Default usage
            )
            resources.append(resource)
        
        return Plan(
            name=f"cli-plan-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}",
            description=f"Plan created from command line for {provider} in {region}",
            resources=resources
        )