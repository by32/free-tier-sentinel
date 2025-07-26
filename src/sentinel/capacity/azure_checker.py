"""Azure capacity checking implementation."""

from datetime import UTC, datetime
from unittest.mock import Mock

from sentinel.capacity.checker import CapacityChecker, CapacityResult


class AzureCapacityChecker(CapacityChecker):
    """Capacity checker for Azure Virtual Machines."""

    def __init__(self, subscription_id: str = "default-subscription"):
        """Initialize Azure capacity checker."""
        self.provider = "azure"
        self.subscription_id = subscription_id

        # Mock the Azure client for now
        # In a real implementation, this would be:
        # from azure.mgmt.compute import ComputeManagementClient
        # from azure.identity import DefaultAzureCredential
        # credential = DefaultAzureCredential()
        # self.compute_client = ComputeManagementClient(credential, subscription_id)
        self.compute_client = self._create_mock_client()

    def _create_mock_client(self):
        """Create a mock client for testing purposes."""
        client = Mock()

        # Mock VM sizes list
        vm_sizes_mock = Mock()

        # Create mock VM size objects with proper name attributes
        mock_b1s = Mock()
        mock_b1s.name = "Standard_B1s"
        mock_b2s = Mock()
        mock_b2s.name = "Standard_B2s"
        mock_d2s = Mock()
        mock_d2s.name = "Standard_D2s_v3"

        vm_sizes_mock.list.return_value = [mock_b1s, mock_b2s, mock_d2s]
        client.virtual_machine_sizes = vm_sizes_mock

        return client

    def check_availability(self, region: str, resource_type: str) -> CapacityResult:
        """Check availability of an Azure VM size in a region."""
        try:
            # Get available VM sizes for the region
            vm_sizes = self.compute_client.virtual_machine_sizes.list(location=region)

            available_sizes = [str(size.name) for size in vm_sizes]
            available = resource_type in available_sizes
            capacity_level = 1.0 if available else 0.0

            provider_data = {
                "provider": "azure",
                "subscription_id": self.subscription_id,
                "available_sizes": available_sizes,
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
            raise Exception(f"Azure API error: {str(e)}")

    def get_available_regions(self) -> list[str]:
        """Get list of available Azure regions."""
        # Simplified implementation - in reality would query Azure API
        return [
            "eastus",
            "eastus2",
            "westus",
            "westus2",
            "centralus",
            "northeurope",
            "westeurope",
            "eastasia",
            "southeastasia",
        ]

    def get_supported_resource_types(self) -> list[str]:
        """Get list of supported Azure VM sizes."""
        # Simplified implementation - in reality would query Azure API
        return [
            "Standard_B1s",
            "Standard_B2s",
            "Standard_D2s_v3",
            "Standard_F2s_v2",
            "Standard_E2s_v3",
        ]
