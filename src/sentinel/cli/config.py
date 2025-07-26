"""Configuration file loading and validation."""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List

from sentinel.models.core import Resource, Plan


class ConfigValidationError(Exception):
    """Raised when configuration file validation fails."""
    pass


class ConfigLoader:
    """Load deployment plans from YAML/JSON configuration files."""
    
    def load_from_file(self, config_path: Path) -> Plan:
        """Load a deployment plan from configuration file."""
        if not config_path.exists():
            raise ConfigValidationError(f"Configuration file not found: {config_path}")
        
        try:
            # Determine file type and load
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                config_data = self._load_yaml(config_path)
            elif config_path.suffix.lower() == '.json':
                config_data = self._load_json(config_path)
            else:
                raise ConfigValidationError(f"Unsupported file format: {config_path.suffix}")
            
            # Validate and convert to Plan
            return self._create_plan_from_config(config_data)
            
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ConfigValidationError(f"Failed to parse configuration file: {str(e)}")
        except Exception as e:
            raise ConfigValidationError(f"Configuration validation error: {str(e)}")
    
    def _load_yaml(self, config_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file."""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_json(self, config_path: Path) -> Dict[str, Any]:
        """Load JSON configuration file."""
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _create_plan_from_config(self, config_data: Dict[str, Any]) -> Plan:
        """Create a Plan object from configuration data."""
        self._validate_config_structure(config_data)
        
        # Extract plan metadata
        plan_info = config_data.get('plan', {})
        plan_name = plan_info.get('name', 'config-plan')
        plan_description = plan_info.get('description', 'Plan loaded from configuration file')
        
        # Parse resources
        resources = []
        for resource_config in config_data.get('resources', []):
            resource = self._create_resource_from_config(resource_config)
            resources.append(resource)
        
        return Plan(
            name=plan_name,
            description=plan_description,
            resources=resources
        )
    
    def _validate_config_structure(self, config_data: Dict[str, Any]):
        """Validate the basic structure of configuration data."""
        if not isinstance(config_data, dict):
            raise ConfigValidationError("Configuration must be a JSON object or YAML document")
        
        if 'resources' not in config_data:
            raise ConfigValidationError("Configuration must contain a 'resources' section")
        
        if not isinstance(config_data['resources'], list):
            raise ConfigValidationError("'resources' must be an array/list")
        
        if len(config_data['resources']) == 0:
            raise ConfigValidationError("At least one resource must be specified")
    
    def _create_resource_from_config(self, resource_config: Dict[str, Any]) -> Resource:
        """Create a Resource object from configuration data."""
        required_fields = ['provider', 'service', 'resource_type', 'region']
        
        # Validate required fields
        for field in required_fields:
            if field not in resource_config:
                raise ConfigValidationError(f"Resource missing required field: {field}")
        
        # Extract values with defaults
        provider = resource_config['provider']
        service = resource_config['service']
        resource_type = resource_config['resource_type']
        region = resource_config['region']
        quantity = resource_config.get('quantity', 1)
        estimated_monthly_usage = resource_config.get('estimated_monthly_usage', 100)
        
        # Validate types
        if not isinstance(quantity, int) or quantity < 1:
            raise ConfigValidationError(f"Invalid quantity: {quantity}. Must be a positive integer")
        
        if not isinstance(estimated_monthly_usage, (int, float)) or estimated_monthly_usage < 0:
            raise ConfigValidationError(f"Invalid estimated_monthly_usage: {estimated_monthly_usage}. Must be non-negative")
        
        return Resource(
            provider=provider,
            service=service,
            resource_type=resource_type,
            region=region,
            quantity=quantity,
            estimated_monthly_usage=estimated_monthly_usage
        )