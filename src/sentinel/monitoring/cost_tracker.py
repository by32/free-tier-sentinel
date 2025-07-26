"""Real-time cost tracking and alerting system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from decimal import Decimal
from typing import List, Optional, Dict
from enum import Enum

from sentinel.models.core import Resource


class AlertMethod(Enum):
    """Notification methods for cost alerts."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"


@dataclass
class CostAlert:
    """Configuration for cost-based alerts."""
    threshold: Decimal
    period: str  # "daily", "weekly", "monthly"
    notification_method: str
    recipients: List[str]
    enabled: bool = True


@dataclass
class CostDataPoint:
    """Single cost data point for a resource."""
    resource: Resource
    resource_id: Optional[str]
    timestamp: datetime
    hourly_rate: Decimal
    accumulated_cost: Decimal
    usage_hours: float


class CostTracker(ABC):
    """Abstract base class for cost tracking implementations."""
    
    @abstractmethod
    def track_resource_cost(self, resource: Resource, hourly_rate: Decimal, timestamp: datetime):
        """Track cost for a resource at a specific time."""
        raise NotImplementedError("Subclasses must implement track_resource_cost")
    
    @abstractmethod
    def get_current_costs(self) -> List[CostDataPoint]:
        """Get current cost data for all tracked resources."""
        raise NotImplementedError("Subclasses must implement get_current_costs")
    
    @abstractmethod
    def set_cost_alert(self, alert: CostAlert):
        """Configure a cost alert."""
        raise NotImplementedError("Subclasses must implement set_cost_alert")
    
    @abstractmethod
    def check_alerts(self) -> List[CostAlert]:
        """Check for triggered cost alerts."""
        raise NotImplementedError("Subclasses must implement check_alerts")


class LiveCostTracker(CostTracker):
    """Live implementation of cost tracking system."""
    
    def __init__(self):
        """Initialize the live cost tracker."""
        self._cost_data: Dict[str, List[CostDataPoint]] = {}
        self._alerts: List[CostAlert] = []
        self._triggered_alerts: List[CostAlert] = []
    
    def track_resource_cost(self, resource: Resource, hourly_rate: Decimal, timestamp: datetime):
        """Track cost for a resource at a specific time."""
        resource_key = f"{resource.provider}:{resource.service}:{resource.resource_type}:{resource.region}"
        
        if resource_key not in self._cost_data:
            self._cost_data[resource_key] = []
        
        # Calculate accumulated cost based on previous data points
        accumulated_cost = Decimal("0.00")
        previous_data = self._cost_data[resource_key]
        
        if previous_data:
            last_point = previous_data[-1]
            time_diff = (timestamp - last_point.timestamp).total_seconds() / 3600  # hours
            accumulated_cost = last_point.accumulated_cost + (hourly_rate * Decimal(str(time_diff)))
        
        cost_point = CostDataPoint(
            resource=resource,
            resource_id=None,  # Will be set when resource is provisioned
            timestamp=timestamp,
            hourly_rate=hourly_rate,
            accumulated_cost=accumulated_cost,
            usage_hours=len(previous_data) + 1  # Simple hour counting
        )
        
        self._cost_data[resource_key].append(cost_point)
    
    def get_current_costs(self) -> List[CostDataPoint]:
        """Get current cost data for all tracked resources."""
        current_costs = []
        for resource_data in self._cost_data.values():
            if resource_data:
                current_costs.append(resource_data[-1])  # Get latest data point
        return current_costs
    
    def set_cost_alert(self, alert: CostAlert):
        """Configure a cost alert."""
        self._alerts.append(alert)
    
    def check_alerts(self) -> List[CostAlert]:
        """Check for triggered cost alerts."""
        triggered = []
        current_costs = self.get_current_costs()
        
        for alert in self._alerts:
            if not alert.enabled:
                continue
                
            # Simple threshold check - in reality, this would be more sophisticated
            total_cost = sum(cost.accumulated_cost for cost in current_costs)
            
            if total_cost >= alert.threshold:
                triggered.append(alert)
                
        return triggered
    
    def get_cost_history(self, resource: Resource, hours: int) -> List[CostDataPoint]:
        """Get cost history for a specific resource."""
        resource_key = f"{resource.provider}:{resource.service}:{resource.resource_type}:{resource.region}"
        
        if resource_key not in self._cost_data:
            return []
        
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        recent_data = [
            point for point in self._cost_data[resource_key]
            if point.timestamp >= cutoff_time
        ]
        
        return recent_data