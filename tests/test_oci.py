"""Tests for OCI capacity checking and hunting functionality."""

import time

import pytest

from sentinel.capacity.hunter import (
    CapacityHunter,
    HuntConfig,
    HuntStatus,
    HuntTarget,
)
from sentinel.capacity.oci_checker import MockOCICapacityChecker, OCICapacityChecker


class TestMockOCICapacityChecker:
    """Test the mock OCI capacity checker."""

    def test_mock_checker_initialization(self):
        """Test mock checker initializes correctly."""
        checker = MockOCICapacityChecker(home_region="us-ashburn-1")

        assert checker.provider == "oci"
        assert checker._home_region == "us-ashburn-1"
        assert len(checker._mock_ads) == 3

    def test_mock_checker_get_regions(self):
        """Test mock checker returns home region only."""
        checker = MockOCICapacityChecker(home_region="us-phoenix-1")
        regions = checker.get_available_regions()

        assert regions == ["us-phoenix-1"]

    def test_mock_checker_get_supported_types(self):
        """Test mock checker returns free tier shapes."""
        checker = MockOCICapacityChecker()
        shapes = checker.get_supported_resource_types()

        assert "VM.Standard.A1.Flex" in shapes
        assert "VM.Standard.E2.1.Micro" in shapes

    def test_mock_checker_check_availability_with_capacity(self):
        """Test capacity check when some ADs have capacity."""
        checker = MockOCICapacityChecker(home_region="us-ashburn-1")
        # Default mock has AD-3 with 0.3 capacity

        result = checker.check_availability("us-ashburn-1", "VM.Standard.A1.Flex")

        assert result.available is True
        assert result.capacity_level > 0
        assert result.region == "us-ashburn-1"
        assert result.resource_type == "VM.Standard.A1.Flex"
        assert "us-ashburn-1-AD-3" in result.provider_specific_data["available_ads"]

    def test_mock_checker_check_availability_no_capacity(self):
        """Test capacity check when no ADs have capacity."""
        checker = MockOCICapacityChecker(home_region="us-ashburn-1")
        # Set all ADs to 0 capacity
        checker.set_ad_capacity("us-ashburn-1-AD-1", 0.0)
        checker.set_ad_capacity("us-ashburn-1-AD-2", 0.0)
        checker.set_ad_capacity("us-ashburn-1-AD-3", 0.0)

        result = checker.check_availability("us-ashburn-1", "VM.Standard.A1.Flex")

        assert result.available is False
        assert result.capacity_level == 0.0
        assert len(result.provider_specific_data["available_ads"]) == 0

    def test_mock_checker_set_ad_capacity(self):
        """Test setting AD capacity for testing scenarios."""
        checker = MockOCICapacityChecker(home_region="us-ashburn-1")

        # Set AD-1 to have high capacity
        checker.set_ad_capacity("us-ashburn-1-AD-1", 0.9)

        result = checker.check_availability("us-ashburn-1", "VM.Standard.A1.Flex")

        assert "us-ashburn-1-AD-1" in result.provider_specific_data["available_ads"]
        assert result.provider_specific_data["ad_capacity"]["us-ashburn-1-AD-1"] == 0.9


class TestHuntTarget:
    """Test hunt target configuration."""

    def test_hunt_target_defaults(self):
        """Test hunt target has sensible defaults."""
        target = HuntTarget(
            provider="oci",
            resource_type="VM.Standard.A1.Flex",
        )

        assert target.provider == "oci"
        assert target.resource_type == "VM.Standard.A1.Flex"
        assert target.ocpus == 1
        assert target.memory_gb == 6
        assert target.display_name == "free-tier-instance"

    def test_hunt_target_custom_config(self):
        """Test hunt target with custom configuration."""
        target = HuntTarget(
            provider="oci",
            resource_type="VM.Standard.A1.Flex",
            ocpus=4,
            memory_gb=24,
            display_name="my-instance",
            image_id="ocid1.image.test",
            subnet_id="ocid1.subnet.test",
        )

        assert target.ocpus == 4
        assert target.memory_gb == 24
        assert target.display_name == "my-instance"
        assert target.image_id == "ocid1.image.test"


class TestHuntConfig:
    """Test hunt configuration."""

    def test_hunt_config_defaults(self):
        """Test hunt config has sensible defaults."""
        config = HuntConfig()

        assert config.poll_interval_seconds == 30.0
        assert config.min_poll_interval == 10.0
        assert config.max_poll_interval == 120.0
        assert config.max_attempts == 0  # Unlimited
        assert config.auto_provision is True

    def test_hunt_config_custom(self):
        """Test hunt config with custom values."""
        config = HuntConfig(
            poll_interval_seconds=15.0,
            max_attempts=100,
            auto_provision=False,
        )

        assert config.poll_interval_seconds == 15.0
        assert config.max_attempts == 100
        assert config.auto_provision is False


class TestCapacityHunter:
    """Test the capacity hunter."""

    @pytest.fixture
    def mock_checker(self):
        """Create a mock checker for testing."""
        return MockOCICapacityChecker(home_region="us-ashburn-1")

    @pytest.fixture
    def basic_target(self):
        """Create a basic hunt target."""
        return HuntTarget(
            provider="oci",
            resource_type="VM.Standard.A1.Flex",
        )

    def test_hunter_initialization(self, mock_checker):
        """Test hunter initializes correctly."""
        config = HuntConfig(poll_interval_seconds=5.0)
        hunter = CapacityHunter(mock_checker, config)

        assert hunter.checker is mock_checker
        assert hunter.config.poll_interval_seconds == 5.0
        assert hunter.status == HuntStatus.IDLE

    def test_hunter_finds_capacity_immediately(self, mock_checker, basic_target):
        """Test hunter finds capacity when available."""
        # Ensure capacity is available
        mock_checker.set_ad_capacity("us-ashburn-1-AD-1", 0.8)

        config = HuntConfig(
            poll_interval_seconds=1.0,
            max_attempts=3,
            auto_provision=False,  # Don't try to actually provision
        )
        hunter = CapacityHunter(mock_checker, config)

        result = hunter.hunt(basic_target)

        assert result.status == HuntStatus.SUCCESS
        assert result.attempts >= 1
        assert len(result.capacity_checks) > 0

    def test_hunter_respects_max_attempts(self, mock_checker, basic_target):
        """Test hunter stops after max attempts."""
        # Set no capacity
        mock_checker.set_ad_capacity("us-ashburn-1-AD-1", 0.0)
        mock_checker.set_ad_capacity("us-ashburn-1-AD-2", 0.0)
        mock_checker.set_ad_capacity("us-ashburn-1-AD-3", 0.0)

        config = HuntConfig(
            poll_interval_seconds=0.1,
            max_attempts=3,
            auto_provision=False,
        )
        hunter = CapacityHunter(mock_checker, config)

        result = hunter.hunt(basic_target)

        assert result.status == HuntStatus.FAILED
        assert result.attempts >= 3  # May be 3 or 4 depending on timing
        assert "Max attempts" in (result.error_message or "")

    def test_hunter_respects_max_duration(self, mock_checker, basic_target):
        """Test hunter stops after max duration."""
        # Set no capacity
        mock_checker.set_ad_capacity("us-ashburn-1-AD-1", 0.0)
        mock_checker.set_ad_capacity("us-ashburn-1-AD-2", 0.0)
        mock_checker.set_ad_capacity("us-ashburn-1-AD-3", 0.0)

        config = HuntConfig(
            poll_interval_seconds=0.1,
            max_duration_seconds=0.5,
            auto_provision=False,
        )
        hunter = CapacityHunter(mock_checker, config)

        result = hunter.hunt(basic_target)

        assert result.status == HuntStatus.FAILED
        assert "Max duration" in (result.error_message or "")

    def test_hunter_can_be_cancelled(self, mock_checker, basic_target):
        """Test hunter can be cancelled."""
        # Set no capacity so it keeps hunting
        mock_checker.set_ad_capacity("us-ashburn-1-AD-1", 0.0)
        mock_checker.set_ad_capacity("us-ashburn-1-AD-2", 0.0)
        mock_checker.set_ad_capacity("us-ashburn-1-AD-3", 0.0)

        config = HuntConfig(
            poll_interval_seconds=0.5,
            auto_provision=False,
        )
        hunter = CapacityHunter(mock_checker, config)

        # Start hunt in background
        result_holder = {}
        def capture_result(result):
            result_holder['result'] = result

        hunter.start_hunt(basic_target, callback=capture_result)

        # Let it run for a bit
        time.sleep(0.3)

        # Cancel
        hunter.stop_hunt()

        # Wait for thread to finish
        time.sleep(0.3)

        assert hunter.status == HuntStatus.CANCELLED

    def test_hunter_callbacks_are_called(self, mock_checker, basic_target):
        """Test hunter calls status change callbacks."""
        mock_checker.set_ad_capacity("us-ashburn-1-AD-1", 0.8)

        status_changes = []

        def on_status_change(status, message):
            status_changes.append((status, message))

        config = HuntConfig(
            poll_interval_seconds=0.1,
            max_attempts=2,
            auto_provision=False,
            on_status_change=on_status_change,
        )
        hunter = CapacityHunter(mock_checker, config)

        _result = hunter.hunt(basic_target)

        # Should have received status updates
        assert len(status_changes) > 0
        statuses = [s[0] for s in status_changes]
        assert HuntStatus.HUNTING in statuses

    def test_hunter_capacity_found_callback(self, mock_checker, basic_target):
        """Test hunter calls capacity found callback."""
        mock_checker.set_ad_capacity("us-ashburn-1-AD-2", 0.7)

        capacity_found_calls = []

        def on_capacity_found(ad_name, result):
            capacity_found_calls.append((ad_name, result))

        config = HuntConfig(
            poll_interval_seconds=0.1,
            max_attempts=2,
            auto_provision=False,
            on_capacity_found=on_capacity_found,
        )
        hunter = CapacityHunter(mock_checker, config)

        _result = hunter.hunt(basic_target)

        # Should have found capacity
        assert len(capacity_found_calls) > 0


class TestOCIConstraints:
    """Test OCI constraint file loading."""

    def test_oci_constraints_file_exists(self):
        """Test OCI constraints file exists and is valid YAML."""
        import os

        import yaml

        constraints_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "constraints",
            "oci.yaml"
        )

        assert os.path.exists(constraints_path)

        with open(constraints_path) as f:
            data = yaml.safe_load(f)

        assert data["provider"] == "oci"
        assert "constraints" in data
        assert len(data["constraints"]) > 0

    def test_oci_constraints_include_a1_flex(self):
        """Test OCI constraints include A1 Flex shape."""
        import os

        import yaml

        constraints_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "constraints",
            "oci.yaml"
        )

        with open(constraints_path) as f:
            data = yaml.safe_load(f)

        a1_constraints = [
            c for c in data["constraints"]
            if c.get("resource_type") == "VM.Standard.A1.Flex"
        ]

        assert len(a1_constraints) >= 2  # OCPUs and memory limits

    def test_oci_constraints_can_be_loaded(self):
        """Test OCI constraints can be loaded by the constraint loader."""
        import os

        from sentinel.constraints.loader import ConstraintLoader

        constraints_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "constraints",
            "oci.yaml"
        )

        loader = ConstraintLoader()
        constraints = loader.load_from_file(constraints_path)

        assert len(constraints) > 0
        assert all(c.provider == "oci" for c in constraints)


class TestOCICapacityCheckerMocked:
    """Test OCI capacity checker with mocked OCI SDK."""

    @pytest.fixture
    def mock_oci_config(self):
        """Mock OCI configuration."""
        return {
            "tenancy": "ocid1.tenancy.test",
            "user": "ocid1.user.test",
            "fingerprint": "aa:bb:cc:dd",
            "key_file": "/path/to/key.pem",
            "region": "us-ashburn-1",
        }

    def test_oci_checker_free_tier_shapes(self):
        """Test OCI checker knows about free tier shapes."""
        shapes = OCICapacityChecker.FREE_TIER_SHAPES

        assert "VM.Standard.A1.Flex" in shapes
        assert "VM.Standard.E2.1.Micro" in shapes
        assert shapes["VM.Standard.A1.Flex"]["max_ocpus"] == 4
        assert shapes["VM.Standard.A1.Flex"]["max_memory_gb"] == 24
