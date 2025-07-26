"""Core provisioning engine interfaces and data structures."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
from typing import Any, Optional

from sentinel.models.core import Resource, Plan


class ProvisioningState(Enum):
    """States for resource provisioning lifecycle."""
    PENDING = "pending"
    PROVISIONING = "provisioning"
    READY = "ready"
    FAILED = "failed"
    ROLLBACK = "rollback"


@dataclass
class ProvisioningError:
    """Error information for provisioning failures."""
    resource_type: str
    provider: str
    error_type: str
    error_message: str
    retry_after: Optional[timedelta] = None
    retry_suggested: bool = False


@dataclass
class ProvisioningResult:
    """Result of provisioning a single resource."""
    resource: Resource
    state: ProvisioningState
    resource_id: Optional[str] = None
    provisioned_at: Optional[datetime] = None
    error: Optional[ProvisioningError] = None
    provider_specific_data: dict[str, Any] = field(default_factory=dict)
    capacity_checked: bool = False

    def __post_init__(self):
        if self.state == ProvisioningState.READY and self.provisioned_at is None:
            self.provisioned_at = datetime.now(UTC)


@dataclass 
class ProvisioningPlanResult:
    """Result of provisioning a complete deployment plan."""
    plan: Plan
    state: ProvisioningState
    deployment_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    resource_results: list[ProvisioningResult] = field(default_factory=list)
    
    def __post_init__(self):
        if self.deployment_id is None:
            self.deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"
        if self.started_at is None:
            self.started_at = datetime.now(UTC)


class ProvisioningEngine(ABC):
    """Abstract base class for provisioning engines."""

    @abstractmethod
    def provision_resource(self, resource: Resource) -> ProvisioningResult:
        """Provision a single resource."""
        raise NotImplementedError("Subclasses must implement provision_resource")

    @abstractmethod
    def provision_plan(self, plan: Plan) -> ProvisioningPlanResult:
        """Provision a complete deployment plan."""
        raise NotImplementedError("Subclasses must implement provision_plan")

    @abstractmethod
    def get_provisioning_status(self, deployment_id: str) -> Optional[ProvisioningPlanResult]:
        """Get the current status of a deployment."""
        raise NotImplementedError("Subclasses must implement get_provisioning_status")


class DefaultProvisioningEngine(ProvisioningEngine):
    """Default implementation of provisioning engine with mock behavior."""

    def __init__(self):
        """Initialize the default provisioning engine."""
        self._deployments: dict[str, ProvisioningPlanResult] = {}

    def provision_resource(self, resource: Resource) -> ProvisioningResult:
        """Provision a single resource with mock implementation."""
        # Simulate provisioning logic
        if resource.resource_type == "nonexistent.type":
            # Simulate failure for invalid resource types
            error = ProvisioningError(
                resource_type=resource.resource_type,
                provider=resource.provider,
                error_type="INVALID_INSTANCE_TYPE",
                error_message=f"Instance type {resource.resource_type} does not exist",
                retry_suggested=False
            )
            return ProvisioningResult(
                resource=resource,
                state=ProvisioningState.FAILED,
                error=error
            )

        # Simulate successful provisioning
        resource_id = self._generate_resource_id(resource)
        provider_data = {
            "provider": resource.provider,
            "service": resource.service,
            "region": resource.region
        }

        return ProvisioningResult(
            resource=resource,
            state=ProvisioningState.READY,
            resource_id=resource_id,
            provider_specific_data=provider_data
        )

    def provision_plan(self, plan: Plan) -> ProvisioningPlanResult:
        """Provision a complete deployment plan."""
        deployment_id = f"deploy-{uuid.uuid4().hex[:8]}"
        
        plan_result = ProvisioningPlanResult(
            plan=plan,
            state=ProvisioningState.PROVISIONING,
            deployment_id=deployment_id,
            started_at=datetime.now(UTC)
        )

        # Store deployment for status tracking
        self._deployments[deployment_id] = plan_result

        # Provision each resource
        resource_results = []
        all_successful = True

        for resource in plan.resources:
            result = self.provision_resource(resource)
            resource_results.append(result)
            
            if result.state == ProvisioningState.FAILED:
                all_successful = False

        plan_result.resource_results = resource_results
        plan_result.state = ProvisioningState.READY if all_successful else ProvisioningState.FAILED
        plan_result.completed_at = datetime.now(UTC)

        return plan_result

    def get_provisioning_status(self, deployment_id: str) -> Optional[ProvisioningPlanResult]:
        """Get the current status of a deployment."""
        return self._deployments.get(deployment_id)

    def _generate_resource_id(self, resource: Resource) -> str:
        """Generate a resource ID based on the resource type."""
        if resource.service == "ec2":
            return f"i-{uuid.uuid4().hex[:16]}"
        elif resource.service == "s3":
            return f"{resource.provider}-{uuid.uuid4().hex[:8]}-bucket"
        else:
            return f"{resource.service}-{uuid.uuid4().hex[:8]}"