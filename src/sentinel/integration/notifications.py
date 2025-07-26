"""Webhook notification system for deployment events."""

import json
import hmac
import hashlib
from datetime import datetime, UTC
from typing import Dict, Any, Optional
import requests

from sentinel.models.core import Plan


class WebhookNotifier:
    """Send webhook notifications for deployment events."""
    
    def __init__(self, webhook_url: str, secret_key: Optional[str] = None):
        """Initialize webhook notifier."""
        self.webhook_url = webhook_url
        self.secret_key = secret_key
    
    def notify_deployment_complete(self, plan: Plan, success: bool, deployment_id: Optional[str] = None):
        """Send notification when deployment completes."""
        payload = {
            "event": "deployment_complete",
            "timestamp": datetime.now(UTC).isoformat(),
            "plan_name": plan.name,
            "plan_description": plan.description,
            "success": success,
            "deployment_id": deployment_id,
            "resource_count": len(plan.resources),
            "estimated_cost": float(plan.total_estimated_cost)
        }
        
        self._send_webhook(payload)
    
    def notify_cost_alert(self, plan: Plan, current_cost: float, threshold: float):
        """Send notification when cost threshold is exceeded."""
        payload = {
            "event": "cost_alert",
            "timestamp": datetime.now(UTC).isoformat(),
            "plan_name": plan.name,
            "current_cost": current_cost,
            "threshold": threshold,
            "overage": current_cost - threshold
        }
        
        self._send_webhook(payload)
    
    def notify_health_issue(self, resource_id: str, status: str, message: str):
        """Send notification for resource health issues."""
        payload = {
            "event": "health_alert",
            "timestamp": datetime.now(UTC).isoformat(),
            "resource_id": resource_id,
            "status": status,
            "message": message
        }
        
        self._send_webhook(payload)
    
    def _send_webhook(self, payload: Dict[str, Any]):
        """Send webhook with payload."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Free-Tier-Sentinel/1.0"
        }
        
        # Add signature if secret key is provided
        if self.secret_key:
            payload_json = json.dumps(payload, sort_keys=True)
            signature = hmac.new(
                self.secret_key.encode('utf-8'),
                payload_json.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            headers["X-Sentinel-Signature"] = f"sha256={signature}"
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
        except requests.RequestException:
            # In a real implementation, we'd log this error
            pass