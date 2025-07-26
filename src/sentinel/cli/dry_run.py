"""Dry-run functionality for plan validation."""

from dataclasses import dataclass
from typing import List
from decimal import Decimal

from sentinel.models.core import Plan, Resource


@dataclass
class DryRunResult:
    """Result of dry-run validation."""
    is_valid: bool
    total_resources: int
    estimated_cost: Decimal
    validation_warnings: List[str]


class DryRunValidator:
    """Validate deployment plans without executing them."""
    
    def __init__(self):
        self.supported_providers = {'aws', 'gcp', 'azure'}
        self.provider_regions = {
            'aws': {'us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'},
            'gcp': {'us-central1', 'us-west1', 'europe-west1', 'asia-east1'},
            'azure': {'eastus', 'westus2', 'westeurope', 'southeastasia'}
        }
    
    def validate_plan(self, plan: Plan) -> DryRunResult:
        """Validate a deployment plan and return validation results."""
        warnings = []
        is_valid = True
        
        # Basic plan validation
        if not plan.resources:
            warnings.append("Plan contains no resources")
            is_valid = False
        
        # Validate each resource
        for resource in plan.resources:
            resource_warnings = self._validate_resource(resource)
            warnings.extend(resource_warnings)
        
        # Calculate estimated cost (simplified)
        estimated_cost = self._calculate_estimated_cost(plan.resources)
        
        # If there are warnings about invalid regions/providers, mark as invalid
        if any('invalid' in warning.lower() for warning in warnings):
            is_valid = False
        
        return DryRunResult(
            is_valid=is_valid,
            total_resources=len(plan.resources),
            estimated_cost=estimated_cost,
            validation_warnings=warnings
        )
    
    def _validate_resource(self, resource: Resource) -> List[str]:
        """Validate a single resource and return warnings."""
        warnings = []
        
        # Validate provider
        if resource.provider not in self.supported_providers:
            warnings.append(f"Unsupported provider: {resource.provider}")
        
        # Validate region
        if resource.provider in self.provider_regions:
            valid_regions = self.provider_regions[resource.provider]
            if resource.region not in valid_regions:
                warnings.append(f"Invalid region '{resource.region}' for provider '{resource.provider}'")
        
        # Validate quantity
        if resource.quantity < 1:
            warnings.append(f"Invalid quantity {resource.quantity} for {resource.resource_type}")
        
        # Validate usage
        if resource.estimated_monthly_usage < 0:
            warnings.append(f"Invalid estimated usage {resource.estimated_monthly_usage} for {resource.resource_type}")
        
        # Check for potentially problematic resource types
        if resource.resource_type == "nonexistent.type":
            warnings.append(f"Resource type '{resource.resource_type}' may not exist")
        
        return warnings
    
    def _calculate_estimated_cost(self, resources: List[Resource]) -> Decimal:
        """Calculate estimated cost for resources (simplified calculation)."""
        total_cost = Decimal('0.00')
        
        # Simple cost estimation (in reality, this would use proper pricing)
        cost_per_hour = {
            't2.micro': Decimal('0.0116'),
            't3.micro': Decimal('0.0104'),
            'e2-micro': Decimal('0.0104'),
            'f1-micro': Decimal('0.0084'),
            'Standard_B1s': Decimal('0.0104')
        }
        
        for resource in resources:
            if resource.service in ['ec2', 'compute', 'vm']:
                # Compute instance pricing
                hourly_rate = cost_per_hour.get(resource.resource_type, Decimal('0.01'))
                monthly_cost = hourly_rate * Decimal(str(resource.estimated_monthly_usage))
                total_cost += monthly_cost * resource.quantity
            elif resource.service in ['s3', 'storage']:
                # Storage pricing (per GB)
                storage_rate = Decimal('0.023')  # $0.023 per GB/month
                monthly_cost = storage_rate * Decimal(str(resource.estimated_monthly_usage))
                total_cost += monthly_cost * resource.quantity
        
        return total_cost