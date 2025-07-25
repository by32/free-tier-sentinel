"""Integration tests for constraint loading with real files."""

from pathlib import Path

import pytest

from sentinel.constraints.loader import ConstraintLoader
from sentinel.constraints.query import ConstraintQuery


class TestConstraintIntegration:
    """Test constraint system with real constraint files."""

    def test_load_all_constraint_files(self):
        """Test loading all constraint files from constraints directory."""
        loader = ConstraintLoader()
        constraints_dir = Path(__file__).parent.parent / "constraints"

        # Skip if constraints directory doesn't exist
        if not constraints_dir.exists():
            pytest.skip("Constraints directory not found")

        constraints = loader.load_from_directory(str(constraints_dir))

        # Should have constraints from multiple providers
        assert len(constraints) > 0

        # Check that we have multiple providers
        providers = {c.provider for c in constraints}
        assert len(providers) >= 2  # At least AWS and GCP

        # All constraints should be valid Constraint objects
        assert all(hasattr(c, 'is_free_tier') for c in constraints)

    def test_query_real_constraints(self):
        """Test querying capabilities with real constraint data."""
        loader = ConstraintLoader()
        constraints_dir = Path(__file__).parent.parent / "constraints"

        if not constraints_dir.exists():
            pytest.skip("Constraints directory not found")

        constraints = loader.load_from_directory(str(constraints_dir))
        query = ConstraintQuery(constraints)

        # Test provider filtering
        aws_constraints = query.by_provider("aws")
        assert len(aws_constraints) > 0
        assert all(c.provider == "aws" for c in aws_constraints)

        # Test service filtering
        compute_constraints = query.by_service("compute").to_list()
        if compute_constraints:  # Only test if compute services exist
            assert all(c.service == "compute" for c in compute_constraints)

        # Test free tier filtering
        free_tier_constraints = query.free_tier_only()
        assert len(free_tier_constraints) > 0
        assert all(c.is_free_tier() for c in free_tier_constraints)

        # Test chained queries
        aws_free_tier = query.by_provider("aws").free_tier_only()
        assert len(aws_free_tier) > 0
        assert all(c.provider == "aws" and c.is_free_tier() for c in aws_free_tier)

    def test_constraint_data_quality(self):
        """Test that loaded constraint data meets quality standards."""
        loader = ConstraintLoader()
        constraints_dir = Path(__file__).parent.parent / "constraints"

        if not constraints_dir.exists():
            pytest.skip("Constraints directory not found")

        constraints = loader.load_from_directory(str(constraints_dir))

        for constraint in constraints:
            # All constraints should have positive limit values
            assert constraint.limit_value >= 0

            # All constraints should have valid periods
            assert constraint.period in ["monthly", "daily", "yearly"]

            # All constraints should have valid currencies
            assert constraint.currency in ["USD", "EUR", "GBP"]

            # Free tier constraints should have zero cost
            if constraint.is_free_tier():
                assert constraint.cost_per_unit.is_zero()

    def test_specific_provider_constraints(self):
        """Test specific provider constraint expectations."""
        loader = ConstraintLoader()
        constraints_dir = Path(__file__).parent.parent / "constraints"

        if not constraints_dir.exists():
            pytest.skip("Constraints directory not found")

        constraints = loader.load_from_directory(str(constraints_dir))
        query = ConstraintQuery(constraints)

        # AWS should have EC2 t2.micro free tier
        aws_ec2 = query.by_provider("aws").by_service("ec2").by_resource_type("t2.micro")
        if len(aws_ec2) > 0:
            ec2_constraint = aws_ec2[0]
            assert ec2_constraint.limit_value == 750  # 750 hours/month
            assert ec2_constraint.is_free_tier()

        # GCP should have f1-micro free tier
        gcp_compute = query.by_provider("gcp").by_service("compute").by_resource_type("f1-micro")
        if len(gcp_compute) > 0:
            f1_constraint = gcp_compute[0]
            assert f1_constraint.limit_value == 744  # 744 hours/month
            assert f1_constraint.is_free_tier()

        # Azure should have B1s free tier
        azure_compute = query.by_provider("azure").by_service("compute").by_resource_type("B1s")
        if len(azure_compute) > 0:
            b1s_constraint = azure_compute[0]
            assert b1s_constraint.limit_value == 750  # 750 hours/month
            assert b1s_constraint.is_free_tier()
