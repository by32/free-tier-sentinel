"""Resource health monitoring system."""

import time
import threading
from dataclasses import dataclass
from datetime import datetime, UTC
from enum import Enum
from typing import List, Optional, Dict
import requests

from sentinel.models.core import Resource


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Result of a health check."""
    resource_id: str
    status: HealthStatus
    last_checked: datetime
    message: Optional[str] = None
    metrics: Dict[str, float] = None


@dataclass
class HealthAlert:
    """Configuration for health-based alerts."""
    resource_id: str
    alert_on_status: List[HealthStatus]
    notification_method: str
    webhook_url: Optional[str] = None
    email_recipients: Optional[List[str]] = None


class ResourceHealthMonitor:
    """Monitor health of provisioned resources."""
    
    def __init__(self):
        """Initialize the health monitor."""
        self._health_checks: Dict[str, HealthCheck] = {}
        self._alerts: List[HealthAlert] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._resources_to_monitor: List[Resource] = []
        self._check_interval = 300  # 5 minutes default
    
    def check_resource_health(self, resource: Resource, resource_id: str) -> HealthCheck:
        """Check health of a specific resource."""
        # Mock health check - in reality, this would query cloud provider APIs
        import random
        
        # Simulate health check logic
        status = random.choice([HealthStatus.HEALTHY, HealthStatus.HEALTHY, HealthStatus.UNHEALTHY])
        
        health_check = HealthCheck(
            resource_id=resource_id,
            status=status,
            last_checked=datetime.now(UTC),
            message=f"Health check for {resource.resource_type}" + 
                   (" - All systems operational" if status == HealthStatus.HEALTHY else " - Issues detected"),
            metrics={
                "cpu_utilization": random.uniform(10, 90),
                "memory_utilization": random.uniform(20, 85),
                "disk_utilization": random.uniform(15, 70)
            }
        )
        
        self._health_checks[resource_id] = health_check
        
        # Check for alerts
        self._check_health_alerts(health_check)
        
        return health_check
    
    def get_health_status(self, resource_id: str) -> Optional[HealthCheck]:
        """Get current health status for a resource."""
        return self._health_checks.get(resource_id)
    
    def set_health_alert(self, alert: HealthAlert):
        """Configure a health alert."""
        self._alerts.append(alert)
    
    def start_monitoring(self, resources: List[Resource], check_interval: int = 300):
        """Start continuous health monitoring."""
        self._resources_to_monitor = resources
        self._check_interval = check_interval
        self._monitoring = True
        
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop continuous health monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
    
    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self._monitoring and (self._monitor_thread is not None and self._monitor_thread.is_alive())
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._monitoring:
            for resource in self._resources_to_monitor:
                # In reality, we'd need to track resource IDs from provisioning
                mock_resource_id = f"{resource.service}-{resource.resource_type}-{hash(resource.region) % 10000}"
                self.check_resource_health(resource, mock_resource_id)
            
            time.sleep(self._check_interval)
    
    def _check_health_alerts(self, health_check: HealthCheck):
        """Check if health status triggers any alerts."""
        for alert in self._alerts:
            if alert.resource_id == health_check.resource_id:
                if health_check.status in alert.alert_on_status:
                    self._send_health_alert(alert, health_check)
    
    def _send_health_alert(self, alert: HealthAlert, health_check: HealthCheck):
        """Send health alert notification."""
        if alert.notification_method == "webhook" and alert.webhook_url:
            try:
                payload = {
                    "event": "health_alert",
                    "resource_id": health_check.resource_id,
                    "status": health_check.status.value,
                    "message": health_check.message,
                    "timestamp": health_check.last_checked.isoformat(),
                    "metrics": health_check.metrics
                }
                
                requests.post(alert.webhook_url, json=payload, timeout=10)
                
            except requests.RequestException:
                # In a real implementation, we'd log this error
                pass