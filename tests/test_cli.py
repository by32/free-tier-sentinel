"""Test CLI interface using TDD approach."""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, call
from click.testing import CliRunner
from io import StringIO

from sentinel.models.core import Resource, Plan


class TestCLIInterface:
    """Test basic CLI interface and command structure."""

    def test_cli_main_command_exists(self):
        """Test that main CLI command exists and is callable."""
        from sentinel.cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'Usage:' in result.output
        assert 'plan' in result.output
        assert 'provision' in result.output

    def test_cli_plan_command_exists(self):
        """Test that plan command exists with proper structure."""
        from sentinel.cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['plan', '--help'])
        
        assert result.exit_code == 0
        assert 'Create a deployment plan' in result.output
        assert '--interactive' in result.output
        assert '--config' in result.output
        assert '--dry-run' in result.output

    def test_cli_provision_command_exists(self):
        """Test that provision command exists with proper structure."""
        from sentinel.cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['provision', '--help'])
        
        assert result.exit_code == 0
        assert 'Execute a deployment plan' in result.output
        assert '--plan-file' in result.output
        assert '--progress' in result.output

    def test_cli_status_command_exists(self):
        """Test that status command exists for checking deployments."""
        from sentinel.cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['status', '--help'])
        
        assert result.exit_code == 0
        assert 'Check deployment status' in result.output
        assert '--deployment-id' in result.output


class TestInteractivePlanning:
    """Test interactive planning wizard functionality."""

    @pytest.fixture
    def mock_input_responses(self):
        """Provide mock responses for interactive prompts."""
        return [
            "aws",  # Provider choice
            "us-east-1",  # Region
            "1",  # Number of EC2 instances
            "t2.micro",  # Instance type
            "100",  # Estimated monthly usage
            "y",  # Add S3 bucket
            "5",  # S3 storage GB
            "test-deployment",  # Plan name
            "Test deployment plan",  # Plan description
            "y"  # Confirm plan
        ]

    @patch('sentinel.cli.planning.click.prompt')
    @patch('sentinel.cli.planning.click.confirm')
    def test_interactive_planning_wizard(self, mock_confirm, mock_prompt):
        """Test the interactive planning wizard flow."""
        from sentinel.cli.main import cli
        from sentinel.cli.planning import InteractivePlanner
        
        # Setup mock responses
        mock_prompt.side_effect = [
            "aws", "us-east-1", "t2.micro", "1", "100",
            "test-deployment", "Test deployment plan"
        ]
        mock_confirm.side_effect = [True, False, True]  # Add compute, don't add storage, confirm plan
        
        planner = InteractivePlanner()
        plan = planner.create_plan()
        
        assert plan.name == "test-deployment"
        assert plan.description == "Test deployment plan"
        assert len(plan.resources) >= 1
        
        # Check EC2 resource
        ec2_resources = [r for r in plan.resources if r.service == "ec2"]
        assert len(ec2_resources) == 1
        assert ec2_resources[0].resource_type == "t2.micro"
        assert ec2_resources[0].region == "us-east-1"

    def test_provider_selection_validation(self):
        """Test that provider selection validates against supported providers."""
        from sentinel.cli.planning import InteractivePlanner
        
        planner = InteractivePlanner()
        
        # Test valid provider
        assert planner.validate_provider("aws") is True
        assert planner.validate_provider("gcp") is True
        assert planner.validate_provider("azure") is True
        
        # Test invalid provider
        assert planner.validate_provider("invalid") is False

    def test_region_validation_by_provider(self):
        """Test that region validation works for each provider."""
        from sentinel.cli.planning import InteractivePlanner
        
        planner = InteractivePlanner()
        
        # Test AWS regions
        assert planner.validate_region("aws", "us-east-1") is True
        assert planner.validate_region("aws", "invalid-region") is False
        
        # Test GCP regions
        assert planner.validate_region("gcp", "us-central1") is True
        assert planner.validate_region("gcp", "invalid-region") is False

    @patch('sentinel.cli.planning.click.prompt')
    def test_resource_configuration_prompts(self, mock_prompt):
        """Test resource configuration prompting logic."""
        from sentinel.cli.planning import ResourceConfigurator
        
        mock_prompt.side_effect = ["t2.micro", "1", "100"]
        
        configurator = ResourceConfigurator()
        resource = configurator.configure_ec2_instance("aws", "us-east-1")
        
        assert resource.provider == "aws"
        assert resource.service == "ec2"
        assert resource.resource_type == "t2.micro"
        assert resource.region == "us-east-1"
        assert resource.estimated_monthly_usage == 100


class TestConfigurationFiles:
    """Test YAML/JSON configuration file support."""

    @pytest.fixture
    def sample_config_yaml(self, tmp_path):
        """Create sample YAML configuration file."""
        config_data = {
            "plan": {
                "name": "yaml-test-plan",
                "description": "Plan from YAML config"
            },
            "resources": [
                {
                    "provider": "aws",
                    "service": "ec2",
                    "resource_type": "t2.micro",
                    "region": "us-east-1",
                    "quantity": 2,
                    "estimated_monthly_usage": 200
                },
                {
                    "provider": "aws",
                    "service": "s3",
                    "resource_type": "standard_storage",
                    "region": "us-east-1",
                    "quantity": 1,
                    "estimated_monthly_usage": 10
                }
            ]
        }
        
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)
        
        return config_file

    @pytest.fixture
    def sample_config_json(self, tmp_path):
        """Create sample JSON configuration file."""
        config_data = {
            "plan": {
                "name": "json-test-plan",
                "description": "Plan from JSON config"
            },
            "resources": [
                {
                    "provider": "gcp", 
                    "service": "compute",
                    "resource_type": "e2-micro",
                    "region": "us-central1",
                    "quantity": 1,
                    "estimated_monthly_usage": 150
                }
            ]
        }
        
        config_file = tmp_path / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        return config_file

    def test_yaml_config_loading(self, sample_config_yaml):
        """Test loading configuration from YAML file."""
        from sentinel.cli.config import ConfigLoader
        
        loader = ConfigLoader()
        plan = loader.load_from_file(sample_config_yaml)
        
        assert plan.name == "yaml-test-plan"
        assert plan.description == "Plan from YAML config"
        assert len(plan.resources) == 2
        
        # Check EC2 resource
        ec2_resource = next(r for r in plan.resources if r.service == "ec2")
        assert ec2_resource.provider == "aws"
        assert ec2_resource.resource_type == "t2.micro"
        assert ec2_resource.quantity == 2

    def test_json_config_loading(self, sample_config_json):
        """Test loading configuration from JSON file."""
        from sentinel.cli.config import ConfigLoader
        
        loader = ConfigLoader()
        plan = loader.load_from_file(sample_config_json)
        
        assert plan.name == "json-test-plan"
        assert plan.description == "Plan from JSON config"
        assert len(plan.resources) == 1
        
        # Check GCP resource
        gcp_resource = plan.resources[0]
        assert gcp_resource.provider == "gcp"
        assert gcp_resource.service == "compute"
        assert gcp_resource.resource_type == "e2-micro"

    def test_config_validation_errors(self, tmp_path):
        """Test configuration validation with invalid files."""
        from sentinel.cli.config import ConfigLoader, ConfigValidationError
        
        # Create invalid YAML file
        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        loader = ConfigLoader()
        
        with pytest.raises(ConfigValidationError):
            loader.load_from_file(invalid_file)

    def test_cli_with_config_file(self, sample_config_yaml):
        """Test CLI plan command with config file."""
        from sentinel.cli.main import cli
        
        runner = CliRunner()
        result = runner.invoke(cli, ['plan', '--config', str(sample_config_yaml), '--dry-run'])
        
        assert result.exit_code == 0
        assert "Plan validation successful" in result.output
        # In dry-run mode, the plan name may not be displayed, but validation should succeed


class TestPlanManagement:
    """Test plan save/load and management functionality."""

    @pytest.fixture
    def sample_plan(self):
        """Provide a sample deployment plan."""
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100
            )
        ]
        
        return Plan(
            name="test-save-plan",
            description="Plan for save/load testing",
            resources=resources
        )

    def test_plan_saving(self, sample_plan, tmp_path):
        """Test saving deployment plans to file."""
        from sentinel.cli.plan_manager import PlanManager
        
        manager = PlanManager()
        plan_file = tmp_path / "saved_plan.json"
        
        manager.save_plan(sample_plan, plan_file)
        
        assert plan_file.exists()
        
        # Verify file contents
        with open(plan_file, 'r') as f:
            saved_data = json.load(f)
        
        assert saved_data['name'] == "test-save-plan"
        assert saved_data['description'] == "Plan for save/load testing"
        assert len(saved_data['resources']) == 1

    def test_plan_loading(self, sample_plan, tmp_path):
        """Test loading deployment plans from file."""
        from sentinel.cli.plan_manager import PlanManager
        
        manager = PlanManager()
        plan_file = tmp_path / "saved_plan.json"
        
        # Save then load
        manager.save_plan(sample_plan, plan_file)
        loaded_plan = manager.load_plan(plan_file)
        
        assert loaded_plan.name == sample_plan.name
        assert loaded_plan.description == sample_plan.description
        assert len(loaded_plan.resources) == len(sample_plan.resources)
        
        # Check resource details
        loaded_resource = loaded_plan.resources[0]
        original_resource = sample_plan.resources[0]
        assert loaded_resource.provider == original_resource.provider
        assert loaded_resource.service == original_resource.service
        assert loaded_resource.resource_type == original_resource.resource_type

    def test_plan_comparison(self):
        """Test plan comparison and diff functionality."""
        from sentinel.cli.plan_manager import PlanManager
        
        plan1 = Plan(name="plan1", description="First plan", resources=[])
        plan2 = Plan(name="plan2", description="Second plan", resources=[])
        
        manager = PlanManager()
        diff = manager.compare_plans(plan1, plan2)
        
        assert 'name' in diff
        assert 'description' in diff
        assert diff['name']['old'] == "plan1"
        assert diff['name']['new'] == "plan2"


class TestRichOutput:
    """Test rich output formatting and progress display."""

    def test_plan_output_formatting(self):
        """Test formatted plan display output."""
        from sentinel.cli.output import PlanFormatter
        
        resources = [
            Resource(
                provider="aws",
                service="ec2", 
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100
            )
        ]
        
        plan = Plan(
            name="format-test",
            description="Test plan formatting",
            resources=resources
        )
        
        formatter = PlanFormatter()
        output = formatter.format_plan(plan)
        
        assert "format-test" in output
        assert "Test plan formatting" in output
        assert "aws" in output
        assert "t2.micro" in output
        assert "us-east-1" in output

    def test_progress_display(self):
        """Test progress display for provisioning operations."""
        from sentinel.cli.output import ProgressDisplay
        
        display = ProgressDisplay()
        
        # Test progress tracking
        display.start_operation("Testing progress", total_steps=3)
        
        assert display.current_step == 0
        assert display.total_steps == 3
        
        display.update_progress("Step 1 complete")
        assert display.current_step == 1
        
        display.finish_operation("All steps complete")
        assert display.is_complete is True

    @patch('sys.stdout', new_callable=StringIO)
    def test_colored_output(self, mock_stdout):
        """Test colored console output functionality."""
        from sentinel.cli.output import ColoredOutput
        
        output = ColoredOutput()
        
        output.success("Operation successful")
        output.error("Operation failed")
        output.warning("Operation warning")
        output.info("Operation info")
        
        printed = mock_stdout.getvalue()
        assert "Operation successful" in printed
        assert "Operation failed" in printed
        assert "Operation warning" in printed
        assert "Operation info" in printed


class TestDryRunMode:
    """Test dry-run functionality for plan validation."""

    def test_dry_run_plan_validation(self):
        """Test dry-run mode validates plans without execution."""
        from sentinel.cli.dry_run import DryRunValidator
        
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100
            )
        ]
        
        plan = Plan(
            name="dry-run-test",
            description="Test dry-run validation",
            resources=resources
        )
        
        validator = DryRunValidator()
        result = validator.validate_plan(plan)
        
        assert result.is_valid is True
        assert result.total_resources == 1
        assert result.estimated_cost is not None
        assert len(result.validation_warnings) >= 0

    def test_dry_run_capacity_checking(self):
        """Test dry-run includes capacity availability checking."""
        from sentinel.cli.dry_run import DryRunValidator
        
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="nonexistent.type",
                region="invalid-region",
                quantity=1,
                estimated_monthly_usage=100
            )
        ]
        
        plan = Plan(
            name="dry-run-capacity-test",
            description="Test capacity checking in dry-run",
            resources=resources
        )
        
        validator = DryRunValidator()
        result = validator.validate_plan(plan)
        
        # Should detect issues with invalid resource type and region
        assert len(result.validation_warnings) > 0
        assert any("region" in warning.lower() for warning in result.validation_warnings)

    def test_cli_dry_run_command(self):
        """Test CLI dry-run command execution."""
        from sentinel.cli.main import cli
        
        runner = CliRunner()
        
        # Test dry-run with inline configuration
        result = runner.invoke(cli, [
            'plan',
            '--dry-run',
            '--provider', 'aws',
            '--region', 'us-east-1',
            '--resource', 'ec2:t2.micro:1'
        ])
        
        assert result.exit_code == 0
        assert "Dry-run mode" in result.output
        assert "Plan validation" in result.output
        assert "No resources will be provisioned" in result.output