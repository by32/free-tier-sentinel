"""Test core data models using TDD approach."""

from datetime import datetime
from decimal import Decimal

import pytest

from sentinel.models.core import (
    CloudProvider,
    Constraint,
    Plan,
    Resource,
    ResourceType,
    Service,
    Usage,
)


class TestCloudProvider:
    """Test CloudProvider model."""

    def test_provider_creation_with_valid_data(self):
        """Test creating a cloud provider with valid data."""
        provider = CloudProvider(
            name="aws",
            display_name="Amazon Web Services",
            regions=["us-east-1", "us-west-2"],
        )

        assert provider.name == "aws"
        assert provider.display_name == "Amazon Web Services"
        assert provider.regions == ["us-east-1", "us-west-2"]

    def test_provider_name_must_be_lowercase(self):
        """Test that provider name is automatically converted to lowercase."""
        provider = CloudProvider(
            name="AWS", display_name="Amazon Web Services", regions=["us-east-1"]
        )

        assert provider.name == "aws"

    def test_provider_requires_at_least_one_region(self):
        """Test that provider must have at least one region."""
        with pytest.raises(ValueError, match="at least one region"):
            CloudProvider(name="aws", display_name="Amazon Web Services", regions=[])


class TestService:
    """Test Service model."""

    def test_service_creation_with_valid_data(self):
        """Test creating a service with valid data."""
        service = Service(
            name="ec2",
            display_name="Elastic Compute Cloud",
            provider="aws",
            category="compute",
        )

        assert service.name == "ec2"
        assert service.display_name == "Elastic Compute Cloud"
        assert service.provider == "aws"
        assert service.category == "compute"


class TestResourceType:
    """Test ResourceType model."""

    def test_resource_type_creation(self):
        """Test creating a resource type with specifications."""
        resource_type = ResourceType(
            name="t2.micro",
            service="ec2",
            provider="aws",
            specs={"vcpus": 1, "memory_gb": 1, "storage_gb": 8},
        )

        assert resource_type.name == "t2.micro"
        assert resource_type.service == "ec2"
        assert resource_type.provider == "aws"
        assert resource_type.specs["vcpus"] == 1


class TestConstraint:
    """Test Constraint model."""

    def test_constraint_creation_with_free_tier_limit(self):
        """Test creating a constraint for free tier limits."""
        constraint = Constraint(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            limit_type="free_tier_hours",
            limit_value=750,
            period="monthly",
            currency="USD",
            cost_per_unit=Decimal("0.0116"),
        )

        assert constraint.provider == "aws"
        assert constraint.service == "ec2"
        assert constraint.resource_type == "t2.micro"
        assert constraint.limit_value == 750
        assert constraint.period == "monthly"
        assert isinstance(constraint.cost_per_unit, Decimal)

    def test_constraint_with_zero_cost_for_free_tier(self):
        """Test constraint with zero cost for free tier usage."""
        constraint = Constraint(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            limit_type="free_tier_hours",
            limit_value=750,
            period="monthly",
            currency="USD",
            cost_per_unit=Decimal("0.00"),  # Free within limit
        )

        assert constraint.cost_per_unit == Decimal("0.00")
        assert constraint.is_free_tier()

    def test_constraint_validation_negative_limit(self):
        """Test that negative limits are rejected."""
        with pytest.raises(ValueError, match="limit_value must be positive"):
            Constraint(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                limit_type="free_tier_hours",
                limit_value=-100,  # Invalid
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00"),
            )


class TestUsage:
    """Test Usage tracking model."""

    def test_usage_creation(self):
        """Test creating usage tracking for a resource."""
        usage = Usage(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            current_usage=100,
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
        )

        assert usage.provider == "aws"
        assert usage.current_usage == 100
        assert usage.period_start < usage.period_end

    def test_usage_percentage_calculation(self):
        """Test calculating usage percentage against constraint."""
        constraint = Constraint(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            limit_type="free_tier_hours",
            limit_value=750,
            period="monthly",
            currency="USD",
            cost_per_unit=Decimal("0.00"),
        )

        usage = Usage(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            current_usage=375,  # Half of limit
            period_start=datetime(2024, 1, 1),
            period_end=datetime(2024, 1, 31),
        )

        percentage = usage.percentage_of_limit(constraint)
        assert percentage == 50.0


class TestResource:
    """Test Resource model for planned resources."""

    def test_resource_creation(self):
        """Test creating a planned resource."""
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=744,  # 24/7 for 31 days
        )

        assert resource.provider == "aws"
        assert resource.quantity == 1
        assert resource.estimated_monthly_usage == 744


class TestPlan:
    """Test Plan model for deployment plans."""

    def test_empty_plan_creation(self):
        """Test creating an empty deployment plan."""
        plan = Plan(name="test-plan", description="A test deployment plan")

        assert plan.name == "test-plan"
        assert plan.description == "A test deployment plan"
        assert len(plan.resources) == 0
        assert plan.total_estimated_cost == Decimal("0.00")

    def test_plan_with_resources(self):
        """Test creating a plan with resources."""
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=744,
            )
        ]

        plan = Plan(
            name="simple-web-server",
            description="Single EC2 instance",
            resources=resources,
        )

        assert len(plan.resources) == 1
        assert plan.resources[0].resource_type == "t2.micro"

    def test_plan_cost_calculation(self):
        """Test that plan can calculate total estimated cost."""
        # This will fail initially - we need to implement cost calculation
        plan = Plan(name="test-plan", description="Cost calculation test")

        # This should work once we implement the cost calculation logic
        assert hasattr(plan, "calculate_total_cost")

    def test_plan_validates_against_constraints(self):
        """Test that plan can validate against free tier constraints."""
        plan = Plan(name="test-plan", description="Validation test")

        # This should work once we implement validation logic
        assert hasattr(plan, "validate_constraints")
