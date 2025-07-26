"""GCP capacity checking implementation."""

from datetime import UTC, datetime
from unittest.mock import Mock

from sentinel.capacity.checker import CapacityChecker, CapacityResult


class GCPCapacityChecker(CapacityChecker):
    """Capacity checker for GCP Compute Engine instances."""

    def __init__(self, project_id: str = "default-project"):
        """Initialize GCP capacity checker."""
        self.provider = "gcp"
        self.project_id = project_id

        # Mock the Google Cloud client for now
        # In a real implementation, this would be:
        # from googleapiclient import discovery
        # self.compute_client = discovery.build('compute', 'v1')
        self.compute_client = self._create_mock_client()

    def _create_mock_client(self):
        """Create a mock client for testing purposes."""
        client = Mock()

        # Mock zones list
        zones_mock = Mock()
        zones_mock.list.return_value.execute.return_value = {
            "items": [
                {"name": "us-central1-a", "status": "UP"},
                {"name": "us-central1-b", "status": "UP"},
                {"name": "us-central1-c", "status": "UP"},
            ]
        }
        client.zones.return_value = zones_mock

        # Mock machine types list
        machine_types_mock = Mock()
        machine_types_mock.list.return_value.execute.return_value = {
            "items": [
                {"name": "f1-micro", "zone": "us-central1-a"},
                {"name": "f1-micro", "zone": "us-central1-b"},
                {"name": "f1-micro", "zone": "us-central1-c"},
            ]
        }
        client.machineTypes.return_value = machine_types_mock

        return client

    def check_availability(self, region: str, resource_type: str) -> CapacityResult:
        """Check availability of a GCP machine type in a region."""
        try:
            # Get available zones for the region
            zones_response = (
                self.compute_client.zones()
                .list(project=self.project_id, filter=f"name:{region}-*")
                .execute()
            )

            available_zones = [
                zone["name"]
                for zone in zones_response.get("items", [])
                if zone["status"] == "UP"
            ]

            # Check machine type availability
            machine_types_response = (
                self.compute_client.machineTypes()
                .list(
                    project=self.project_id,
                    zone=available_zones[0] if available_zones else f"{region}-a",
                )
                .execute()
            )

            available_machine_types = [
                mt["name"]
                for mt in machine_types_response.get("items", [])
                if mt["name"] == resource_type
            ]

            available = len(available_machine_types) > 0 and len(available_zones) > 0
            capacity_level = 1.0 if available else 0.0

            provider_data = {
                "provider": "gcp",
                "available_zones": available_zones,
                "project_id": self.project_id,
            }

            return CapacityResult(
                region=region,
                resource_type=resource_type,
                available=available,
                capacity_level=capacity_level,
                last_checked=datetime.now(UTC),
                provider_specific_data=provider_data,
            )

        except Exception as e:
            raise Exception(f"GCP API error: {str(e)}")

    def get_available_regions(self) -> list[str]:
        """Get list of available GCP regions."""
        # Simplified implementation - in reality would query GCP API
        return [
            "us-central1",
            "us-east1",
            "us-west1",
            "us-west2",
            "europe-west1",
            "europe-west2",
            "asia-east1",
        ]

    def get_supported_resource_types(self) -> list[str]:
        """Get list of supported GCP machine types."""
        # Simplified implementation - in reality would query GCP API
        return [
            "f1-micro",
            "g1-small",
            "n1-standard-1",
            "n1-standard-2",
            "e2-micro",
            "e2-small",
            "e2-medium",
        ]
