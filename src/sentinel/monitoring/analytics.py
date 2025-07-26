"""Usage analytics and reporting engine."""

import random
from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Dict

from sentinel.models.core import Resource


class ReportType(Enum):
    """Types of usage reports."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class UsageDataPoint:
    """Single usage data point for a resource."""
    resource_id: str
    timestamp: datetime
    cpu_utilization: float
    memory_utilization: float
    network_in: float
    network_out: float
    disk_io: float


@dataclass
class ResourceSummary:
    """Summary of resource usage in a report."""
    resource: Resource
    resource_id: str
    total_usage_hours: float
    average_cpu_utilization: float
    average_memory_utilization: float
    total_cost: Decimal


@dataclass
class UsageReport:
    """Complete usage report."""
    report_type: ReportType
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    resource_summaries: List[ResourceSummary]
    total_cost: Decimal
    total_usage_hours: float


@dataclass
class UsageTrend:
    """Usage trend analysis for a resource."""
    resource: Resource
    period_days: int
    trend_direction: str  # "increasing", "decreasing", "stable"
    average_daily_usage: float
    peak_usage: float
    usage_variance: float


@dataclass
class UsagePrediction:
    """Future usage prediction for a resource."""
    resource: Resource
    prediction_period_days: int
    predicted_usage: float
    confidence_score: float
    prediction_method: str = "linear_regression"


class UsageAnalyticsEngine:
    """Engine for usage analytics and reporting."""
    
    def __init__(self):
        """Initialize the analytics engine."""
        self._usage_data: Dict[str, List[UsageDataPoint]] = {}
    
    def collect_usage_data(self, resource: Resource, resource_id: str) -> UsageDataPoint:
        """Collect usage data from a resource."""
        # Mock data collection - in reality, this would query cloud provider APIs
        data_point = UsageDataPoint(
            resource_id=resource_id,
            timestamp=datetime.now(UTC),
            cpu_utilization=random.uniform(10, 90),
            memory_utilization=random.uniform(20, 85),
            network_in=random.uniform(100, 1000),  # MB
            network_out=random.uniform(50, 500),   # MB
            disk_io=random.uniform(10, 100)        # IOPS
        )
        
        if resource_id not in self._usage_data:
            self._usage_data[resource_id] = []
        
        self._usage_data[resource_id].append(data_point)
        
        return data_point
    
    def generate_report(self, resources: List[Resource], report_type: ReportType) -> UsageReport:
        """Generate a usage report for the specified resources."""
        now = datetime.now(UTC)
        
        # Determine report period
        if report_type == ReportType.DAILY:
            period_start = now - timedelta(days=1)
        elif report_type == ReportType.WEEKLY:
            period_start = now - timedelta(weeks=1)
        else:  # MONTHLY
            period_start = now - timedelta(days=30)
        
        resource_summaries = []
        total_cost = Decimal("0.00")
        total_usage_hours = 0.0
        
        for resource in resources:
            # Mock resource ID
            resource_id = f"{resource.service}-{resource.resource_type}-{hash(resource.region) % 10000}"
            
            # Calculate summary (mock data)
            usage_hours = random.uniform(50, 200)
            avg_cpu = random.uniform(20, 70)
            avg_memory = random.uniform(30, 80)
            cost = Decimal(str(random.uniform(1.0, 10.0)))
            
            summary = ResourceSummary(
                resource=resource,
                resource_id=resource_id,
                total_usage_hours=usage_hours,
                average_cpu_utilization=avg_cpu,
                average_memory_utilization=avg_memory,
                total_cost=cost
            )
            
            resource_summaries.append(summary)
            total_cost += cost
            total_usage_hours += usage_hours
        
        return UsageReport(
            report_type=report_type,
            generated_at=now,
            period_start=period_start,
            period_end=now,
            resource_summaries=resource_summaries,
            total_cost=total_cost,
            total_usage_hours=total_usage_hours
        )
    
    def get_usage_trends(self, resource: Resource, days: int) -> UsageTrend:
        """Analyze usage trends for a resource."""
        # Mock trend analysis - in reality, this would analyze historical data
        average_usage = random.uniform(50, 150)
        peak_usage = average_usage * random.uniform(1.2, 2.0)
        variance = random.uniform(10, 30)
        
        # Determine trend direction based on mock analysis
        trend_factor = random.uniform(0.8, 1.2)
        if trend_factor > 1.1:
            direction = "increasing"
        elif trend_factor < 0.9:
            direction = "decreasing"
        else:
            direction = "stable"
        
        return UsageTrend(
            resource=resource,
            period_days=days,
            trend_direction=direction,
            average_daily_usage=average_usage,
            peak_usage=peak_usage,
            usage_variance=variance
        )
    
    def predict_future_usage(self, resource: Resource, days: int) -> UsagePrediction:
        """Predict future usage for a resource."""
        # Mock prediction - in reality, this would use ML models
        current_trend = self.get_usage_trends(resource, 7)  # Use last 7 days for prediction
        
        # Simple linear extrapolation
        base_usage = current_trend.average_daily_usage
        
        if current_trend.trend_direction == "increasing":
            predicted_usage = base_usage * 1.1 * days
            confidence = 0.75
        elif current_trend.trend_direction == "decreasing":
            predicted_usage = base_usage * 0.9 * days
            confidence = 0.72
        else:
            predicted_usage = base_usage * days
            confidence = 0.85
        
        return UsagePrediction(
            resource=resource,
            prediction_period_days=days,
            predicted_usage=predicted_usage,
            confidence_score=confidence,
            prediction_method="linear_regression"
        )