"""Retry mechanisms for provisioning operations."""

import random
import time
from dataclasses import dataclass
from typing import Optional

from .engine import ProvisioningError


@dataclass
class RetryConfig:
    """Configuration for retry mechanisms."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class RetryPolicy:
    """Retry policy for handling provisioning failures."""
    
    def __init__(self, config: RetryConfig):
        """Initialize retry policy with configuration."""
        self.config = config
    
    def should_retry(self, error: ProvisioningError, attempt: int) -> bool:
        """Determine if a failed operation should be retried."""
        # Don't retry if we've exceeded max attempts
        if attempt >= self.config.max_attempts:
            return False
        
        # Only retry if the error suggests it's retriable
        return error.retry_suggested
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt."""
        # Calculate exponential backoff
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        
        # Cap at max delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)  # Ensure non-negative delay