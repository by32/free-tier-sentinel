"""Plan save/load and management functionality."""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, UTC

from sentinel.models.core import Plan, Resource


class PlanManager:
    """Manage deployment plan persistence and operations."""
    
    def save_plan(self, plan: Plan, file_path: Path):
        """Save a deployment plan to a JSON file."""
        plan_data = self._plan_to_dict(plan)
        
        # Add metadata
        plan_data['metadata'] = {
            'saved_at': datetime.now(UTC).isoformat(),
            'version': '1.0'
        }
        
        with open(file_path, 'w') as f:
            json.dump(plan_data, f, indent=2, default=str)
    
    def load_plan(self, file_path: Path) -> Plan:
        """Load a deployment plan from a JSON file."""
        if not file_path.exists():
            raise FileNotFoundError(f"Plan file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            plan_data = json.load(f)
        
        return self._dict_to_plan(plan_data)
    
    def compare_plans(self, plan1: Plan, plan2: Plan) -> Dict[str, Any]:
        """Compare two deployment plans and return differences."""
        diff = {}
        
        # Compare plan metadata
        if plan1.name != plan2.name:
            diff['name'] = {'old': plan1.name, 'new': plan2.name}
        
        if plan1.description != plan2.description:
            diff['description'] = {'old': plan1.description, 'new': plan2.description}
        
        # Compare resources
        resources_diff = self._compare_resources(plan1.resources, plan2.resources)
        if resources_diff:
            diff['resources'] = resources_diff
        
        return diff
    
    def _plan_to_dict(self, plan: Plan) -> Dict[str, Any]:
        """Convert a Plan object to dictionary format."""
        return {
            'name': plan.name,
            'description': plan.description,
            'resources': [self._resource_to_dict(resource) for resource in plan.resources],
            'estimated_cost': float(plan.total_estimated_cost),
            'created_at': plan.created_at.isoformat() if plan.created_at else None
        }
    
    def _resource_to_dict(self, resource: Resource) -> Dict[str, Any]:
        """Convert a Resource object to dictionary format."""
        return {
            'provider': resource.provider,
            'service': resource.service,
            'resource_type': resource.resource_type,
            'region': resource.region,
            'quantity': resource.quantity,
            'estimated_monthly_usage': resource.estimated_monthly_usage
        }
    
    def _dict_to_plan(self, plan_data: Dict[str, Any]) -> Plan:
        """Convert dictionary data to a Plan object."""
        resources = []
        for resource_data in plan_data.get('resources', []):
            resource = Resource(
                provider=resource_data['provider'],
                service=resource_data['service'],
                resource_type=resource_data['resource_type'],
                region=resource_data['region'],
                quantity=resource_data['quantity'],
                estimated_monthly_usage=resource_data['estimated_monthly_usage']
            )
            resources.append(resource)
        
        return Plan(
            name=plan_data['name'],
            description=plan_data['description'],
            resources=resources
        )
    
    def _compare_resources(self, resources1: list[Resource], resources2: list[Resource]) -> Dict[str, Any]:
        """Compare two lists of resources."""
        if len(resources1) != len(resources2):
            return {
                'count_changed': {
                    'old': len(resources1),
                    'new': len(resources2)
                }
            }
        
        # For now, return empty diff if counts match
        # More sophisticated comparison could be added here
        return {}