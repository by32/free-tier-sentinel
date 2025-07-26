"""Capacity aggregation across multiple cloud providers."""

from concurrent.futures import ThreadPoolExecutor, as_completed

from sentinel.capacity.cache import CapacityCache
from sentinel.capacity.checker import CapacityChecker, CapacityResult
from sentinel.models.core import Resource


class CapacityAggregator:
    """Aggregates capacity checking across multiple cloud providers."""

    def __init__(self, checkers: dict[str, CapacityChecker], cache: CapacityCache):
        """Initialize aggregator with provider checkers and cache."""
        self.checkers = checkers
        self.cache = cache

    def check_availability(
        self, provider: str, region: str, resource_type: str
    ) -> CapacityResult:
        """Check availability for a specific provider/region/resource combination."""
        # Try cache first
        cached_result = self.cache.get(provider, region, resource_type)
        if cached_result:
            return cached_result

        # Check with provider
        if provider not in self.checkers:
            raise ValueError(f"Unknown provider: {provider}")

        checker = self.checkers[provider]
        result = checker.check_availability(region, resource_type)

        # Cache the result
        self.cache.set(provider, region, resource_type, result)

        return result

    def check_availability_all_providers(
        self, requests: list[tuple[str, str, str]]
    ) -> list[CapacityResult]:
        """Check availability for multiple provider/region/resource combinations concurrently."""
        results = []

        # Use ThreadPoolExecutor for concurrent checks
        with ThreadPoolExecutor(max_workers=len(self.checkers)) as executor:
            # Submit all tasks
            future_to_request = {}
            for provider, region, resource_type in requests:
                future = executor.submit(
                    self.check_availability, provider, region, resource_type
                )
                future_to_request[future] = (provider, region, resource_type)

            # Collect results as they complete
            for future in as_completed(future_to_request):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    provider, region, resource_type = future_to_request[future]
                    # Create a failed result for error cases
                    from datetime import UTC, datetime

                    error_result = CapacityResult(
                        region=region,
                        resource_type=resource_type,
                        available=False,
                        capacity_level=0.0,
                        last_checked=datetime.now(UTC),
                        provider_specific_data={"provider": provider, "error": str(e)},
                    )
                    results.append(error_result)

        return results

    def filter_available_resources(self, resources: list[Resource]) -> list[Resource]:
        """Filter a list of resources to only include those with available capacity."""
        available_resources = []

        # Create requests for all resources
        requests = [
            (resource.provider, resource.region, resource.resource_type)
            for resource in resources
        ]

        # Check availability for all resources
        capacity_results = self.check_availability_all_providers(requests)

        # Create a mapping of results by resource identifier
        result_map = {}
        for i, result in enumerate(capacity_results):
            # Use the original resource as the key source
            if i < len(resources):
                resource = resources[i]
                key = (resource.provider, resource.region, resource.resource_type)
                result_map[key] = result

        # Filter resources based on availability
        for resource in resources:
            key = (resource.provider, resource.region, resource.resource_type)
            if key in result_map and result_map[key].available:
                available_resources.append(resource)

        return available_resources

    def get_capacity_summary(self) -> dict[str, dict]:
        """Get a summary of capacity across all providers."""
        summary = {}

        for provider_name, checker in self.checkers.items():
            provider_summary = {
                "regions": checker.get_available_regions(),
                "resource_types": checker.get_supported_resource_types(),
                "checker_type": type(checker).__name__,
            }
            summary[provider_name] = provider_summary

        return summary

    def warm_cache(self, regions: list[str], resource_types: list[str]):
        """Pre-populate cache with capacity data for common regions/types."""
        requests = []

        for provider in self.checkers.keys():
            for region in regions:
                for resource_type in resource_types:
                    requests.append((provider, region, resource_type))

        # Check all combinations concurrently
        self.check_availability_all_providers(requests)
