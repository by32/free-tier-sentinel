"""Plan optimization engine using linear programming approaches."""

from decimal import Decimal
from typing import Any

from sentinel.constraints.query import ConstraintQuery
from sentinel.models.core import Constraint, Plan, Resource
from sentinel.planner.cost_calculator import CostCalculator
from sentinel.planner.recommender import ResourceRecommender


class PlanOptimizer:
    """Optimizes deployment plans for cost and free-tier usage."""

    def __init__(self, constraints: list[Constraint]):
        """Initialize optimizer with constraint list."""
        self.constraints = constraints
        self.query = ConstraintQuery(constraints)
        self.calculator = CostCalculator(constraints)
        self.recommender = ResourceRecommender(constraints)

    def optimize_for_cost(self, plan: Plan) -> Plan:
        """Optimize plan to minimize cost while meeting requirements."""
        optimized_plan = Plan(
            name=f"{plan.name}-optimized",
            description=f"Cost-optimized version of {plan.description}",
            resources=[],
        )

        # Analyze original plan requirements
        total_compute_hours = 0
        total_storage_gb = 0

        for resource in plan.resources:
            if resource.service in ["ec2", "compute"]:
                total_compute_hours += (
                    resource.quantity * resource.estimated_monthly_usage
                )
            elif resource.service in ["s3", "storage"]:
                total_storage_gb += resource.quantity * resource.estimated_monthly_usage

        # Optimize compute resources
        if total_compute_hours > 0:
            compute_resources = self._optimize_compute_allocation(total_compute_hours)
            optimized_plan.resources.extend(compute_resources)

        # Optimize storage resources
        if total_storage_gb > 0:
            storage_resources = self._optimize_storage_allocation(total_storage_gb)
            optimized_plan.resources.extend(storage_resources)

        return optimized_plan

    def optimize_within_budget(self, requirements: dict[str, Any]) -> Plan | None:
        """Optimize plan to stay within specified budget."""
        max_budget = requirements.get("max_budget", Decimal("0.00"))
        compute_hours = requirements.get("compute_hours", 0)
        storage_gb = requirements.get("storage_gb", 0)

        # Start with free tier resources
        plan = Plan(
            name="budget-optimized",
            description=f"Plan optimized for budget ${max_budget}",
            resources=[],
        )

        remaining_budget = max_budget

        # Allocate compute resources within budget
        if compute_hours > 0:
            compute_resources, compute_cost = self._allocate_compute_within_budget(
                compute_hours, remaining_budget
            )
            plan.resources.extend(compute_resources)
            remaining_budget -= compute_cost

        # Allocate storage resources with remaining budget
        if storage_gb > 0 and remaining_budget > Decimal("0.00"):
            storage_resources, storage_cost = self._allocate_storage_within_budget(
                storage_gb, remaining_budget
            )
            plan.resources.extend(storage_resources)

        # Validate final plan cost
        cost_result = self.calculator.calculate_plan_cost(plan)
        if cost_result.total_cost <= max_budget:
            return plan

        return None

    def optimize_free_tier_only(self, requirements: dict[str, Any]) -> Plan | None:
        """Optimize plan to use only free tier resources."""
        compute_hours = requirements.get("compute_hours", 0)
        storage_gb = requirements.get("storage_gb", 0)

        plan = Plan(
            name="free-tier-only",
            description="Plan using only free tier resources",
            resources=[],
        )

        # Get all free tier constraints
        free_tier_constraints = self.query.free_tier_only().to_list()

        # Allocate compute resources
        if compute_hours > 0:
            remaining_hours = compute_hours
            for constraint in free_tier_constraints:
                if constraint.service in ["ec2", "compute"] and remaining_hours > 0:
                    allocation = min(remaining_hours, constraint.limit_value)
                    if allocation > 0:
                        resource = Resource(
                            provider=constraint.provider,
                            service=constraint.service,
                            resource_type=constraint.resource_type,
                            region=(
                                constraint.region
                                if constraint.region != "*"
                                else "us-east-1"
                            ),
                            quantity=1,
                            estimated_monthly_usage=allocation,
                        )
                        plan.resources.append(resource)
                        remaining_hours -= allocation

            # If we couldn't satisfy all compute requirements, return None
            if remaining_hours > 0:
                return None

        # Allocate storage resources
        if storage_gb > 0:
            remaining_storage = storage_gb
            for constraint in free_tier_constraints:
                if constraint.service in ["s3", "storage"] and remaining_storage > 0:
                    allocation = min(remaining_storage, constraint.limit_value)
                    if allocation > 0:
                        resource = Resource(
                            provider=constraint.provider,
                            service=constraint.service,
                            resource_type=constraint.resource_type,
                            region=(
                                constraint.region
                                if constraint.region != "*"
                                else "us-east-1"
                            ),
                            quantity=1,
                            estimated_monthly_usage=allocation,
                        )
                        plan.resources.append(resource)
                        remaining_storage -= allocation

            # If we couldn't satisfy all storage requirements, return partial plan
            # (storage is less critical than compute)

        return plan if plan.resources else None

    def _optimize_compute_allocation(self, total_hours: int) -> list[Resource]:
        """Optimize compute resource allocation across providers."""
        resources = []
        remaining_hours = total_hours

        # Get compute constraints sorted by cost (free tier first)
        compute_constraints = []
        for constraint in self.constraints:
            if constraint.service in ["ec2", "compute"]:
                compute_constraints.append(constraint)

        # Sort by cost (free tier first, then by cost per unit)
        compute_constraints.sort(key=lambda c: (not c.is_free_tier(), c.cost_per_unit))

        # Allocate hours to cheapest options first
        for constraint in compute_constraints:
            if remaining_hours <= 0:
                break

            allocation = min(remaining_hours, constraint.limit_value)
            if allocation > 0:
                resource = Resource(
                    provider=constraint.provider,
                    service=constraint.service,
                    resource_type=constraint.resource_type,
                    region=(
                        constraint.region if constraint.region != "*" else "us-east-1"
                    ),
                    quantity=1,
                    estimated_monthly_usage=allocation,
                )
                resources.append(resource)
                remaining_hours -= allocation

        return resources

    def _optimize_storage_allocation(self, total_gb: int) -> list[Resource]:
        """Optimize storage resource allocation across providers."""
        resources = []
        remaining_gb = total_gb

        # Get storage constraints sorted by cost
        storage_constraints = []
        for constraint in self.constraints:
            if constraint.service in ["s3", "storage"]:
                storage_constraints.append(constraint)

        storage_constraints.sort(key=lambda c: (not c.is_free_tier(), c.cost_per_unit))

        # Allocate GB to cheapest options first
        for constraint in storage_constraints:
            if remaining_gb <= 0:
                break

            allocation = min(remaining_gb, constraint.limit_value)
            if allocation > 0:
                resource = Resource(
                    provider=constraint.provider,
                    service=constraint.service,
                    resource_type=constraint.resource_type,
                    region=(
                        constraint.region if constraint.region != "*" else "us-east-1"
                    ),
                    quantity=1,
                    estimated_monthly_usage=allocation,
                )
                resources.append(resource)
                remaining_gb -= allocation

        return resources

    def _allocate_compute_within_budget(
        self, hours: int, budget: Decimal
    ) -> tuple[list[Resource], Decimal]:
        """Allocate compute resources within budget constraint."""
        resources = []
        total_cost = Decimal("0.00")
        remaining_hours = hours
        remaining_budget = budget

        # Get compute constraints sorted by value (free tier first)
        compute_constraints = []
        for constraint in self.constraints:
            if constraint.service in ["ec2", "compute"]:
                compute_constraints.append(constraint)

        compute_constraints.sort(key=lambda c: (not c.is_free_tier(), c.cost_per_unit))

        for constraint in compute_constraints:
            if remaining_hours <= 0 or remaining_budget <= Decimal("0.00"):
                break

            # Calculate how much we can afford with this resource
            if constraint.is_free_tier():
                allocation = min(remaining_hours, constraint.limit_value)
                cost = Decimal("0.00")
            else:
                max_affordable = (
                    int(remaining_budget / constraint.cost_per_unit)
                    if constraint.cost_per_unit > 0
                    else 0
                )
                allocation = min(remaining_hours, max_affordable)
                cost = Decimal(str(allocation)) * constraint.cost_per_unit

            if allocation > 0:
                resource = Resource(
                    provider=constraint.provider,
                    service=constraint.service,
                    resource_type=constraint.resource_type,
                    region=(
                        constraint.region if constraint.region != "*" else "us-east-1"
                    ),
                    quantity=1,
                    estimated_monthly_usage=allocation,
                )
                resources.append(resource)
                remaining_hours -= allocation
                remaining_budget -= cost
                total_cost += cost

        return resources, total_cost

    def _allocate_storage_within_budget(
        self, gb: int, budget: Decimal
    ) -> tuple[list[Resource], Decimal]:
        """Allocate storage resources within budget constraint."""
        resources = []
        total_cost = Decimal("0.00")
        remaining_gb = gb
        remaining_budget = budget

        # Get storage constraints sorted by value
        storage_constraints = []
        for constraint in self.constraints:
            if constraint.service in ["s3", "storage"]:
                storage_constraints.append(constraint)

        storage_constraints.sort(key=lambda c: (not c.is_free_tier(), c.cost_per_unit))

        for constraint in storage_constraints:
            if remaining_gb <= 0 or remaining_budget <= Decimal("0.00"):
                break

            # Calculate how much we can afford
            if constraint.is_free_tier():
                allocation = min(remaining_gb, constraint.limit_value)
                cost = Decimal("0.00")
            else:
                max_affordable = (
                    int(remaining_budget / constraint.cost_per_unit)
                    if constraint.cost_per_unit > 0
                    else 0
                )
                allocation = min(remaining_gb, max_affordable)
                cost = Decimal(str(allocation)) * constraint.cost_per_unit

            if allocation > 0:
                resource = Resource(
                    provider=constraint.provider,
                    service=constraint.service,
                    resource_type=constraint.resource_type,
                    region=(
                        constraint.region if constraint.region != "*" else "us-east-1"
                    ),
                    quantity=1,
                    estimated_monthly_usage=allocation,
                )
                resources.append(resource)
                remaining_gb -= allocation
                remaining_budget -= cost
                total_cost += cost

        return resources, total_cost


class CapacityAwarePlanOptimizer(PlanOptimizer):
    """Plan optimizer that considers capacity availability."""

    def __init__(self, constraints: list[Constraint], capacity_aggregator):
        """Initialize optimizer with constraints and capacity aggregator."""
        super().__init__(constraints)
        self.capacity_aggregator = capacity_aggregator

    def optimize_with_capacity_constraints(self, requirements: dict[str, Any]) -> Plan:
        """Optimize plan considering both cost and capacity constraints."""
        compute_hours = requirements.get("compute_hours", 0)
        storage_gb = requirements.get("storage_gb", 0)
        preferred_providers = requirements.get(
            "preferred_providers", ["aws", "gcp", "azure"]
        )

        plan = Plan(
            name="capacity-optimized",
            description="Plan optimized for both cost and capacity",
            resources=[],
        )

        # Get constraints and filter by available capacity
        available_constraints = self._filter_constraints_by_capacity(
            preferred_providers
        )

        # Allocate compute resources
        if compute_hours > 0:
            compute_resources = self._allocate_compute_with_capacity(
                compute_hours, available_constraints
            )
            plan.resources.extend(compute_resources)

        # Allocate storage resources
        if storage_gb > 0:
            storage_resources = self._allocate_storage_with_capacity(
                storage_gb, available_constraints
            )
            plan.resources.extend(storage_resources)

        return plan

    def _filter_constraints_by_capacity(
        self, preferred_providers: list[str]
    ) -> list[Constraint]:
        """Filter constraints to only include those with available capacity."""
        available_constraints = []

        for constraint in self.constraints:
            if constraint.provider not in preferred_providers:
                continue

            try:
                # Check capacity for this constraint
                capacity_result = self.capacity_aggregator.check_availability(
                    constraint.provider,
                    constraint.region if constraint.region != "*" else "us-east-1",
                    constraint.resource_type,
                )

                if capacity_result.available:
                    # Add capacity level as a property for sorting
                    constraint_with_capacity = constraint
                    constraint_with_capacity._capacity_level = (
                        capacity_result.capacity_level
                    )
                    available_constraints.append(constraint_with_capacity)

            except Exception:
                # Skip constraints where capacity check fails
                continue

        return available_constraints

    def _allocate_compute_with_capacity(
        self, total_hours: int, available_constraints: list[Constraint]
    ) -> list[Resource]:
        """Allocate compute resources considering capacity levels."""
        resources = []
        remaining_hours = total_hours

        # Filter and sort compute constraints by capacity and cost
        compute_constraints = [
            c for c in available_constraints if c.service in ["ec2", "compute"]
        ]

        # Sort by: free tier first, then by capacity level (desc), then by cost
        compute_constraints.sort(
            key=lambda c: (
                not c.is_free_tier(),  # Free tier first
                -getattr(c, "_capacity_level", 0.0),  # Higher capacity first
                c.cost_per_unit,  # Lower cost first
            )
        )

        for constraint in compute_constraints:
            if remaining_hours <= 0:
                break

            allocation = min(remaining_hours, constraint.limit_value)
            if allocation > 0:
                resource = Resource(
                    provider=constraint.provider,
                    service=constraint.service,
                    resource_type=constraint.resource_type,
                    region=(
                        constraint.region if constraint.region != "*" else "us-east-1"
                    ),
                    quantity=1,
                    estimated_monthly_usage=allocation,
                )
                resources.append(resource)
                remaining_hours -= allocation

        return resources

    def _allocate_storage_with_capacity(
        self, total_gb: int, available_constraints: list[Constraint]
    ) -> list[Resource]:
        """Allocate storage resources considering capacity levels."""
        resources = []
        remaining_gb = total_gb

        # Filter and sort storage constraints
        storage_constraints = [
            c for c in available_constraints if c.service in ["s3", "storage"]
        ]

        storage_constraints.sort(
            key=lambda c: (
                not c.is_free_tier(),
                -getattr(c, "_capacity_level", 0.0),
                c.cost_per_unit,
            )
        )

        for constraint in storage_constraints:
            if remaining_gb <= 0:
                break

            allocation = min(remaining_gb, constraint.limit_value)
            if allocation > 0:
                resource = Resource(
                    provider=constraint.provider,
                    service=constraint.service,
                    resource_type=constraint.resource_type,
                    region=(
                        constraint.region if constraint.region != "*" else "us-east-1"
                    ),
                    quantity=1,
                    estimated_monthly_usage=allocation,
                )
                resources.append(resource)
                remaining_gb -= allocation

        return resources
