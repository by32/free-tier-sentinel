"""Constraint querying functionality."""

from sentinel.models.core import Constraint


class ConstraintQuery:
    """Query interface for constraints with method chaining."""

    def __init__(self, constraints: list[Constraint]):
        """Initialize with list of constraints."""
        self._constraints = constraints

    def by_provider(self, provider: str) -> "ConstraintQuery":
        """Filter constraints by provider."""
        filtered = [c for c in self._constraints if c.provider == provider]
        return ConstraintQuery(filtered)

    def by_service(self, service: str) -> "ConstraintQuery":
        """Filter constraints by service."""
        filtered = [c for c in self._constraints if c.service == service]
        return ConstraintQuery(filtered)

    def by_resource_type(self, resource_type: str) -> "ConstraintQuery":
        """Filter constraints by resource type."""
        filtered = [c for c in self._constraints if c.resource_type == resource_type]
        return ConstraintQuery(filtered)

    def by_region(self, region: str) -> "ConstraintQuery":
        """Filter constraints by region."""
        filtered = [c for c in self._constraints if c.region == region]
        return ConstraintQuery(filtered)

    def free_tier_only(self) -> "ConstraintQuery":
        """Filter to only free tier constraints."""
        filtered = [c for c in self._constraints if c.is_free_tier()]
        return ConstraintQuery(filtered)

    def __len__(self) -> int:
        """Return number of constraints."""
        return len(self._constraints)

    def __getitem__(self, index: int) -> Constraint:
        """Get constraint by index."""
        return self._constraints[index]

    def __iter__(self):
        """Make query results iterable."""
        return iter(self._constraints)

    def to_list(self) -> list[Constraint]:
        """Convert query results to list."""
        return self._constraints.copy()

    def __eq__(self, other) -> bool:
        """Support equality comparison with lists."""
        if isinstance(other, list):
            return self._constraints == other
        elif isinstance(other, ConstraintQuery):
            return self._constraints == other._constraints
        return False
