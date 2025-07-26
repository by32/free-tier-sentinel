"""Base capacity checking interface and data structures."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CapacityResult:
    """Result of a capacity availability check."""

    region: str
    resource_type: str
    available: bool
    capacity_level: float  # 0.0 to 1.0, representing available capacity
    last_checked: datetime
    provider_specific_data: dict[str, Any] = None

    def __post_init__(self):
        if self.provider_specific_data is None:
            self.provider_specific_data = {}


@dataclass
class CapacityError:
    """Error information for capacity check failures."""

    region: str
    resource_type: str
    error_type: str
    error_message: str
    retry_after: timedelta = None


class CapacityChecker(ABC):
    """Abstract base class for capacity checkers."""

    @abstractmethod
    def check_availability(self, region: str, resource_type: str) -> CapacityResult:
        """Check availability of a resource type in a region."""
        raise NotImplementedError("Subclasses must implement check_availability")

    @abstractmethod
    def get_available_regions(self) -> list[str]:
        """Get list of available regions for this provider."""
        raise NotImplementedError("Subclasses must implement get_available_regions")

    @abstractmethod
    def get_supported_resource_types(self) -> list[str]:
        """Get list of supported resource types for this provider."""
        raise NotImplementedError(
            "Subclasses must implement get_supported_resource_types"
        )
