"""Test provisioning engine using TDD approach."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, patch
from decimal import Decimal
from enum import Enum

from sentinel.models.core import Resource, Plan


class TestProvisioningInterface:
    """Test provisioning engine interface and state management."""

    def test_provisioning_engine_interface(self):
        """Test that provisioning engine defines the required interface."""
        from sentinel.provisioning.engine import ProvisioningEngine
        
        # Test that we can't instantiate abstract class
        with pytest.raises(TypeError):
            ProvisioningEngine()
        
        # Test that subclass must implement abstract methods
        class IncompleteEngine(ProvisioningEngine):
            pass
        
        with pytest.raises(TypeError):
            IncompleteEngine()

    def test_provisioning_state_enumeration(self):
        """Test provisioning state enumeration."""
        from sentinel.provisioning.engine import ProvisioningState
        
        # Test all required states exist
        assert ProvisioningState.PENDING
        assert ProvisioningState.PROVISIONING
        assert ProvisioningState.READY
        assert ProvisioningState.FAILED
        assert ProvisioningState.ROLLBACK

    def test_provisioning_result_data_structure(self):
        """Test the provisioning result data structure."""
        from sentinel.provisioning.engine import ProvisioningResult, ProvisioningState
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        result = ProvisioningResult(
            resource=resource,
            state=ProvisioningState.READY,
            resource_id="i-1234567890abcdef0",
            provisioned_at=datetime.now(UTC),
            provider_specific_data={"instance_id": "i-1234567890abcdef0", "vpc_id": "vpc-12345"}
        )
        
        assert result.resource == resource
        assert result.state == ProvisioningState.READY
        assert result.resource_id == "i-1234567890abcdef0"
        assert isinstance(result.provisioned_at, datetime)
        assert "instance_id" in result.provider_specific_data

    def test_provisioning_plan_result(self):
        """Test the provisioning plan result structure."""
        from sentinel.provisioning.engine import ProvisioningPlanResult, ProvisioningState
        
        plan = Plan(
            name="test-plan",
            description="Test deployment plan",
            resources=[]
        )
        
        plan_result = ProvisioningPlanResult(
            plan=plan,
            state=ProvisioningState.PROVISIONING,
            started_at=datetime.now(UTC),
            resource_results=[],
            deployment_id="deploy-123"
        )
        
        assert plan_result.plan == plan
        assert plan_result.state == ProvisioningState.PROVISIONING
        assert plan_result.deployment_id == "deploy-123"
        assert isinstance(plan_result.started_at, datetime)

    def test_provisioning_error_handling(self):
        """Test provisioning error data structure."""
        from sentinel.provisioning.engine import ProvisioningError
        
        error = ProvisioningError(
            resource_type="t2.micro",
            provider="aws",
            error_type="CAPACITY_EXCEEDED",
            error_message="Insufficient capacity for t2.micro in us-east-1a",
            retry_after=timedelta(minutes=5),
            retry_suggested=True
        )
        
        assert error.resource_type == "t2.micro"
        assert error.provider == "aws"
        assert error.error_type == "CAPACITY_EXCEEDED"
        assert error.retry_suggested is True
        assert error.retry_after == timedelta(minutes=5)


class TestProvisioningEngineImplementation:
    """Test concrete provisioning engine implementation."""

    @pytest.fixture
    def sample_resources(self):
        """Provide sample resources for testing."""
        return [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100
            ),
            Resource(
                provider="aws",
                service="s3",
                resource_type="standard_storage",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=5  # 5 GB
            )
        ]

    @pytest.fixture
    def sample_plan(self, sample_resources):
        """Provide a sample deployment plan."""
        return Plan(
            name="test-deployment",
            description="Test deployment plan",
            resources=sample_resources
        )

    def test_provisioning_engine_creation(self):
        """Test creating a provisioning engine."""
        from sentinel.provisioning.engine import DefaultProvisioningEngine
        
        engine = DefaultProvisioningEngine()
        
        assert engine is not None
        assert hasattr(engine, 'provision_resource')
        assert hasattr(engine, 'provision_plan')
        assert hasattr(engine, 'get_provisioning_status')

    def test_provision_single_resource_success(self, sample_resources):
        """Test successfully provisioning a single resource."""
        from sentinel.provisioning.engine import DefaultProvisioningEngine, ProvisioningState
        
        engine = DefaultProvisioningEngine()
        resource = sample_resources[0]  # t2.micro
        
        result = engine.provision_resource(resource)
        
        assert result.resource == resource
        assert result.state == ProvisioningState.READY
        assert result.resource_id is not None
        assert result.provisioned_at is not None
        assert "provider" in result.provider_specific_data

    def test_provision_single_resource_failure(self, sample_resources):
        """Test handling provisioning failure for a single resource."""
        from sentinel.provisioning.engine import DefaultProvisioningEngine, ProvisioningState
        
        engine = DefaultProvisioningEngine()
        
        # Mock a resource that will fail (non-existent instance type)
        failing_resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="nonexistent.type",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        result = engine.provision_resource(failing_resource)
        
        assert result.resource == failing_resource
        assert result.state == ProvisioningState.FAILED
        assert result.error is not None
        assert result.error.error_type in ["INVALID_INSTANCE_TYPE", "VALIDATION_ERROR"]

    def test_provision_plan_success(self, sample_plan):
        """Test successfully provisioning a complete plan."""
        from sentinel.provisioning.engine import DefaultProvisioningEngine, ProvisioningState
        
        engine = DefaultProvisioningEngine()
        
        plan_result = engine.provision_plan(sample_plan)
        
        assert plan_result.plan == sample_plan
        assert plan_result.state == ProvisioningState.READY
        assert len(plan_result.resource_results) == len(sample_plan.resources)
        assert plan_result.deployment_id is not None
        assert plan_result.completed_at is not None
        
        # All resources should be successfully provisioned
        for resource_result in plan_result.resource_results:
            assert resource_result.state == ProvisioningState.READY

    def test_provision_plan_partial_failure(self, sample_resources):
        """Test handling partial failure when provisioning a plan."""
        from sentinel.provisioning.engine import DefaultProvisioningEngine, ProvisioningState
        
        engine = DefaultProvisioningEngine()
        
        # Create a plan with one good and one bad resource
        mixed_resources = sample_resources + [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="nonexistent.type",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100
            )
        ]
        
        mixed_plan = Plan(
            name="mixed-plan",
            description="Plan with good and bad resources",
            resources=mixed_resources
        )
        
        plan_result = engine.provision_plan(mixed_plan)
        
        assert plan_result.state == ProvisioningState.FAILED
        assert len(plan_result.resource_results) == len(mixed_resources)
        
        # Should have both successful and failed resources
        successful_results = [r for r in plan_result.resource_results if r.state == ProvisioningState.READY]
        failed_results = [r for r in plan_result.resource_results if r.state == ProvisioningState.FAILED]
        
        assert len(successful_results) > 0
        assert len(failed_results) > 0

    def test_get_provisioning_status(self, sample_plan):
        """Test getting provisioning status for a deployment."""
        from sentinel.provisioning.engine import DefaultProvisioningEngine, ProvisioningState
        
        engine = DefaultProvisioningEngine()
        
        # Start provisioning
        plan_result = engine.provision_plan(sample_plan)
        deployment_id = plan_result.deployment_id
        
        # Check status
        status = engine.get_provisioning_status(deployment_id)
        
        assert status is not None
        assert status.deployment_id == deployment_id
        assert status.plan == sample_plan
        assert status.state in [ProvisioningState.PROVISIONING, ProvisioningState.READY]


class TestRetryMechanisms:
    """Test retry logic and failure handling."""

    def test_retry_configuration(self):
        """Test retry configuration options."""
        from sentinel.provisioning.retry import RetryConfig
        
        config = RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_retry_policy_creation(self):
        """Test creating retry policies for different scenarios."""
        from sentinel.provisioning.retry import RetryPolicy, RetryConfig
        
        config = RetryConfig(max_attempts=3, base_delay=1.0)
        policy = RetryPolicy(config)
        
        assert policy.config == config
        assert hasattr(policy, 'should_retry')
        assert hasattr(policy, 'get_delay')

    def test_retry_exponential_backoff(self):
        """Test exponential backoff calculation."""
        from sentinel.provisioning.retry import RetryPolicy, RetryConfig
        
        config = RetryConfig(
            max_attempts=5,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False  # Disable jitter for predictable testing
        )
        policy = RetryPolicy(config)
        
        # Test delay calculation for multiple attempts
        delays = []
        for attempt in range(1, 5):
            delay = policy.get_delay(attempt)
            delays.append(delay)
        
        # Should follow exponential backoff: 1, 2, 4, 8
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0
        assert delays[3] == 8.0

    def test_retry_with_capacity_failures(self):
        """Test retry behavior for capacity-related failures."""
        from sentinel.provisioning.retry import RetryPolicy, RetryConfig
        from sentinel.provisioning.engine import ProvisioningError
        
        config = RetryConfig(max_attempts=3)
        policy = RetryPolicy(config)
        
        # Capacity failure should be retryable
        capacity_error = ProvisioningError(
            resource_type="t2.micro",
            provider="aws",
            error_type="CAPACITY_EXCEEDED",
            error_message="Insufficient capacity",
            retry_suggested=True
        )
        
        assert policy.should_retry(capacity_error, attempt=1) is True
        
        # Validation error should not be retryable
        validation_error = ProvisioningError(
            resource_type="invalid.type",
            provider="aws",
            error_type="VALIDATION_ERROR",
            error_message="Invalid instance type",
            retry_suggested=False
        )
        
        assert policy.should_retry(validation_error, attempt=1) is False

    def test_retry_max_attempts(self):
        """Test that retry stops after max attempts."""
        from sentinel.provisioning.retry import RetryPolicy, RetryConfig
        from sentinel.provisioning.engine import ProvisioningError
        
        config = RetryConfig(max_attempts=3)
        policy = RetryPolicy(config)
        
        capacity_error = ProvisioningError(
            resource_type="t2.micro",
            provider="aws",
            error_type="CAPACITY_EXCEEDED",
            error_message="Insufficient capacity",
            retry_suggested=True
        )
        
        # Should retry for attempts 1 and 2
        assert policy.should_retry(capacity_error, attempt=1) is True
        assert policy.should_retry(capacity_error, attempt=2) is True
        
        # Should not retry after max attempts
        assert policy.should_retry(capacity_error, attempt=3) is False


class TestAWSProvisioningAdapter:
    """Test AWS-specific provisioning logic."""

    def test_aws_adapter_creation(self):
        """Test creating an AWS provisioning adapter."""
        from sentinel.provisioning.adapters.aws import AWSProvisioningAdapter
        
        adapter = AWSProvisioningAdapter()
        
        assert adapter.provider == "aws"
        assert hasattr(adapter, 'provision_ec2_instance')
        assert hasattr(adapter, 'provision_s3_bucket')
        assert hasattr(adapter, 'get_resource_status')

    def test_aws_ec2_provisioning(self):
        """Test provisioning an EC2 instance."""
        from sentinel.provisioning.adapters.aws import AWSProvisioningAdapter
        from sentinel.provisioning.engine import ProvisioningState
        
        adapter = AWSProvisioningAdapter()
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        result = adapter.provision_resource(resource)
        
        assert result.resource == resource
        assert result.state == ProvisioningState.READY
        assert result.resource_id.startswith("i-")  # EC2 instance ID format
        assert "instance_id" in result.provider_specific_data

    def test_aws_s3_provisioning(self):
        """Test provisioning an S3 bucket."""
        from sentinel.provisioning.adapters.aws import AWSProvisioningAdapter
        from sentinel.provisioning.engine import ProvisioningState
        
        adapter = AWSProvisioningAdapter()
        
        resource = Resource(
            provider="aws",
            service="s3",
            resource_type="standard_storage",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=5
        )
        
        result = adapter.provision_resource(resource)
        
        assert result.resource == resource
        assert result.state == ProvisioningState.READY
        assert result.resource_id.endswith("-bucket")  # S3 bucket naming
        assert "bucket_name" in result.provider_specific_data

    @patch('sentinel.capacity.aws_checker.boto3.client')
    def test_aws_provisioning_with_capacity_integration(self, mock_boto_client):
        """Test AWS provisioning with capacity checking integration."""
        from sentinel.provisioning.adapters.aws import AWSProvisioningAdapter
        from sentinel.capacity.aggregator import CapacityAggregator
        from sentinel.capacity.cache import CapacityCache
        from sentinel.capacity.aws_checker import AWSCapacityChecker
        
        # Mock AWS API responses
        mock_ec2 = Mock()
        mock_boto_client.return_value = mock_ec2
        
        # Mock availability zones response
        mock_ec2.describe_availability_zones.return_value = {
            "AvailabilityZones": [
                {"ZoneName": "us-east-1a"},
                {"ZoneName": "us-east-1b"}
            ]
        }
        
        # Mock instance type offerings response
        mock_ec2.describe_instance_type_offerings.return_value = {
            "InstanceTypeOfferings": [
                {"InstanceType": "t2.micro", "Location": "us-east-1a"}
            ]
        }
        
        # Setup capacity checking
        checkers = {"aws": AWSCapacityChecker()}
        cache = CapacityCache(ttl_seconds=300)
        capacity_aggregator = CapacityAggregator(checkers, cache)
        
        # Create adapter with capacity integration
        adapter = AWSProvisioningAdapter(capacity_aggregator=capacity_aggregator)
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        result = adapter.provision_resource(resource)
        
        # Should check capacity before provisioning
        assert result is not None
        # Capacity check should be reflected in the result
        assert hasattr(result, 'capacity_checked')
        assert result.capacity_checked is True