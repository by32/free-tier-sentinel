"""Constraint YAML validation functionality."""

from dataclasses import dataclass
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


@dataclass
class ValidationResult:
    """Result of constraint validation."""
    is_valid: bool
    errors: list[str]
    data: dict[str, Any] | None = None


class ConstraintSchema(BaseModel):
    """Schema for constraint YAML files."""

    version: str = Field(..., description="Schema version")
    provider: str = Field(..., description="Cloud provider name")
    constraints: list[dict[str, Any]] = Field(..., description="List of constraints")

    def model_post_init(self, __context: Any) -> None:
        """Validate provider and constraints after initialization."""
        # Validate provider is in allowed list
        allowed_providers = {"aws", "gcp", "azure", "oci"}
        if self.provider not in allowed_providers:
            raise ValueError(f"Provider must be one of {allowed_providers}")

        # Validate each constraint
        for constraint in self.constraints:
            self._validate_constraint(constraint)

    def _validate_constraint(self, constraint: dict[str, Any]) -> None:
        """Validate individual constraint data."""
        required_fields = {
            "service", "resource_type", "region", "limit_type",
            "limit_value", "period", "currency", "cost_per_unit"
        }

        missing_fields = required_fields - set(constraint.keys())
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Validate limit_value is positive
        if constraint.get("limit_value", 0) < 0:
            raise ValueError("limit_value must be positive")


class ConstraintValidator:
    """Validates constraint YAML files."""

    def validate_yaml(self, yaml_content: str) -> ValidationResult:
        """Validate YAML content against constraint schema."""
        try:
            # Parse YAML
            data = yaml.safe_load(yaml_content)
            if not data:
                return ValidationResult(
                    is_valid=False,
                    errors=["Empty YAML content"]
                )

            # Validate against schema
            ConstraintSchema(**data)

            return ValidationResult(
                is_valid=True,
                errors=[],
                data=data
            )

        except yaml.YAMLError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"YAML parsing error: {str(e)}"]
            )
        except ValidationError as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
        except ValueError as e:
            return ValidationResult(
                is_valid=False,
                errors=[str(e)]
            )
