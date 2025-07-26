"""AWS provisioning adapter implementation."""

import uuid
from datetime import datetime, UTC
from typing import Optional

from sentinel.models.core import Resource
from ..engine import ProvisioningResult, ProvisioningState, ProvisioningError


class AWSProvisioningAdapter:
    """AWS-specific provisioning adapter."""
    
    def __init__(self, capacity_aggregator=None):
        """Initialize AWS adapter with optional capacity integration."""
        self.provider = "aws"
        self.capacity_aggregator = capacity_aggregator
    
    def provision_resource(self, resource: Resource) -> ProvisioningResult:
        """Provision a single AWS resource."""
        # Check capacity if available
        capacity_checked = False
        if self.capacity_aggregator:
            capacity_result = self.capacity_aggregator.check_availability(
                resource.provider, resource.region, resource.resource_type
            )
            capacity_checked = True
            
            if not capacity_result.available:
                error = ProvisioningError(
                    resource_type=resource.resource_type,
                    provider=resource.provider,
                    error_type="CAPACITY_EXCEEDED",
                    error_message=f"No capacity available for {resource.resource_type} in {resource.region}",
                    retry_suggested=True
                )
                return ProvisioningResult(
                    resource=resource,
                    state=ProvisioningState.FAILED,
                    error=error,
                    capacity_checked=capacity_checked
                )
        
        # Mock provisioning logic based on service
        if resource.service == "ec2":
            return self.provision_ec2_instance(resource, capacity_checked)
        elif resource.service == "s3":
            return self.provision_s3_bucket(resource, capacity_checked)
        else:
            # Generic resource provisioning
            resource_id = f"{resource.service}-{uuid.uuid4().hex[:8]}"
            return ProvisioningResult(
                resource=resource,
                state=ProvisioningState.READY,
                resource_id=resource_id,
                provider_specific_data={
                    "service": resource.service,
                    "region": resource.region
                },
                capacity_checked=capacity_checked
            )
    
    def provision_ec2_instance(self, resource: Resource, capacity_checked: bool = False) -> ProvisioningResult:
        """Provision an EC2 instance."""
        # Generate EC2-style instance ID
        instance_id = f"i-{uuid.uuid4().hex[:16]}"
        
        provider_data = {
            "instance_id": instance_id,
            "instance_type": resource.resource_type,
            "region": resource.region,
            "vpc_id": f"vpc-{uuid.uuid4().hex[:8]}",
            "subnet_id": f"subnet-{uuid.uuid4().hex[:8]}"
        }
        
        return ProvisioningResult(
            resource=resource,
            state=ProvisioningState.READY,
            resource_id=instance_id,
            provider_specific_data=provider_data,
            capacity_checked=capacity_checked
        )
    
    def provision_s3_bucket(self, resource: Resource, capacity_checked: bool = False) -> ProvisioningResult:
        """Provision an S3 bucket."""
        # Generate S3 bucket name
        bucket_name = f"{self.provider}-{uuid.uuid4().hex[:8]}-bucket"
        
        provider_data = {
            "bucket_name": bucket_name,
            "region": resource.region,
            "storage_class": "STANDARD",
            "versioning": False
        }
        
        return ProvisioningResult(
            resource=resource,
            state=ProvisioningState.READY,
            resource_id=bucket_name,
            provider_specific_data=provider_data,
            capacity_checked=capacity_checked
        )
    
    def get_resource_status(self, resource_id: str) -> Optional[ProvisioningResult]:
        """Get the current status of a provisioned resource."""
        # Mock implementation - in real world this would query AWS APIs
        return None