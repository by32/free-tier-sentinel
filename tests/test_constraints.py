"""Test constraint database loading and validation using TDD approach."""

from decimal import Decimal
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from sentinel.constraints.loader import ConstraintLoader
from sentinel.constraints.query import ConstraintQuery
from sentinel.constraints.validator import ConstraintValidator
from sentinel.models.core import Constraint


class TestConstraintValidator:
    """Test constraint schema validation."""

    def test_valid_constraint_yaml_passes_validation(self):
        """Test that valid YAML constraint data passes validation."""
        valid_yaml_content = """
        version: "1.0"
        provider: aws
        constraints:
          - service: ec2
            resource_type: t2.micro
            region: "*"
            limit_type: free_tier_hours
            limit_value: 750
            period: monthly
            currency: USD
            cost_per_unit: "0.00"
            description: "Free tier EC2 t2.micro instances"
        """

        validator = ConstraintValidator()
        result = validator.validate_yaml(valid_yaml_content)

        assert result.is_valid is True
        assert len(result.errors) == 0
        assert result.data["provider"] == "aws"
        assert len(result.data["constraints"]) == 1

    def test_invalid_yaml_structure_fails_validation(self):
        """Test that invalid YAML structure fails validation."""
        invalid_yaml_content = """
        provider: aws
        # Missing required version field
        constraints:
          - service: ec2
            # Missing required fields
        """

        validator = ConstraintValidator()
        result = validator.validate_yaml(invalid_yaml_content)

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "version" in str(result.errors).lower()

    def test_negative_limit_value_fails_validation(self):
        """Test that negative limit values fail validation."""
        invalid_yaml_content = """
        version: "1.0"
        provider: aws
        constraints:
          - service: ec2
            resource_type: t2.micro
            region: us-east-1
            limit_type: free_tier_hours
            limit_value: -100  # Invalid negative value
            period: monthly
            currency: USD
            cost_per_unit: "0.00"
        """

        validator = ConstraintValidator()
        result = validator.validate_yaml(invalid_yaml_content)

        assert result.is_valid is False
        assert "negative" in str(result.errors).lower() or "positive" in str(result.errors).lower()

    def test_invalid_provider_name_fails_validation(self):
        """Test that invalid provider names fail validation."""
        invalid_yaml_content = """
        version: "1.0"
        provider: "invalid-provider"  # Not in allowed list
        constraints:
          - service: ec2
            resource_type: t2.micro
            region: us-east-1
            limit_type: free_tier_hours
            limit_value: 750
            period: monthly
            currency: USD
            cost_per_unit: "0.00"
        """

        validator = ConstraintValidator()
        result = validator.validate_yaml(invalid_yaml_content)

        assert result.is_valid is False
        assert "provider" in str(result.errors).lower()


class TestConstraintLoader:
    """Test constraint loading functionality."""

    def test_load_constraints_from_file(self):
        """Test loading constraints from a YAML file."""
        yaml_content = """
        version: "1.0"
        provider: aws
        constraints:
          - service: ec2
            resource_type: t2.micro
            region: "*"
            limit_type: free_tier_hours
            limit_value: 750
            period: monthly
            currency: USD
            cost_per_unit: "0.00"
            description: "Free tier EC2 t2.micro instances"
          - service: s3
            resource_type: standard_storage
            region: "*"
            limit_type: free_tier_gb
            limit_value: 5
            period: monthly
            currency: USD
            cost_per_unit: "0.00"
            description: "Free tier S3 standard storage"
        """

        loader = ConstraintLoader()

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            constraints = loader.load_from_file("fake_file.yaml")

        assert len(constraints) == 2
        assert all(isinstance(c, Constraint) for c in constraints)
        assert constraints[0].service == "ec2"
        assert constraints[0].limit_value == 750
        assert constraints[1].service == "s3"
        assert constraints[1].limit_value == 5

    def test_load_constraints_from_directory(self):
        """Test loading all constraint files from a directory."""
        loader = ConstraintLoader()

        # Mock multiple YAML files in a directory
        aws_content = """
        version: "1.0"
        provider: aws
        constraints:
          - service: ec2
            resource_type: t2.micro
            region: "*"
            limit_type: free_tier_hours
            limit_value: 750
            period: monthly
            currency: USD
            cost_per_unit: "0.00"
        """

        gcp_content = """
        version: "1.0"
        provider: gcp
        constraints:
          - service: compute
            resource_type: f1-micro
            region: "*"
            limit_type: free_tier_hours
            limit_value: 744
            period: monthly
            currency: USD
            cost_per_unit: "0.00"
        """

        with patch("pathlib.Path.glob") as mock_glob, \
             patch("builtins.open", mock_open()) as mock_file:

            # Mock directory structure
            mock_glob.return_value = [Path("aws.yaml"), Path("gcp.yaml")]

            # Mock file contents
            mock_file.return_value.read.side_effect = [aws_content, gcp_content]

            constraints = loader.load_from_directory("constraints/")

        assert len(constraints) == 2
        providers = {c.provider for c in constraints}
        assert providers == {"aws", "gcp"}

    def test_load_invalid_file_raises_error(self):
        """Test that loading invalid files raises appropriate errors."""
        invalid_yaml = "invalid: yaml: content: ["

        loader = ConstraintLoader()

        with patch("builtins.open", mock_open(read_data=invalid_yaml)):
            with pytest.raises(ValueError, match="Failed to parse YAML"):
                loader.load_from_file("invalid.yaml")

    def test_load_nonexistent_file_raises_error(self):
        """Test that loading non-existent files raises appropriate errors."""
        loader = ConstraintLoader()

        with pytest.raises(FileNotFoundError):
            loader.load_from_file("nonexistent.yaml")


class TestConstraintQuery:
    """Test constraint querying functionality."""

    @pytest.fixture
    def sample_constraints(self):
        """Provide sample constraints for testing."""
        return [
            Constraint(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                limit_type="free_tier_hours",
                limit_value=750,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            ),
            Constraint(
                provider="aws",
                service="ec2",
                resource_type="t2.small",
                region="us-east-1",
                limit_type="standard_hours",
                limit_value=0,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.023")
            ),
            Constraint(
                provider="gcp",
                service="compute",
                resource_type="f1-micro",
                region="us-central1",
                limit_type="free_tier_hours",
                limit_value=744,
                period="monthly",
                currency="USD",
                cost_per_unit=Decimal("0.00")
            )
        ]

    def test_query_by_provider(self, sample_constraints):
        """Test querying constraints by provider."""
        query = ConstraintQuery(sample_constraints)

        aws_constraints = query.by_provider("aws")

        assert len(aws_constraints) == 2
        assert all(c.provider == "aws" for c in aws_constraints)

    def test_query_by_service(self, sample_constraints):
        """Test querying constraints by service."""
        query = ConstraintQuery(sample_constraints)

        ec2_constraints = query.by_service("ec2")

        assert len(ec2_constraints) == 2
        assert all(c.service == "ec2" for c in ec2_constraints)

    def test_query_by_resource_type(self, sample_constraints):
        """Test querying constraints by resource type."""
        query = ConstraintQuery(sample_constraints)

        micro_constraints = query.by_resource_type("t2.micro")

        assert len(micro_constraints) == 1
        assert micro_constraints[0].resource_type == "t2.micro"

    def test_query_free_tier_only(self, sample_constraints):
        """Test querying only free tier constraints."""
        query = ConstraintQuery(sample_constraints)

        free_tier = query.free_tier_only()

        assert len(free_tier) == 2
        assert all(c.is_free_tier() for c in free_tier)

    def test_query_by_region(self, sample_constraints):
        """Test querying constraints by region."""
        query = ConstraintQuery(sample_constraints)

        us_east_constraints = query.by_region("us-east-1")

        assert len(us_east_constraints) == 2
        assert all(c.region == "us-east-1" for c in us_east_constraints)

    def test_chained_queries(self, sample_constraints):
        """Test chaining multiple query filters."""
        query = ConstraintQuery(sample_constraints)

        result = query.by_provider("aws").by_service("ec2").free_tier_only()

        assert len(result) == 1
        assert result[0].provider == "aws"
        assert result[0].service == "ec2"
        assert result[0].is_free_tier()

    def test_query_returns_empty_for_no_matches(self, sample_constraints):
        """Test that queries return empty list when no matches found."""
        query = ConstraintQuery(sample_constraints)

        result = query.by_provider("azure")

        assert len(result) == 0
        assert result == []
