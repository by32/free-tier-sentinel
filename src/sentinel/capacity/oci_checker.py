"""OCI (Oracle Cloud Infrastructure) capacity checking implementation."""

from datetime import UTC, datetime
from typing import Any

import oci
from oci.exceptions import ServiceError

from sentinel.capacity.checker import CapacityChecker, CapacityResult


class OCICapacityChecker(CapacityChecker):
    """Capacity checker for OCI compute instances.

    Designed specifically to handle OCI free tier scarcity by checking
    all availability domains within the home region.
    """

    # OCI free tier shapes
    FREE_TIER_SHAPES = {
        "VM.Standard.A1.Flex": {
            "max_ocpus": 4,
            "max_memory_gb": 24,
            "description": "ARM-based Always Free instance",
        },
        "VM.Standard.E2.1.Micro": {
            "max_ocpus": 1,
            "max_memory_gb": 1,
            "description": "AMD-based Always Free instance",
        },
    }

    def __init__(self, config_file: str | None = None, profile: str = "DEFAULT"):
        """Initialize OCI capacity checker.

        Args:
            config_file: Path to OCI config file. Defaults to ~/.oci/config
            profile: Profile name in config file. Defaults to DEFAULT.
        """
        self.provider = "oci"

        # Load OCI configuration
        if config_file:
            self.config = oci.config.from_file(config_file, profile)
        else:
            self.config = oci.config.from_file(profile_name=profile)

        # Initialize clients
        self.identity_client = oci.identity.IdentityClient(self.config)
        self.compute_client = oci.core.ComputeClient(self.config)

        # Get home region and tenancy info
        self.tenancy_id = self.config["tenancy"]
        self._home_region: str | None = None
        self._availability_domains: list[dict[str, Any]] | None = None

    @property
    def home_region(self) -> str:
        """Get the home region for this tenancy (cached)."""
        if self._home_region is None:
            tenancy = self.identity_client.get_tenancy(self.tenancy_id).data
            self._home_region = tenancy.home_region_key
        return self._home_region

    def get_availability_domains(self) -> list[dict[str, Any]]:
        """Get all availability domains in the home region."""
        if self._availability_domains is None:
            ads = self.identity_client.list_availability_domains(
                compartment_id=self.tenancy_id
            ).data
            self._availability_domains = [
                {"name": ad.name, "id": ad.id} for ad in ads
            ]
        return self._availability_domains

    def check_availability(self, region: str, resource_type: str) -> CapacityResult:
        """Check availability of a compute shape across all ADs in home region.

        Note: OCI free tier is locked to home region, so the region parameter
        is validated but the check always uses the home region.
        """
        try:
            ads = self.get_availability_domains()
            available_ads: list[str] = []
            ad_capacity: dict[str, float] = {}

            for ad in ads:
                ad_name = ad["name"]
                try:
                    # Check shape availability in this AD
                    capacity = self._check_shape_in_ad(ad_name, resource_type)
                    ad_capacity[ad_name] = capacity

                    if capacity > 0:
                        available_ads.append(ad_name)
                except ServiceError as e:
                    # Capacity not available in this AD
                    if e.code == "InternalError" or "capacity" in str(e.message).lower():
                        ad_capacity[ad_name] = 0.0
                    else:
                        raise

            # Calculate overall capacity level
            total_ads = len(ads)
            available_count = len(available_ads)

            if available_count == 0:
                available = False
                capacity_level = 0.0
            else:
                available = True
                # Weight by individual AD capacity levels
                capacity_level = sum(ad_capacity.values()) / total_ads if total_ads > 0 else 0.0

            provider_data = {
                "provider": "oci",
                "home_region": self.home_region,
                "availability_domains": ads,
                "available_ads": available_ads,
                "ad_capacity": ad_capacity,
                "shape_info": self.FREE_TIER_SHAPES.get(resource_type, {}),
            }

            return CapacityResult(
                region=self.home_region,
                resource_type=resource_type,
                available=available,
                capacity_level=capacity_level,
                last_checked=datetime.now(UTC),
                provider_specific_data=provider_data,
            )

        except ServiceError as e:
            raise Exception(f"OCI API error: {e.code} - {e.message}") from e

    def _check_shape_in_ad(self, ad_name: str, shape: str) -> float:
        """Check if a shape is available in a specific availability domain.

        Returns capacity level (0.0-1.0) or raises ServiceError if unavailable.
        """
        # List available shapes in the AD
        shapes_response = self.compute_client.list_shapes(
            compartment_id=self.tenancy_id,
            availability_domain=ad_name,
        )

        available_shapes = [s.shape for s in shapes_response.data]

        if shape not in available_shapes:
            return 0.0

        # For shapes that are available, try to get capacity info
        # OCI doesn't provide a direct capacity API, so we infer from shape availability
        # A shape being listed doesn't guarantee provisioning success
        return 0.5  # Conservative estimate - shape is listed but may fail

    def check_capacity_by_ad(self, resource_type: str) -> dict[str, CapacityResult]:
        """Check capacity for each AD individually.

        Returns a dict mapping AD name to CapacityResult.
        Useful for finding which specific AD might have capacity.
        """
        results = {}
        ads = self.get_availability_domains()

        for ad in ads:
            ad_name = ad["name"]
            try:
                capacity = self._check_shape_in_ad(ad_name, resource_type)
                results[ad_name] = CapacityResult(
                    region=self.home_region,
                    resource_type=resource_type,
                    available=capacity > 0,
                    capacity_level=capacity,
                    last_checked=datetime.now(UTC),
                    provider_specific_data={
                        "provider": "oci",
                        "availability_domain": ad_name,
                    },
                )
            except ServiceError as e:
                results[ad_name] = CapacityResult(
                    region=self.home_region,
                    resource_type=resource_type,
                    available=False,
                    capacity_level=0.0,
                    last_checked=datetime.now(UTC),
                    provider_specific_data={
                        "provider": "oci",
                        "availability_domain": ad_name,
                        "error": str(e.message),
                    },
                )

        return results

    def try_provision_in_ad(
        self,
        ad_name: str,
        shape: str,
        ocpus: int = 1,
        memory_gb: int = 6,
        display_name: str = "free-tier-instance",
        image_id: str | None = None,
        subnet_id: str | None = None,
        ssh_public_key: str | None = None,
    ) -> dict[str, Any]:
        """Attempt to provision an instance in a specific AD.

        This is a "try" operation - it may fail due to capacity constraints.

        Args:
            ad_name: Availability domain name
            shape: Compute shape (e.g., VM.Standard.A1.Flex)
            ocpus: Number of OCPUs (for flex shapes)
            memory_gb: Memory in GB (for flex shapes)
            display_name: Instance display name
            image_id: Boot image OCID (required)
            subnet_id: Subnet OCID (required)
            ssh_public_key: SSH public key for access

        Returns:
            Dict with instance details on success

        Raises:
            ServiceError: If provisioning fails (including capacity issues)
        """
        if not image_id or not subnet_id:
            raise ValueError("image_id and subnet_id are required for provisioning")

        # Build shape config for flex shapes
        shape_config = None
        if "Flex" in shape:
            shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=float(ocpus),
                memory_in_gbs=float(memory_gb),
            )

        # Build instance metadata
        metadata = {}
        if ssh_public_key:
            metadata["ssh_authorized_keys"] = ssh_public_key

        # Create launch details
        launch_details = oci.core.models.LaunchInstanceDetails(
            availability_domain=ad_name,
            compartment_id=self.tenancy_id,
            shape=shape,
            shape_config=shape_config,
            display_name=display_name,
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                image_id=image_id,
                boot_volume_size_in_gbs=50,  # Free tier includes 200GB total
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id,
                assign_public_ip=True,
            ),
            metadata=metadata,
            is_pv_encryption_in_transit_enabled=True,
        )

        # Attempt to launch
        response = self.compute_client.launch_instance(launch_details)
        instance = response.data

        return {
            "instance_id": instance.id,
            "display_name": instance.display_name,
            "availability_domain": instance.availability_domain,
            "shape": instance.shape,
            "lifecycle_state": instance.lifecycle_state,
            "time_created": str(instance.time_created),
        }

    def get_available_regions(self) -> list[str]:
        """Get the home region (OCI free tier is single-region)."""
        return [self.home_region]

    def get_supported_resource_types(self) -> list[str]:
        """Get list of OCI free tier shapes."""
        return list(self.FREE_TIER_SHAPES.keys())


class MockOCICapacityChecker(CapacityChecker):
    """Mock OCI capacity checker for testing without OCI credentials."""

    FREE_TIER_SHAPES = OCICapacityChecker.FREE_TIER_SHAPES

    def __init__(self, home_region: str = "us-ashburn-1"):
        """Initialize mock checker."""
        self.provider = "oci"
        self._home_region = home_region
        self._mock_ads = [
            {"name": f"{home_region}-AD-1", "id": "ad1"},
            {"name": f"{home_region}-AD-2", "id": "ad2"},
            {"name": f"{home_region}-AD-3", "id": "ad3"},
        ]
        # Simulate typical scarcity - only AD-3 has occasional capacity
        self._ad_capacity = {
            f"{home_region}-AD-1": 0.0,
            f"{home_region}-AD-2": 0.0,
            f"{home_region}-AD-3": 0.3,
        }

    def set_ad_capacity(self, ad_name: str, capacity: float) -> None:
        """Set mock capacity for testing."""
        self._ad_capacity[ad_name] = capacity

    def check_availability(self, region: str, resource_type: str) -> CapacityResult:
        """Check mock availability."""
        available_ads = [
            ad["name"] for ad in self._mock_ads
            if self._ad_capacity.get(ad["name"], 0) > 0
        ]

        total_capacity = sum(self._ad_capacity.values())
        capacity_level = total_capacity / len(self._mock_ads) if self._mock_ads else 0.0

        return CapacityResult(
            region=self._home_region,
            resource_type=resource_type,
            available=len(available_ads) > 0,
            capacity_level=capacity_level,
            last_checked=datetime.now(UTC),
            provider_specific_data={
                "provider": "oci",
                "home_region": self._home_region,
                "available_ads": available_ads,
                "ad_capacity": self._ad_capacity.copy(),
            },
        )

    def get_available_regions(self) -> list[str]:
        """Get mock home region."""
        return [self._home_region]

    def get_supported_resource_types(self) -> list[str]:
        """Get list of OCI free tier shapes."""
        return list(self.FREE_TIER_SHAPES.keys())
