"""Cost calculation engine for free-tier planning."""

from dataclasses import dataclass
from decimal import Decimal

from sentinel.constraints.query import ConstraintQuery
from sentinel.models.core import Constraint, Plan, Resource, Usage


@dataclass
class ResourceCostResult:
    """Result of resource cost calculation."""
    resource: Resource
    total_cost: Decimal
    is_free_tier: bool
    constraint_used: Constraint | None = None
    usage_percentage: float = 0.0
    free_tier_hours: int = 0
    overage_hours: int = 0


@dataclass
class PlanCostResult:
    """Result of plan cost calculation."""
    plan: Plan
    total_cost: Decimal
    resource_costs: list[ResourceCostResult]


@dataclass
class ValidationResult:
    """Result of plan constraint validation."""
    is_valid: bool
    violations: list[str]
    total_estimated_cost: Decimal


class CostCalculator:
    """Calculates costs for resources against free-tier constraints."""

    def __init__(self, constraints: list[Constraint]):
        """Initialize calculator with constraint list."""
        self.constraints = constraints
        self.query = ConstraintQuery(constraints)

    def calculate_resource_cost(
        self,
        resource: Resource,
        existing_usage: list[Usage] | None = None
    ) -> ResourceCostResult:
        """Calculate cost for a single resource."""
        # Find matching constraint
        matching_constraints = (
            self.query
            .by_provider(resource.provider)
            .by_service(resource.service)
            .by_resource_type(resource.resource_type)
        )

        # Handle region matching (including wildcard)
        region_constraints = []
        for constraint in matching_constraints:
            if constraint.region == "*" or constraint.region == resource.region:
                region_constraints.append(constraint)

        if not region_constraints:
            # No constraint found - assume standard pricing
            return ResourceCostResult(
                resource=resource,
                total_cost=Decimal("0.00"),  # Placeholder - would need pricing data
                is_free_tier=False
            )

        # Use the first matching constraint (could be enhanced with priority logic)
        constraint = region_constraints[0]

        # Calculate existing usage for this constraint
        used_quota = 0
        if existing_usage:
            for usage in existing_usage:
                if (usage.provider == resource.provider and
                    usage.service == resource.service and
                    usage.resource_type == resource.resource_type and
                    (constraint.region == "*" or usage.region == resource.region)):
                    used_quota += usage.current_usage

        # Calculate available free tier quota
        available_quota = max(0, constraint.limit_value - used_quota)

        # Calculate free tier and overage usage
        total_usage = resource.quantity * resource.estimated_monthly_usage
        free_tier_usage = min(total_usage, available_quota)
        overage_usage = max(0, total_usage - available_quota)

        # Calculate cost
        if overage_usage == 0:
            total_cost = Decimal("0.00")
            is_free_tier = True
        else:
            # For free tier constraints that exceed limits, we need pricing for overage
            # This is a simplification - in reality we'd need separate pricing data
            if constraint.is_free_tier():
                # Use a default rate for overage on free tier resources
                # In practice, this would come from a separate pricing database
                default_overage_rate = Decimal("0.0116")  # t2.micro standard rate
                total_cost = Decimal(str(overage_usage)) * default_overage_rate
            else:
                total_cost = Decimal(str(overage_usage)) * constraint.cost_per_unit
            is_free_tier = False

        # Calculate usage percentage
        usage_percentage = (total_usage / constraint.limit_value * 100.0) if constraint.limit_value > 0 else 100.0

        return ResourceCostResult(
            resource=resource,
            total_cost=total_cost,
            is_free_tier=is_free_tier,
            constraint_used=constraint,
            usage_percentage=usage_percentage,
            free_tier_hours=int(free_tier_usage),
            overage_hours=int(overage_usage)
        )

    def calculate_plan_cost(
        self,
        plan: Plan,
        existing_usage: list[Usage] | None = None
    ) -> PlanCostResult:
        """Calculate total cost for a complete plan."""
        resource_costs = []
        total_cost = Decimal("0.00")

        for resource in plan.resources:
            cost_result = self.calculate_resource_cost(resource, existing_usage)
            resource_costs.append(cost_result)
            total_cost += cost_result.total_cost

        return PlanCostResult(
            plan=plan,
            total_cost=total_cost,
            resource_costs=resource_costs
        )

    def validate_plan_constraints(self, plan: Plan) -> ValidationResult:
        """Validate plan against constraints and return violations."""
        violations = []
        total_cost = Decimal("0.00")

        # Group resources by constraint to check aggregate limits
        constraint_usage = {}

        for resource in plan.resources:
            cost_result = self.calculate_resource_cost(resource)
            total_cost += cost_result.total_cost

            if cost_result.constraint_used:
                constraint_key = (
                    cost_result.constraint_used.provider,
                    cost_result.constraint_used.service,
                    cost_result.constraint_used.resource_type,
                    cost_result.constraint_used.region
                )

                if constraint_key not in constraint_usage:
                    constraint_usage[constraint_key] = {
                        'constraint': cost_result.constraint_used,
                        'total_usage': 0,
                        'resources': []
                    }

                usage = resource.quantity * resource.estimated_monthly_usage
                constraint_usage[constraint_key]['total_usage'] += usage
                constraint_usage[constraint_key]['resources'].append(resource)

        # Check for constraint violations
        for _constraint_key, usage_info in constraint_usage.items():
            constraint = usage_info['constraint']
            total_usage = usage_info['total_usage']

            if total_usage > constraint.limit_value:
                overage = total_usage - constraint.limit_value
                violation = (
                    f"Constraint violation: {constraint.provider} {constraint.service} "
                    f"{constraint.resource_type} exceeds limit by {overage} "
                    f"{constraint.limit_type.replace('_', ' ')}"
                )
                violations.append(violation)

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            total_estimated_cost=total_cost
        )
