#!/usr/bin/env python3
"""
Demo script showing capacity-aware planning integration.

This demonstrates how the capacity detection system integrates with the
planning components to provide intelligent, availability-aware resource
recommendations and optimizations.
"""

from decimal import Decimal
from sentinel.models.core import Constraint, Resource
from sentinel.capacity.aggregator import CapacityAggregator
from sentinel.capacity.cache import CapacityCache
from sentinel.capacity.aws_checker import AWSCapacityChecker
from sentinel.capacity.gcp_checker import GCPCapacityChecker
from sentinel.capacity.azure_checker import AzureCapacityChecker
from sentinel.planner.cost_calculator import CapacityAwareCostCalculator
from sentinel.planner.recommender import CapacityAwareResourceRecommender
from sentinel.planner.optimizer import CapacityAwarePlanOptimizer


def setup_demo_constraints():
    """Create sample constraints for demonstration."""
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
            cost_per_unit=Decimal("0.00"),
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
            cost_per_unit=Decimal("0.00"),
        ),
        Constraint(
            provider="azure",
            service="compute",
            resource_type="Standard_B1s",
            region="eastus",
            limit_type="free_tier_hours",
            limit_value=750,
            period="monthly",
            currency="USD",
            cost_per_unit=Decimal("0.00"),
        ),
    ]


def setup_capacity_system():
    """Initialize the capacity detection system."""
    # Create capacity checkers for each provider
    checkers = {
        "aws": AWSCapacityChecker(),
        "gcp": GCPCapacityChecker(),
        "azure": AzureCapacityChecker(),
    }

    # Create cache with 5-minute TTL
    cache = CapacityCache(ttl_seconds=300)

    # Create aggregator
    aggregator = CapacityAggregator(checkers, cache)

    return aggregator


def demo_capacity_aware_cost_calculation():
    """Demonstrate capacity-aware cost calculation."""
    print("🔍 Capacity-Aware Cost Calculation Demo")
    print("=" * 50)

    constraints = setup_demo_constraints()
    aggregator = setup_capacity_system()
    calculator = CapacityAwareCostCalculator(constraints, aggregator)

    # Test resource that should have capacity
    aws_resource = Resource(
        provider="aws",
        service="ec2",
        resource_type="t2.micro",
        region="us-east-1",
        quantity=1,
        estimated_monthly_usage=500,
    )

    result = calculator.calculate_resource_cost(aws_resource)

    print(f"Resource: {aws_resource.provider} {aws_resource.resource_type}")
    print(f"Cost: ${result.total_cost}")
    print(f"Free Tier: {result.is_free_tier}")
    print(f"Capacity Available: {result.capacity_available}")
    print(f"Capacity Level: {result.capacity_level:.1%}")
    print()


def demo_capacity_aware_recommendations():
    """Demonstrate capacity-aware resource recommendations."""
    print("💡 Capacity-Aware Recommendations Demo")
    print("=" * 50)

    constraints = setup_demo_constraints()
    aggregator = setup_capacity_system()
    recommender = CapacityAwareResourceRecommender(constraints, aggregator)

    requirements = {
        "service_type": "compute",
        "estimated_monthly_hours": 500,
        "preferred_providers": ["aws", "gcp", "azure"],
    }

    recommendations = recommender.recommend_resources(requirements)

    print(f"Requirements: {requirements['estimated_monthly_hours']} compute hours")
    print(f"Found {len(recommendations)} available recommendations:")
    print()

    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec.provider} {rec.resource_type} in {rec.region}")
        print(f"   Confidence: {rec.confidence_score:.2f}")
        print(f"   Capacity: {rec.capacity_level:.1%} available")
        print(f"   Cost: ${rec.estimated_cost}")
        print()


def demo_capacity_aware_optimization():
    """Demonstrate capacity-aware plan optimization."""
    print("⚡ Capacity-Aware Plan Optimization Demo")
    print("=" * 50)

    constraints = setup_demo_constraints()
    aggregator = setup_capacity_system()
    optimizer = CapacityAwarePlanOptimizer(constraints, aggregator)

    requirements = {
        "compute_hours": 1200,  # Requires multiple providers
        "preferred_providers": ["aws", "gcp", "azure"],
    }

    plan = optimizer.optimize_with_capacity_constraints(requirements)

    print(f"Requirements: {requirements['compute_hours']} compute hours")
    print(f"Optimized plan '{plan.name}':")
    print()

    total_hours = 0
    for resource in plan.resources:
        print(f"• {resource.provider} {resource.resource_type}")
        print(f"  Region: {resource.region}")
        print(f"  Hours: {resource.estimated_monthly_usage}")
        total_hours += resource.estimated_monthly_usage
        print()

    print(f"Total allocated hours: {total_hours}")
    print(f"Providers used: {len(set(r.provider for r in plan.resources))}")


def main():
    """Run the capacity integration demo."""
    print("🚀 Free-Tier Sentinel: Capacity Integration Demo")
    print("=" * 60)
    print()
    print("This demo shows how capacity detection integrates with planning")
    print("to provide intelligent, availability-aware resource management.")
    print()

    try:
        demo_capacity_aware_cost_calculation()
        demo_capacity_aware_recommendations()
        demo_capacity_aware_optimization()

        print("✅ Demo completed successfully!")
        print()
        print("Key Benefits:")
        print("• Avoids resources without available capacity")
        print("• Prioritizes high-capacity options for reliability")
        print("• Integrates seamlessly with cost optimization")
        print("• Provides real-time capacity information")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
