"""Resource recommendation engine for free-tier optimization."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sentinel.constraints.query import ConstraintQuery
from sentinel.models.core import Constraint, Usage


@dataclass
class ResourceRecommendation:
    """A recommended resource configuration."""
    provider: str
    service: str
    resource_type: str
    region: str
    estimated_monthly_usage: int
    is_free_tier: bool
    free_tier_limit: int
    estimated_cost: Decimal
    confidence_score: float  # 0.0 to 1.0


class ResourceRecommender:
    """Recommends optimal resource configurations."""

    def __init__(self, constraints: list[Constraint]):
        """Initialize recommender with constraint list."""
        self.constraints = constraints
        self.query = ConstraintQuery(constraints)

    def recommend_resources(
        self,
        requirements: dict[str, Any],
        existing_usage: list[Usage] | None = None
    ) -> list[ResourceRecommendation]:
        """Recommend resources based on requirements."""
        recommendations = []

        service_type = requirements.get("service_type", "compute")
        estimated_hours = requirements.get("estimated_monthly_hours", 0)
        preferred_providers = requirements.get("preferred_providers", ["aws", "gcp", "azure"])
        preferred_regions = requirements.get("preferred_regions", [])
        max_cost = requirements.get("max_cost")

        # Map service types to actual service names
        service_mapping = {
            "compute": ["ec2", "compute", "compute"],  # aws, gcp, azure
            "storage": ["s3", "storage", "storage"],
            "functions": ["lambda", "functions", "functions"]
        }

        # Get relevant constraints
        relevant_constraints = []
        for provider in preferred_providers:
            if service_type in service_mapping:
                service_names = service_mapping[service_type]
                provider_index = ["aws", "gcp", "azure"].index(provider) if provider in ["aws", "gcp", "azure"] else 0
                service_name = service_names[min(provider_index, len(service_names) - 1)]

                provider_constraints = (
                    self.query
                    .by_provider(provider)
                    .by_service(service_name)
                    .to_list()
                )
                relevant_constraints.extend(provider_constraints)

        # Filter by region if specified
        if preferred_regions:
            filtered_constraints = []
            for constraint in relevant_constraints:
                if constraint.region == "*" or constraint.region in preferred_regions:
                    filtered_constraints.append(constraint)
            relevant_constraints = filtered_constraints

        # Calculate available capacity considering existing usage
        for constraint in relevant_constraints:
            available_capacity = constraint.limit_value

            if existing_usage:
                for usage in existing_usage:
                    if (usage.provider == constraint.provider and
                        usage.service == constraint.service and
                        usage.resource_type == constraint.resource_type and
                        (constraint.region == "*" or usage.region == constraint.region)):
                        available_capacity -= usage.current_usage

            available_capacity = max(0, available_capacity)

            # Check if this constraint can meet requirements
            if estimated_hours <= available_capacity:
                estimated_cost = Decimal("0.00") if constraint.is_free_tier() else Decimal(str(estimated_hours)) * constraint.cost_per_unit

                # Skip if exceeds max cost
                if max_cost is not None and estimated_cost > max_cost:
                    continue

                # Calculate confidence score based on fit and preference
                capacity_fit = 1.0 - (estimated_hours / constraint.limit_value) if constraint.limit_value > 0 else 0.0
                provider_preference = 1.0 if constraint.provider in preferred_providers else 0.5
                cost_preference = 1.0 if constraint.is_free_tier() else 0.7

                confidence_score = (capacity_fit + provider_preference + cost_preference) / 3.0

                recommendation = ResourceRecommendation(
                    provider=constraint.provider,
                    service=constraint.service,
                    resource_type=constraint.resource_type,
                    region=constraint.region,
                    estimated_monthly_usage=estimated_hours,
                    is_free_tier=constraint.is_free_tier(),
                    free_tier_limit=constraint.limit_value,
                    estimated_cost=estimated_cost,
                    confidence_score=confidence_score
                )
                recommendations.append(recommendation)

        # Sort by confidence score (highest first)
        recommendations.sort(key=lambda r: r.confidence_score, reverse=True)

        return recommendations

    def recommend_best_fit(
        self,
        requirements: dict[str, Any],
        existing_usage: list[Usage] | None = None
    ) -> ResourceRecommendation | None:
        """Recommend the single best fitting resource."""
        recommendations = self.recommend_resources(requirements, existing_usage)

        if recommendations:
            return recommendations[0]

        return None
