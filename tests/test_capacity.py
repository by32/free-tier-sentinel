"""Test capacity detection system using TDD approach."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from sentinel.capacity.aggregator import CapacityAggregator
from sentinel.capacity.aws_checker import AWSCapacityChecker
from sentinel.capacity.azure_checker import AzureCapacityChecker
from sentinel.capacity.cache import CapacityCache
from sentinel.capacity.checker import CapacityChecker
from sentinel.capacity.gcp_checker import GCPCapacityChecker
from sentinel.models.core import Resource


class TestCapacityChecker:
    """Test base capacity checker interface."""

    def test_capacity_checker_interface(self):
        """Test that capacity checker defines the required interface."""
        # Test that we can't instantiate abstract class
        with pytest.raises(TypeError):
            CapacityChecker()

        # Test that subclass must implement abstract methods
        class IncompleteChecker(CapacityChecker):
            pass

        with pytest.raises(TypeError):
            IncompleteChecker()

    def test_capacity_result_data_structure(self):
        """Test the capacity result data structure."""
        from sentinel.capacity.checker import CapacityResult

        result = CapacityResult(
            region="us-east-1",
            resource_type="t2.micro",
            available=True,
            capacity_level=0.85,  # 85% available
            last_checked=datetime.now(UTC),
            provider_specific_data={"availability_zone": "us-east-1a"},
        )

        assert result.region == "us-east-1"
        assert result.resource_type == "t2.micro"
        assert result.available is True
        assert result.capacity_level == 0.85
        assert isinstance(result.last_checked, datetime)
        assert "availability_zone" in result.provider_specific_data

    def test_capacity_error_handling(self):
        """Test capacity error data structure."""
        from sentinel.capacity.checker import CapacityError

        error = CapacityError(
            region="us-west-2",
            resource_type="c5.large",
            error_type="API_RATE_LIMIT",
            error_message="Rate limit exceeded",
            retry_after=timedelta(minutes=5),
        )

        assert error.region == "us-west-2"
        assert error.resource_type == "c5.large"
        assert error.error_type == "API_RATE_LIMIT"
        assert error.retry_after == timedelta(minutes=5)


class TestAWSCapacityChecker:
    """Test AWS-specific capacity checking."""

    @pytest.fixture
    def mock_ec2_client(self):
        """Create a mock EC2 client."""
        client = Mock()
        client.describe_availability_zones.return_value = {
            "AvailabilityZones": [
                {"ZoneName": "us-east-1a", "State": "available"},
                {"ZoneName": "us-east-1b", "State": "available"},
                {"ZoneName": "us-east-1c", "State": "unavailable"},  # Capacity issue
            ]
        }
        client.describe_instance_type_offerings.return_value = {
            "InstanceTypeOfferings": [
                {"InstanceType": "t2.micro", "Location": "us-east-1a"},
                {"InstanceType": "t2.micro", "Location": "us-east-1b"},
                # Not available in us-east-1c
            ]
        }
        return client

    def test_aws_checker_creation(self, mock_ec2_client):
        """Test creating an AWS capacity checker."""
        with patch("boto3.client", return_value=mock_ec2_client):
            checker = AWSCapacityChecker()

            assert checker.provider == "aws"
            assert hasattr(checker, "ec2_client")

    def test_aws_check_availability_success(self, mock_ec2_client):
        """Test successful availability check for AWS resources."""
        with patch("boto3.client", return_value=mock_ec2_client):
            checker = AWSCapacityChecker()

            result = checker.check_availability("us-east-1", "t2.micro")

            assert result.region == "us-east-1"
            assert result.resource_type == "t2.micro"
            assert result.available is True
            assert result.capacity_level > 0.0
            assert result.provider_specific_data["provider"] == "aws"

    def test_aws_check_availability_partial_capacity(self, mock_ec2_client):
        """Test availability check when only some AZs have capacity."""
        # Modify mock to show limited availability
        mock_ec2_client.describe_instance_type_offerings.return_value = {
            "InstanceTypeOfferings": [
                {"InstanceType": "t2.micro", "Location": "us-east-1a"},
                # Only available in one AZ
            ]
        }

        with patch("boto3.client", return_value=mock_ec2_client):
            checker = AWSCapacityChecker()

            result = checker.check_availability("us-east-1", "t2.micro")

            assert result.available is True  # Still available, but limited
            assert result.capacity_level < 1.0  # Reduced capacity
            assert "limited_availability" in result.provider_specific_data

    def test_aws_check_availability_no_capacity(self, mock_ec2_client):
        """Test availability check when no capacity is available."""
        mock_ec2_client.describe_instance_type_offerings.return_value = {
            "InstanceTypeOfferings": []  # No availability
        }

        with patch("boto3.client", return_value=mock_ec2_client):
            checker = AWSCapacityChecker()

            result = checker.check_availability("us-east-1", "t2.micro")

            assert result.available is False
            assert result.capacity_level == 0.0

    def test_aws_get_available_regions(self, mock_ec2_client):
        """Test getting available AWS regions."""
        mock_ec2_client.describe_regions.return_value = {
            "Regions": [
                {"RegionName": "us-east-1"},
                {"RegionName": "us-west-2"},
                {"RegionName": "eu-west-1"},
            ]
        }

        with patch("boto3.client", return_value=mock_ec2_client):
            checker = AWSCapacityChecker()

            regions = checker.get_available_regions()

            assert "us-east-1" in regions
            assert "us-west-2" in regions
            assert "eu-west-1" in regions

    def test_aws_api_error_handling(self, mock_ec2_client):
        """Test handling of AWS API errors."""
        from botocore.exceptions import ClientError

        mock_ec2_client.describe_instance_type_offerings.side_effect = ClientError(
            {"Error": {"Code": "Throttling", "Message": "Rate exceeded"}},
            "DescribeInstanceTypeOfferings",
        )

        with patch("boto3.client", return_value=mock_ec2_client):
            checker = AWSCapacityChecker()

            with pytest.raises(Exception):  # Should handle API errors gracefully
                checker.check_availability("us-east-1", "t2.micro")


class TestGCPCapacityChecker:
    """Test GCP-specific capacity checking."""

    @pytest.fixture
    def mock_compute_client(self):
        """Create a mock GCP Compute client."""
        client = Mock()
        client.zones().list().execute.return_value = {
            "items": [
                {"name": "us-central1-a", "status": "UP"},
                {"name": "us-central1-b", "status": "UP"},
                {"name": "us-central1-c", "status": "DOWN"},
            ]
        }
        client.machineTypes().list().execute.return_value = {
            "items": [
                {"name": "f1-micro", "zone": "us-central1-a"},
                {"name": "f1-micro", "zone": "us-central1-b"},
            ]
        }
        return client

    def test_gcp_checker_creation(self, mock_compute_client):
        """Test creating a GCP capacity checker."""
        # GCP checker uses mock client by default in our implementation
        checker = GCPCapacityChecker()

        assert checker.provider == "gcp"
        assert hasattr(checker, "compute_client")

    def test_gcp_check_availability_success(self, mock_compute_client):
        """Test successful availability check for GCP resources."""
        # GCP checker uses mock client by default in our implementation
        checker = GCPCapacityChecker()

        result = checker.check_availability("us-central1", "f1-micro")

        assert result.region == "us-central1"
        assert result.resource_type == "f1-micro"
        assert result.available is True
        assert result.provider_specific_data["provider"] == "gcp"


class TestAzureCapacityChecker:
    """Test Azure-specific capacity checking."""

    @pytest.fixture
    def mock_compute_client(self):
        """Create a mock Azure Compute client."""
        client = Mock()
        client.virtual_machine_sizes.list.return_value = [
            Mock(name="Standard_B1s"),
            Mock(name="Standard_B2s"),
        ]
        return client

    def test_azure_checker_creation(self, mock_compute_client):
        """Test creating an Azure capacity checker."""
        # Azure checker uses mock client by default in our implementation
        checker = AzureCapacityChecker()

        assert checker.provider == "azure"
        assert hasattr(checker, "compute_client")

    def test_azure_check_availability_success(self, mock_compute_client):
        """Test successful availability check for Azure resources."""
        # Azure checker uses mock client by default in our implementation
        checker = AzureCapacityChecker()

        result = checker.check_availability("eastus", "Standard_B1s")

        assert result.region == "eastus"
        assert result.resource_type == "Standard_B1s"
        assert result.available is True
        assert result.provider_specific_data["provider"] == "azure"


class TestCapacityCache:
    """Test capacity caching system."""

    def test_cache_creation(self):
        """Test creating a capacity cache."""
        cache = CapacityCache(ttl_seconds=300)  # 5 minute TTL

        assert cache.ttl_seconds == 300
        assert hasattr(cache, "get")
        assert hasattr(cache, "set")
        assert hasattr(cache, "clear")

    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        from sentinel.capacity.checker import CapacityResult

        cache = CapacityCache(ttl_seconds=300)

        result = CapacityResult(
            region="us-east-1",
            resource_type="t2.micro",
            available=True,
            capacity_level=0.9,
            last_checked=datetime.now(UTC),
        )

        cache.set("aws", "us-east-1", "t2.micro", result)
        cached_result = cache.get("aws", "us-east-1", "t2.micro")

        assert cached_result is not None
        assert cached_result.region == "us-east-1"
        assert cached_result.resource_type == "t2.micro"
        assert cached_result.available is True

    def test_cache_expiration(self):
        """Test that cache entries expire after TTL."""
        from sentinel.capacity.checker import CapacityResult

        cache = CapacityCache(ttl_seconds=0.1)  # 100ms TTL

        result = CapacityResult(
            region="us-east-1",
            resource_type="t2.micro",
            available=True,
            capacity_level=0.9,
            last_checked=datetime.now(UTC),
        )

        cache.set("aws", "us-east-1", "t2.micro", result)

        # Should be available immediately
        cached_result = cache.get("aws", "us-east-1", "t2.micro")
        assert cached_result is not None

        # Should expire after TTL
        import time

        time.sleep(0.2)

        expired_result = cache.get("aws", "us-east-1", "t2.micro")
        assert expired_result is None

    def test_cache_key_generation(self):
        """Test cache key generation for different providers/regions/types."""
        cache = CapacityCache(ttl_seconds=300)

        # Should generate unique keys for different combinations
        key1 = cache._generate_key("aws", "us-east-1", "t2.micro")
        key2 = cache._generate_key("aws", "us-west-2", "t2.micro")
        key3 = cache._generate_key("gcp", "us-east-1", "f1-micro")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_cache_clear(self):
        """Test clearing cache entries."""
        from sentinel.capacity.checker import CapacityResult

        cache = CapacityCache(ttl_seconds=300)

        result = CapacityResult(
            region="us-east-1",
            resource_type="t2.micro",
            available=True,
            capacity_level=0.9,
            last_checked=datetime.now(UTC),
        )

        cache.set("aws", "us-east-1", "t2.micro", result)
        assert cache.get("aws", "us-east-1", "t2.micro") is not None

        cache.clear()
        assert cache.get("aws", "us-east-1", "t2.micro") is None


class TestCapacityAggregator:
    """Test capacity aggregation across providers."""

    @pytest.fixture
    def mock_checkers(self):
        """Create mock capacity checkers for testing."""
        aws_checker = Mock()
        gcp_checker = Mock()
        azure_checker = Mock()

        return {"aws": aws_checker, "gcp": gcp_checker, "azure": azure_checker}

    def test_aggregator_creation(self, mock_checkers):
        """Test creating a capacity aggregator."""
        cache = CapacityCache(ttl_seconds=300)
        aggregator = CapacityAggregator(mock_checkers, cache)

        assert len(aggregator.checkers) == 3
        assert "aws" in aggregator.checkers
        assert "gcp" in aggregator.checkers
        assert "azure" in aggregator.checkers

    def test_check_availability_single_provider(self, mock_checkers):
        """Test checking availability for a single provider."""
        from sentinel.capacity.checker import CapacityResult

        # Mock AWS checker response
        mock_result = CapacityResult(
            region="us-east-1",
            resource_type="t2.micro",
            available=True,
            capacity_level=0.8,
            last_checked=datetime.now(UTC),
        )
        mock_checkers["aws"].check_availability.return_value = mock_result

        cache = CapacityCache(ttl_seconds=300)
        aggregator = CapacityAggregator(mock_checkers, cache)

        result = aggregator.check_availability("aws", "us-east-1", "t2.micro")

        assert result.available is True
        assert result.capacity_level == 0.8
        mock_checkers["aws"].check_availability.assert_called_once_with(
            "us-east-1", "t2.micro"
        )

    def test_check_availability_all_providers(self, mock_checkers):
        """Test checking availability across all providers."""
        from sentinel.capacity.checker import CapacityResult

        # Mock responses from all providers
        aws_result = CapacityResult(
            region="us-east-1",
            resource_type="t2.micro",
            available=True,
            capacity_level=0.8,
            last_checked=datetime.now(UTC),
        )
        gcp_result = CapacityResult(
            region="us-central1",
            resource_type="f1-micro",
            available=False,
            capacity_level=0.0,
            last_checked=datetime.now(UTC),
        )
        azure_result = CapacityResult(
            region="eastus",
            resource_type="Standard_B1s",
            available=True,
            capacity_level=0.9,
            last_checked=datetime.now(UTC),
        )

        mock_checkers["aws"].check_availability.return_value = aws_result
        mock_checkers["gcp"].check_availability.return_value = gcp_result
        mock_checkers["azure"].check_availability.return_value = azure_result

        cache = CapacityCache(ttl_seconds=300)
        aggregator = CapacityAggregator(mock_checkers, cache)

        results = aggregator.check_availability_all_providers(
            [
                ("aws", "us-east-1", "t2.micro"),
                ("gcp", "us-central1", "f1-micro"),
                ("azure", "eastus", "Standard_B1s"),
            ]
        )

        assert len(results) == 3

        # Sort results by region to ensure consistent ordering for assertions
        results_by_region = {result.region: result for result in results}

        assert "us-east-1" in results_by_region
        assert "us-central1" in results_by_region
        assert "eastus" in results_by_region

        assert results_by_region["us-east-1"].available is True  # AWS
        assert results_by_region["us-central1"].available is False  # GCP
        assert results_by_region["eastus"].available is True  # Azure

    def test_capacity_aware_filtering(self, mock_checkers):
        """Test filtering resources based on capacity availability."""
        from sentinel.capacity.checker import CapacityResult

        # Mock mixed availability results
        available_result = CapacityResult(
            region="us-east-1",
            resource_type="t2.micro",
            available=True,
            capacity_level=0.8,
            last_checked=datetime.now(UTC),
        )
        unavailable_result = CapacityResult(
            region="us-west-2",
            resource_type="t2.micro",
            available=False,
            capacity_level=0.0,
            last_checked=datetime.now(UTC),
        )

        def mock_check_availability(region, resource_type):
            if region == "us-east-1":
                return available_result
            else:
                return unavailable_result

        mock_checkers["aws"].check_availability.side_effect = mock_check_availability

        cache = CapacityCache(ttl_seconds=300)
        aggregator = CapacityAggregator(mock_checkers, cache)

        # Test filtering resources
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100,
            ),
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-west-2",
                quantity=1,
                estimated_monthly_usage=100,
            ),
        ]

        available_resources = aggregator.filter_available_resources(resources)

        assert len(available_resources) == 1
        assert available_resources[0].region == "us-east-1"

    def test_cache_integration(self, mock_checkers):
        """Test that aggregator properly uses cache."""
        from sentinel.capacity.checker import CapacityResult

        mock_result = CapacityResult(
            region="us-east-1",
            resource_type="t2.micro",
            available=True,
            capacity_level=0.8,
            last_checked=datetime.now(UTC),
        )
        mock_checkers["aws"].check_availability.return_value = mock_result

        cache = CapacityCache(ttl_seconds=300)
        aggregator = CapacityAggregator(mock_checkers, cache)

        # First call should hit the API
        result1 = aggregator.check_availability("aws", "us-east-1", "t2.micro")
        assert mock_checkers["aws"].check_availability.call_count == 1

        # Second call should use cache
        result2 = aggregator.check_availability("aws", "us-east-1", "t2.micro")
        assert (
            mock_checkers["aws"].check_availability.call_count == 1
        )  # No additional call

        assert result1.available == result2.available
