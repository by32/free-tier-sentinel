"""Constraint loading functionality."""

from decimal import Decimal
from pathlib import Path

from sentinel.constraints.validator import ConstraintValidator
from sentinel.models.core import Constraint


class ConstraintLoader:
    """Loads constraint data from YAML files."""

    def __init__(self):
        """Initialize loader with validator."""
        self.validator = ConstraintValidator()

    def load_from_file(self, file_path: str) -> list[Constraint]:
        """Load constraints from a single YAML file."""
        try:
            # Read file content
            with open(file_path, encoding='utf-8') as file:
                content = file.read()

            # Validate content
            validation_result = self.validator.validate_yaml(content)
            if not validation_result.is_valid:
                raise ValueError(f"Failed to parse YAML: {validation_result.errors}")

            # Convert to Constraint objects
            data = validation_result.data
            constraints = []

            for constraint_data in data["constraints"]:
                constraint = Constraint(
                    provider=data["provider"],
                    service=constraint_data["service"],
                    resource_type=constraint_data["resource_type"],
                    region=constraint_data["region"],
                    limit_type=constraint_data["limit_type"],
                    limit_value=constraint_data["limit_value"],
                    period=constraint_data["period"],
                    currency=constraint_data["currency"],
                    cost_per_unit=Decimal(str(constraint_data["cost_per_unit"]))
                )
                constraints.append(constraint)

            return constraints

        except FileNotFoundError as e:
            raise FileNotFoundError(f"Constraint file not found: {file_path}") from e
        except Exception as e:
            raise ValueError(f"Failed to parse YAML: {str(e)}") from e

    def load_from_directory(self, directory_path: str) -> list[Constraint]:
        """Load constraints from all YAML files in a directory."""
        directory = Path(directory_path)
        all_constraints = []

        # Find all YAML files in directory
        yaml_files = directory.glob("*.yaml")

        for yaml_file in yaml_files:
            constraints = self.load_from_file(str(yaml_file))
            all_constraints.extend(constraints)

        return all_constraints
