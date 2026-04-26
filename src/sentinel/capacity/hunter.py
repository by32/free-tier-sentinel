"""Capacity Hunter - Aggressive capacity polling and auto-provisioning.

Designed to solve the OCI free tier scarcity problem by continuously
scanning for available capacity and provisioning immediately when found.
"""

import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sentinel.capacity.checker import CapacityResult


class HuntStatus(Enum):
    """Status of a capacity hunt."""
    IDLE = "idle"
    HUNTING = "hunting"
    FOUND_CAPACITY = "found_capacity"
    PROVISIONING = "provisioning"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class HuntTarget:
    """Target configuration for capacity hunting."""
    provider: str
    resource_type: str
    region: str | None = None  # None = use home region

    # For OCI flex shapes
    ocpus: int = 1
    memory_gb: int = 6

    # Provisioning details (required for auto-provision)
    display_name: str = "free-tier-instance"
    image_id: str | None = None
    subnet_id: str | None = None
    ssh_public_key: str | None = None

    # Hunt configuration
    availability_domains: list[str] | None = None  # None = try all ADs


@dataclass
class HuntResult:
    """Result of a capacity hunt."""
    status: HuntStatus
    target: HuntTarget
    started_at: datetime
    completed_at: datetime | None = None
    attempts: int = 0
    successful_ad: str | None = None
    instance_details: dict[str, Any] | None = None
    error_message: str | None = None
    capacity_checks: list[CapacityResult] = field(default_factory=list)


@dataclass
class HuntConfig:
    """Configuration for the capacity hunter."""
    # Polling intervals
    poll_interval_seconds: float = 30.0
    min_poll_interval: float = 10.0
    max_poll_interval: float = 120.0

    # Jitter to avoid thundering herd
    jitter_percent: float = 0.2

    # Retry configuration
    max_attempts: int = 0  # 0 = unlimited
    max_duration_seconds: float = 0  # 0 = unlimited

    # Behavior
    auto_provision: bool = True  # Actually provision when capacity found
    parallel_ad_checks: bool = True  # Check all ADs in parallel
    stop_on_first_success: bool = True  # Stop hunting after successful provision

    # Notifications
    on_capacity_found: Callable[[str, CapacityResult], None] | None = None
    on_provision_success: Callable[[HuntResult], None] | None = None
    on_provision_failure: Callable[[str, Exception], None] | None = None
    on_status_change: Callable[[HuntStatus, str], None] | None = None


class CapacityHunter:
    """Aggressively hunts for capacity and provisions when found.

    Designed for scarce resources like OCI free tier instances.

    Usage:
        hunter = CapacityHunter(oci_checker, config)
        target = HuntTarget(
            provider="oci",
            resource_type="VM.Standard.A1.Flex",
            ocpus=1,
            memory_gb=6,
            image_id="ocid1.image...",
            subnet_id="ocid1.subnet...",
        )
        result = hunter.hunt(target)  # Blocks until success or max attempts

        # Or async:
        hunter.start_hunt(target, callback=my_callback)
        # ... do other things ...
        hunter.stop_hunt()
    """

    def __init__(self, checker: Any, config: HuntConfig | None = None):
        """Initialize the capacity hunter.

        Args:
            checker: A capacity checker (e.g., OCICapacityChecker)
            config: Hunt configuration. Uses defaults if not provided.
        """
        self.checker = checker
        self.config = config or HuntConfig()

        self._status = HuntStatus.IDLE
        self._current_hunt: HuntResult | None = None
        self._hunt_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    @property
    def status(self) -> HuntStatus:
        """Get current hunt status."""
        return self._status

    @property
    def current_hunt(self) -> HuntResult | None:
        """Get current hunt result (if hunting)."""
        return self._current_hunt

    def _set_status(self, status: HuntStatus, message: str = "") -> None:
        """Update status and notify callback."""
        self._status = status
        if self.config.on_status_change:
            try:
                self.config.on_status_change(status, message)
            except Exception:
                pass  # Don't let callback errors stop the hunt

    def hunt(self, target: HuntTarget) -> HuntResult:
        """Start hunting for capacity (blocking).

        Continuously polls for capacity and attempts to provision when found.
        Returns when provisioning succeeds, max attempts reached, or cancelled.

        Args:
            target: The hunt target configuration

        Returns:
            HuntResult with the outcome
        """
        self._stop_event.clear()
        self._current_hunt = HuntResult(
            status=HuntStatus.HUNTING,
            target=target,
            started_at=datetime.now(UTC),
        )
        self._set_status(HuntStatus.HUNTING, f"Starting hunt for {target.resource_type}")

        try:
            result = self._hunt_loop(target)
            return result
        except Exception as e:
            self._current_hunt.status = HuntStatus.FAILED
            self._current_hunt.error_message = str(e)
            self._current_hunt.completed_at = datetime.now(UTC)
            self._set_status(HuntStatus.FAILED, str(e))
            return self._current_hunt

    def start_hunt(
        self,
        target: HuntTarget,
        callback: Callable[[HuntResult], None] | None = None
    ) -> None:
        """Start hunting for capacity (non-blocking).

        Args:
            target: The hunt target configuration
            callback: Optional callback when hunt completes
        """
        if self._hunt_thread and self._hunt_thread.is_alive():
            raise RuntimeError("Hunt already in progress")

        def hunt_wrapper():
            result = self.hunt(target)
            if callback:
                callback(result)

        self._hunt_thread = threading.Thread(target=hunt_wrapper, daemon=True)
        self._hunt_thread.start()

    def stop_hunt(self) -> None:
        """Stop the current hunt."""
        self._stop_event.set()
        self._set_status(HuntStatus.CANCELLED, "Hunt cancelled by user")

        if self._hunt_thread:
            self._hunt_thread.join(timeout=5.0)

    def _hunt_loop(self, target: HuntTarget) -> HuntResult:
        """Main hunting loop."""
        hunt = self._current_hunt
        if hunt is None:
            raise RuntimeError("Hunt not initialized")

        start_time = time.time()

        while not self._stop_event.is_set():
            hunt.attempts += 1

            # Check max attempts
            if self.config.max_attempts > 0 and hunt.attempts > self.config.max_attempts:
                hunt.status = HuntStatus.FAILED
                hunt.error_message = f"Max attempts ({self.config.max_attempts}) reached"
                hunt.completed_at = datetime.now(UTC)
                self._set_status(HuntStatus.FAILED, hunt.error_message)
                return hunt

            # Check max duration
            elapsed = time.time() - start_time
            if self.config.max_duration_seconds > 0 and elapsed > self.config.max_duration_seconds:
                hunt.status = HuntStatus.FAILED
                hunt.error_message = f"Max duration ({self.config.max_duration_seconds}s) reached"
                hunt.completed_at = datetime.now(UTC)
                self._set_status(HuntStatus.FAILED, hunt.error_message)
                return hunt

            # Check capacity across ADs
            ads_to_check = target.availability_domains
            if ads_to_check is None and hasattr(self.checker, 'get_availability_domains'):
                ads_to_check = [ad['name'] for ad in self.checker.get_availability_domains()]

            capacity_results = self._check_all_ads(target, ads_to_check)
            hunt.capacity_checks.extend(capacity_results)

            # Find ADs with capacity
            available_ads = [
                result for result in capacity_results
                if result.available and result.capacity_level > 0
            ]

            if available_ads:
                # Sort by capacity level (highest first)
                available_ads.sort(key=lambda r: r.capacity_level, reverse=True)

                self._set_status(
                    HuntStatus.FOUND_CAPACITY,
                    f"Found capacity in {len(available_ads)} AD(s)"
                )

                if self.config.on_capacity_found:
                    for result in available_ads:
                        provider_data = result.provider_specific_data or {}
                        ad_name = provider_data.get('availability_domain', 'unknown')
                        self.config.on_capacity_found(str(ad_name), result)

                if self.config.auto_provision:
                    # Try to provision in the best AD first
                    for result in available_ads:
                        provider_data = result.provider_specific_data or {}
                        ad_name = provider_data.get('availability_domain')
                        if not ad_name:
                            # Try to extract from region info
                            ad_name = self._get_ad_from_result(result)

                        if ad_name:
                            provision_result = self._try_provision(target, ad_name)
                            if provision_result:
                                hunt.status = HuntStatus.SUCCESS
                                hunt.successful_ad = str(ad_name)
                                hunt.instance_details = provision_result
                                hunt.completed_at = datetime.now(UTC)
                                self._set_status(HuntStatus.SUCCESS, f"Provisioned in {ad_name}")

                                if self.config.on_provision_success:
                                    self.config.on_provision_success(hunt)

                                return hunt
                else:
                    # Capacity found but auto_provision is disabled
                    # Return success - user can provision manually
                    best_result = available_ads[0]
                    best_ad = self._get_ad_from_result(best_result)
                    hunt.status = HuntStatus.SUCCESS
                    hunt.successful_ad = best_ad
                    hunt.instance_details = {"status": "capacity_found", "ad": best_ad}
                    hunt.completed_at = datetime.now(UTC)
                    self._set_status(HuntStatus.SUCCESS, f"Capacity found in {best_ad}")
                    return hunt

            # Calculate next poll interval with jitter
            interval = self._get_poll_interval()
            self._set_status(
                HuntStatus.HUNTING,
                f"Attempt {hunt.attempts}: No capacity. Retrying in {interval:.1f}s"
            )

            # Wait for next poll
            self._stop_event.wait(interval)

        # Hunt was cancelled
        hunt.status = HuntStatus.CANCELLED
        hunt.completed_at = datetime.now(UTC)
        return hunt

    def _check_all_ads(
        self,
        target: HuntTarget,
        ads: list[str] | None
    ) -> list[CapacityResult]:
        """Check capacity in all ADs."""
        if hasattr(self.checker, 'check_capacity_by_ad'):
            # Use the optimized per-AD check if available
            ad_results = self.checker.check_capacity_by_ad(target.resource_type)
            return list(ad_results.values())
        else:
            # Fall back to standard check
            result = self.checker.check_availability(
                target.region or "home",
                target.resource_type
            )
            return [result]

    def _get_ad_from_result(self, result: CapacityResult) -> str | None:
        """Extract AD name from capacity result."""
        provider_data = result.provider_specific_data or {}

        # Try direct AD field
        if 'availability_domain' in provider_data:
            return provider_data['availability_domain']

        # Try available_ads list
        available_ads = provider_data.get('available_ads', [])
        if available_ads:
            return available_ads[0]

        return None

    def _try_provision(self, target: HuntTarget, ad_name: str) -> dict[str, Any] | None:
        """Attempt to provision in the specified AD."""
        self._set_status(HuntStatus.PROVISIONING, f"Attempting provision in {ad_name}")

        try:
            if hasattr(self.checker, 'try_provision_in_ad'):
                result = self.checker.try_provision_in_ad(
                    ad_name=ad_name,
                    shape=target.resource_type,
                    ocpus=target.ocpus,
                    memory_gb=target.memory_gb,
                    display_name=target.display_name,
                    image_id=target.image_id,
                    subnet_id=target.subnet_id,
                    ssh_public_key=target.ssh_public_key,
                )
                return result
            else:
                # Checker doesn't support provisioning
                return {"ad": ad_name, "status": "capacity_found_but_no_provision_support"}

        except Exception as e:
            error_msg = str(e)
            if self.config.on_provision_failure:
                self.config.on_provision_failure(ad_name, e)

            # Check if this is a capacity error (should retry) vs config error (should stop)
            if "capacity" in error_msg.lower() or "out of host" in error_msg.lower():
                self._set_status(HuntStatus.HUNTING, f"Provision failed in {ad_name}: {error_msg}")
                return None
            else:
                # Configuration error - don't retry
                raise

    def _get_poll_interval(self) -> float:
        """Calculate poll interval with jitter."""
        base = self.config.poll_interval_seconds
        jitter = base * self.config.jitter_percent
        interval = base + random.uniform(-jitter, jitter)
        return max(self.config.min_poll_interval, min(interval, self.config.max_poll_interval))


def create_oci_hunter(
    config_file: str | None = None,
    profile: str = "DEFAULT",
    poll_interval: float = 30.0,
    auto_provision: bool = True,
) -> CapacityHunter:
    """Create a capacity hunter configured for OCI free tier.

    Args:
        config_file: Path to OCI config file
        profile: OCI config profile name
        poll_interval: Seconds between capacity checks
        auto_provision: Whether to automatically provision when capacity found

    Returns:
        Configured CapacityHunter instance
    """
    from sentinel.capacity.oci_checker import OCICapacityChecker

    checker = OCICapacityChecker(config_file=config_file, profile=profile)
    config = HuntConfig(
        poll_interval_seconds=poll_interval,
        auto_provision=auto_provision,
    )

    return CapacityHunter(checker, config)
