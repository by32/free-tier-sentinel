"""Core data models for Free Tier Sentinel."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator


class CloudProvider(BaseModel):
    """Represents a cloud provider with available regions."""

    name: str = Field(..., description="Provider identifier (e.g., 'aws', 'gcp')")
    display_name: str = Field(..., description="Human-readable provider name")
    regions: list[str] = Field(..., description="Available regions for this provider")

    @field_validator("name")
    @classmethod
    def name_must_be_lowercase(cls, v: str) -> str:
        """Ensure provider name is lowercase."""
        return v.lower()

    @field_validator("regions")
    @classmethod
    def must_have_regions(cls, v: list[str]) -> list[str]:
        """Ensure at least one region is provided."""
        if not v:
            raise ValueError("Provider must have at least one region")
        return v


class Service(BaseModel):
    """Represents a cloud service within a provider."""

    name: str = Field(..., description="Service identifier (e.g., 'ec2', 'compute')")
    display_name: str = Field(..., description="Human-readable service name")
    provider: str = Field(..., description="Cloud provider name")
    category: str = Field(
        ..., description="Service category (e.g., 'compute', 'storage')"
    )


class ResourceType(BaseModel):
    """Represents a specific resource type within a service."""

    name: str = Field(..., description="Resource type name (e.g., 't2.micro')")
    service: str = Field(..., description="Parent service name")
    provider: str = Field(..., description="Cloud provider name")
    specs: dict[str, Any] = Field(
        default_factory=dict, description="Resource specifications"
    )


class Constraint(BaseModel):
    """Represents a quota or free-tier constraint."""

    provider: str = Field(..., description="Cloud provider name")
    service: str = Field(..., description="Service name")
    resource_type: str = Field(..., description="Resource type name")
    region: str = Field(..., description="Region where constraint applies")
    limit_type: str = Field(..., description="Type of limit (e.g., 'free_tier_hours')")
    limit_value: int = Field(..., description="Numerical limit value")
    period: str = Field(..., description="Time period for the limit (e.g., 'monthly')")
    currency: str = Field(..., description="Currency for cost calculations")
    cost_per_unit: Decimal = Field(..., description="Cost per unit beyond free tier")

    @field_validator("limit_value")
    @classmethod
    def limit_must_be_positive(cls, v: int) -> int:
        """Ensure limit value is positive."""
        if v < 0:
            raise ValueError("limit_value must be positive")
        return v

    def is_free_tier(self) -> bool:
        """Check if this constraint represents free tier usage."""
        return self.cost_per_unit == Decimal("0.00")


class Usage(BaseModel):
    """Tracks current usage of a resource."""

    provider: str = Field(..., description="Cloud provider name")
    service: str = Field(..., description="Service name")
    resource_type: str = Field(..., description="Resource type name")
    region: str = Field(..., description="Region of usage")
    current_usage: int = Field(..., description="Current usage amount")
    period_start: datetime = Field(..., description="Start of tracking period")
    period_end: datetime = Field(..., description="End of tracking period")

    @field_validator("period_end")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        """Ensure period_end is after period_start."""
        if (
            hasattr(info, "data")
            and "period_start" in info.data
            and v <= info.data["period_start"]
        ):
            raise ValueError("period_end must be after period_start")
        return v

    def percentage_of_limit(self, constraint: Constraint) -> float:
        """Calculate usage as percentage of constraint limit."""
        if constraint.limit_value == 0:
            return 100.0
        return (self.current_usage / constraint.limit_value) * 100.0


class Resource(BaseModel):
    """Represents a planned resource in a deployment."""

    provider: str = Field(..., description="Cloud provider name")
    service: str = Field(..., description="Service name")
    resource_type: str = Field(..., description="Resource type name")
    region: str = Field(..., description="Deployment region")
    quantity: int = Field(default=1, description="Number of resources")
    estimated_monthly_usage: int = Field(
        ..., description="Estimated monthly usage hours"
    )

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        """Ensure quantity is positive."""
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v


class Plan(BaseModel):
    """Represents a complete deployment plan."""

    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")
    resources: list[Resource] = Field(
        default_factory=list, description="Planned resources"
    )
    total_estimated_cost: Decimal = Field(
        default=Decimal("0.00"), description="Total estimated cost"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="Plan creation time"
    )

    def calculate_total_cost(self) -> Decimal:
        """Calculate total estimated cost for the plan."""
        # Placeholder implementation - will be enhanced with constraint checking
        return self.total_estimated_cost

    def validate_constraints(self, constraints: list[Constraint]) -> bool:
        """Validate plan against free tier constraints."""
        # Placeholder implementation - will be enhanced with actual validation logic
        return True
