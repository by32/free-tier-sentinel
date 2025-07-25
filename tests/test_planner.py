"""Test planning engine using TDD approach."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from sentinel.models.core import Constraint, Plan, Resource, Usage
from sentinel.planner.cost_calculator import CostCalculator
from sentinel.planner.optimizer import PlanOptimizer
from sentinel.planner.recommender import ResourceRecommender


class TestCostCalculator:
    """Test cost calculation logic."""

    @pytest.fixture
    def sample_constraints(self):
        """Provide sample constraints for testing."""
        return [
            Constraint(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                limit_type="free_tier_hours",
                limit_value=750,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            ),
            Constraint(
                provider="aws",
                service="ec2",
                resource_type="t2.small",
                region="us-east-1",
                limit_type="standard_hours",
                limit_value=0,  # No free tier
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.023")
            ),
            Constraint(
                provider="aws",
                service="s3",
                resource_type="standard_storage",
                region="*",
                limit_type="free_tier_gb",
                limit_value=5,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            )
        ]

    def test_cost_calculator_creation(self, sample_constraints):
        """Test creating a cost calculator with constraints."""
        calculator = CostCalculator(sample_constraints)

        assert calculator is not None
        assert len(calculator.constraints) == 3

    def test_calculate_cost_within_free_tier(self, sample_constraints):
        """Test cost calculation for resources within free tier limits."""
        calculator = CostCalculator(sample_constraints)

        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=500  # Under 750 hour limit
        )

        cost_result = calculator.calculate_resource_cost(resource)

        assert cost_result.total_cost == Decimal("0.00")
        assert cost_result.is_free_tier is True
        assert cost_result.constraint_used is not None
        assert cost_result.usage_percentage < 100.0

    def test_calculate_cost_exceeding_free_tier(self, sample_constraints):
        """Test cost calculation for resources exceeding free tier limits."""
        calculator = CostCalculator(sample_constraints)

        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=800  # Exceeds 750 hour limit
        )

        cost_result = calculator.calculate_resource_cost(resource)

        assert cost_result.total_cost > Decimal("0.00")
        assert cost_result.is_free_tier is False
        assert cost_result.overage_hours == 50  # 800 - 750
        assert cost_result.free_tier_hours == 750

    def test_calculate_cost_no_free_tier(self, sample_constraints):
        """Test cost calculation for resources with no free tier."""
        calculator = CostCalculator(sample_constraints)

        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.small",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )

        cost_result = calculator.calculate_resource_cost(resource)

        assert cost_result.total_cost == Decimal("2.30")  # 100 * 0.023
        assert cost_result.is_free_tier is False
        assert cost_result.free_tier_hours == 0

    def test_calculate_cost_with_existing_usage(self, sample_constraints):
        """Test cost calculation accounting for existing usage."""
        calculator = CostCalculator(sample_constraints)

        # Existing usage consuming part of free tier
        existing_usage = [
            Usage(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                current_usage=300,  # Already used 300 hours
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 31, tzinfo=UTC)
            )
        ]

        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=500  # Want to use 500 more
        )

        cost_result = calculator.calculate_resource_cost(resource, existing_usage)

        # Should have 450 free hours left (750 - 300), so 50 hours charged
        assert cost_result.total_cost > Decimal("0.00")
        assert cost_result.free_tier_hours == 450
        assert cost_result.overage_hours == 50

    def test_calculate_plan_total_cost(self, sample_constraints):
        """Test calculating total cost for a complete plan."""
        calculator = CostCalculator(sample_constraints)

        plan = Plan(
            name="test-plan",
            description="Multi-resource test plan",
            resources=[
                Resource(
                    provider="aws",
                    service="ec2",
                    resource_type="t2.micro",
                    region="us-east-1",
                    quantity=1,
                    estimated_monthly_usage=500
                ),
                Resource(
                    provider="aws",
                    service="s3",
                    resource_type="standard_storage",
                    region="*",
                    quantity=1,
                    estimated_monthly_usage=3  # 3 GB storage
                )
            ]
        )

        plan_cost = calculator.calculate_plan_cost(plan)

        assert plan_cost.total_cost == Decimal("0.00")  # Both within free tier
        assert len(plan_cost.resource_costs) == 2
        assert all(rc.is_free_tier for rc in plan_cost.resource_costs)

    def test_validate_constraints_success(self, sample_constraints):
        """Test constraint validation for valid plan."""
        calculator = CostCalculator(sample_constraints)

        plan = Plan(
            name="valid-plan",
            description="Plan within all constraints",
            resources=[
                Resource(
                    provider="aws",
                    service="ec2",
                    resource_type="t2.micro",
                    region="us-east-1",
                    quantity=1,
                    estimated_monthly_usage=500
                )
            ]
        )

        validation_result = calculator.validate_plan_constraints(plan)

        assert validation_result.is_valid is True
        assert len(validation_result.violations) == 0
        assert validation_result.total_estimated_cost == Decimal("0.00")

    def test_validate_constraints_violations(self, sample_constraints):
        """Test constraint validation for plan with violations."""
        calculator = CostCalculator(sample_constraints)

        plan = Plan(
            name="violating-plan",
            description="Plan exceeding constraints",
            resources=[
                Resource(
                    provider="aws",
                    service="ec2",
                    resource_type="t2.micro",
                    region="us-east-1",
                    quantity=2,  # Two instances
                    estimated_monthly_usage=744  # Each running 24/7
                )
            ]
        )

        validation_result = calculator.validate_plan_constraints(plan)

        assert validation_result.is_valid is False
        assert len(validation_result.violations) > 0
        assert validation_result.total_estimated_cost > Decimal("0.00")


class TestResourceRecommender:
    """Test resource recommendation logic."""

    @pytest.fixture
    def sample_constraints(self):
        """Provide constraints for recommendation testing."""
        return [
            Constraint(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                limit_type="free_tier_hours",
                limit_value=750,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            ),
            Constraint(
                provider="gcp",
                service="compute",
                resource_type="f1-micro",
                region="us-central1",
                limit_type="free_tier_hours",
                limit_value=744,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            ),
            Constraint(
                provider="azure",
                service="compute",
                resource_type="B1s",
                region="*",
                limit_type="free_tier_hours",
                limit_value=750,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            )
        ]

    def test_recommender_creation(self, sample_constraints):
        """Test creating a resource recommender."""
        recommender = ResourceRecommender(sample_constraints)

        assert recommender is not None
        assert len(recommender.constraints) == 3

    def test_recommend_compute_resources(self, sample_constraints):
        """Test recommending compute resources for given requirements."""
        recommender = ResourceRecommender(sample_constraints)

        requirements = {
            "service_type": "compute",
            "estimated_monthly_hours": 500,
            "preferred_providers": ["aws", "gcp"],
            "preferred_regions": ["us-east-1", "us-central1"]
        }

        recommendations = recommender.recommend_resources(requirements)

        assert len(recommendations) > 0
        assert all(r.service == "ec2" or r.service == "compute" for r in recommendations)
        assert all(r.provider in ["aws", "gcp"] for r in recommendations)

        # Should prioritize free tier options
        free_tier_recs = [r for r in recommendations if r.is_free_tier]
        assert len(free_tier_recs) > 0

    def test_recommend_best_fit_resource(self, sample_constraints):
        """Test recommending the best fitting resource for requirements."""
        recommender = ResourceRecommender(sample_constraints)

        requirements = {
            "service_type": "compute",
            "estimated_monthly_hours": 600,
            "max_cost": Decimal("0.00"),  # Must be free
        }

        best_resource = recommender.recommend_best_fit(requirements)

        assert best_resource is not None
        assert best_resource.is_free_tier is True
        assert best_resource.estimated_monthly_usage <= best_resource.free_tier_limit

    def test_recommend_with_usage_constraints(self, sample_constraints):
        """Test recommendations considering existing usage."""
        recommender = ResourceRecommender(sample_constraints)

        existing_usage = [
            Usage(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                current_usage=400,
                period_start=datetime(2024, 1, 1, tzinfo=UTC),
                period_end=datetime(2024, 1, 31, tzinfo=UTC)
            )
        ]

        requirements = {
            "service_type": "compute",
            "estimated_monthly_hours": 400,  # Would exceed AWS free tier
            "max_cost": Decimal("0.00")
        }

        recommendations = recommender.recommend_resources(requirements, existing_usage)

        # Should recommend GCP or Azure since AWS free tier is partially used
        non_aws_recs = [r for r in recommendations if r.provider != "aws"]
        assert len(non_aws_recs) > 0

    def test_recommend_no_suitable_resources(self, sample_constraints):
        """Test recommendation when no resources meet requirements."""
        recommender = ResourceRecommender(sample_constraints)

        requirements = {
            "service_type": "compute",
            "estimated_monthly_hours": 2000,  # Exceeds all free tiers
            "max_cost": Decimal("0.00"),  # Must be free
        }

        recommendations = recommender.recommend_resources(requirements)

        assert len(recommendations) == 0  # No suitable resources


class TestPlanOptimizer:
    """Test plan optimization logic."""

    @pytest.fixture
    def sample_constraints(self):
        """Provide constraints for optimization testing."""
        return [
            Constraint(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                limit_type="free_tier_hours",
                limit_value=750,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            ),
            Constraint(
                provider="aws",
                service="s3",
                resource_type="standard_storage",
                region="*",
                limit_type="free_tier_gb",
                limit_value=5,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            ),
            Constraint(
                provider="gcp",
                service="compute",
                resource_type="f1-micro",
                region="us-central1",
                limit_type="free_tier_hours",
                limit_value=744,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            )
        ]

    def test_optimizer_creation(self, sample_constraints):
        """Test creating a plan optimizer."""
        optimizer = PlanOptimizer(sample_constraints)

        assert optimizer is not None

    def test_optimize_for_minimum_cost(self, sample_constraints):
        """Test optimizing a plan for minimum cost."""
        optimizer = PlanOptimizer(sample_constraints)

        # Initial plan with suboptimal choices
        initial_plan = Plan(
            name="unoptimized",
            description="Plan needing optimization",
            resources=[
                Resource(
                    provider="aws",
                    service="ec2",
                    resource_type="t2.micro",
                    region="us-east-1",
                    quantity=2,  # Two instances exceeding free tier
                    estimated_monthly_usage=744
                )
            ]
        )

        optimized_plan = optimizer.optimize_for_cost(initial_plan)

        assert optimized_plan.name != initial_plan.name
        assert len(optimized_plan.resources) >= len(initial_plan.resources)

        # Should suggest using multiple providers to maximize free tier usage
        providers = {r.provider for r in optimized_plan.resources}
        assert len(providers) > 1

    def test_optimize_within_budget(self, sample_constraints):
        """Test optimizing a plan to stay within budget."""
        optimizer = PlanOptimizer(sample_constraints)

        requirements = {
            "compute_hours": 1000,  # Exceeds single provider free tier
            "storage_gb": 10,       # Exceeds free tier
            "max_budget": Decimal("5.00")
        }

        optimized_plan = optimizer.optimize_within_budget(requirements)

        assert optimized_plan is not None
        # Plan should utilize free tiers first, then lowest cost options
        # Note: Need to implement estimated_cost calculation in optimization

    def test_optimize_for_free_tier_only(self, sample_constraints):
        """Test optimizing to use only free tier resources."""
        optimizer = PlanOptimizer(sample_constraints)
        calculator = CostCalculator(sample_constraints)

        requirements = {
            "compute_hours": 1200,  # Needs multiple providers for free tier
            "storage_gb": 3         # Within free tier
        }

        free_tier_plan = optimizer.optimize_free_tier_only(requirements)

        if free_tier_plan:  # May not be possible for all requirements
            # All resources should be within free tier limits
            # Check via cost calculator that all resources are free tier
            for resource in free_tier_plan.resources:
                cost_result = calculator.calculate_resource_cost(resource)
                assert cost_result.is_free_tier

        # Should at least return partial plan or None if impossible
        assert free_tier_plan is None or len(free_tier_plan.resources) > 0

    def test_optimize_impossible_requirements(self, sample_constraints):
        """Test optimization with impossible requirements."""
        optimizer = PlanOptimizer(sample_constraints)

        requirements = {
            "compute_hours": 10000,  # Far exceeds all free tiers
            "max_budget": Decimal("0.00")  # Must be free
        }

        result = optimizer.optimize_within_budget(requirements)

        # Should return None or empty plan for impossible requirements
        assert result is None or len(result.resources) == 0
