"""Main CLI interface using Click."""

from pathlib import Path

import click

from .config import ConfigLoader
from .dry_run import DryRunValidator
from .enhanced_wizard import EnhancedInteractivePlanner
from .output import ColoredOutput, PlanFormatter
from .plan_manager import PlanManager
from .planning import InteractivePlanner


@click.group()
@click.version_option(version="0.1.0", prog_name="sentinel")
def cli():
    """Free-Tier Sentinel: Multi-cloud free-tier planner with live capacity detection."""
    pass


@cli.command()
@click.option('--interactive', is_flag=True, help='Launch enhanced interactive planning wizard')
@click.option('--config', type=click.Path(exists=True), help='Load plan from configuration file')
@click.option('--dry-run', is_flag=True, help='Validate plan without provisioning')
@click.option('--provider', type=click.Choice(['aws', 'gcp', 'azure']), help='Cloud provider')
@click.option('--region', help='Target region')
@click.option('--resource', multiple=True, help='Resource specification (service:type:quantity)')
@click.option('--output', type=click.Path(), help='Save plan to file')
@click.option('--enhanced', is_flag=True, help='Use enhanced wizard with better UI (default for --interactive)')
def plan(interactive: bool, config: str | None, dry_run: bool, provider: str | None,
         region: str | None, resource: tuple, output: str | None, enhanced: bool):
    """Create a deployment plan for cloud resources."""
    output_handler = ColoredOutput()

    try:
        deployment_plan = None

        if interactive:
            # Launch interactive wizard (enhanced by default)
            if enhanced or True:  # Default to enhanced for better UX
                planner = EnhancedInteractivePlanner()
            else:
                planner = InteractivePlanner()
            deployment_plan = planner.create_plan()

            # Show the created plan
            output_handler.success("✅ Plan created successfully!")
            formatter = PlanFormatter()
            formatted_plan = formatter.format_plan(deployment_plan)
            click.echo(formatted_plan)

            # Auto-save the plan
            from datetime import UTC, datetime
            timestamp = datetime.now(UTC).strftime('%Y%m%d-%H%M%S')
            plan_filename = f"{deployment_plan.name}-{timestamp}.json"
            manager = PlanManager()
            manager.save_plan(deployment_plan, Path(plan_filename))
            output_handler.info(f"Plan automatically saved as: {plan_filename}")

            # Ask user what to do next
            click.echo("\nWhat would you like to do next?")
            next_action = click.prompt(
                "Choose an action",
                type=click.Choice(['provision', 'dry-run', 'save-only']),
                default='dry-run',
                show_choices=True
            )

            if next_action == 'provision':
                # Ask for confirmation since this will create real resources
                click.echo("\n⚠️  WARNING: This will create actual cloud resources!")
                click.echo("Make sure you have valid cloud credentials configured.")

                if click.confirm("Do you want to proceed with provisioning real resources?"):
                    # Execute provisioning directly
                    from sentinel.provisioning.engine import DefaultProvisioningEngine
                    engine = DefaultProvisioningEngine()

                    output_handler.info(f"🚀 Starting provisioning for plan: {deployment_plan.name}")

                    try:
                        plan_result = engine.provision_plan(deployment_plan)

                        if plan_result.state.value == "ready":
                            output_handler.success("🎉 All resources provisioned successfully!")
                        else:
                            output_handler.error("❌ Some resources failed to provision")

                        output_handler.info(f"Deployment ID: {plan_result.deployment_id}")
                        output_handler.info(f"Check status with: uv run sentinel status --deployment-id {plan_result.deployment_id}")

                    except Exception as e:
                        output_handler.error(f"Provisioning failed: {str(e)}")
                        output_handler.info(f"You can try again with: uv run sentinel provision --plan-file {plan_filename}")
                else:
                    output_handler.info("Provisioning cancelled.")
                    output_handler.info(f"To provision later: uv run sentinel provision --plan-file {plan_filename}")

                return  # Exit early since we handled everything

            elif next_action == 'dry-run':
                # Set dry_run flag to continue with validation below
                dry_run = True
                output_handler.info("🔍 Running dry-run validation...")

            elif next_action == 'save-only':
                output_handler.success(f"Plan saved as {plan_filename}")
                output_handler.info(f"To validate: uv run sentinel plan --config {plan_filename} --dry-run")
                output_handler.info(f"To provision: uv run sentinel provision --plan-file {plan_filename}")
                return

        elif config:
            # Load from configuration file
            loader = ConfigLoader()
            deployment_plan = loader.load_from_file(Path(config))

        elif provider and region and resource:
            # Create plan from command line arguments
            from .planning import CommandLinePlanner
            cli_planner = CommandLinePlanner()
            deployment_plan = cli_planner.create_plan_from_args(provider, region, resource)

        else:
            output_handler.error("Must specify either --interactive, --config, or --provider/--region/--resource")
            return

        if dry_run:
            # Validate plan without provisioning
            validator = DryRunValidator()
            result = validator.validate_plan(deployment_plan)

            output_handler.info("Dry-run mode: Plan validation results")
            if result.is_valid:
                output_handler.success("Plan validation successful")
                output_handler.info(f"Total resources: {result.total_resources}")
                output_handler.info(f"Estimated cost: ${result.estimated_cost}")
            else:
                output_handler.error("Plan validation failed")
                for warning in result.validation_warnings:
                    output_handler.warning(f"Warning: {warning}")

            output_handler.info("No resources will be provisioned in dry-run mode")
            return

        # Display the plan
        formatter = PlanFormatter()
        formatted_plan = formatter.format_plan(deployment_plan)
        click.echo(formatted_plan)

        # Save plan if requested
        if output:
            manager = PlanManager()
            manager.save_plan(deployment_plan, Path(output))
            output_handler.success(f"Plan saved to {output}")

    except KeyboardInterrupt:
        output_handler.info("Plan creation cancelled by user.")
    except Exception as e:
        output_handler.error(f"Failed to create plan: {str(e)}")


@cli.command()
@click.option('--plan-file', type=click.Path(exists=True), required=True, help='Plan file to execute')
@click.option('--progress', is_flag=True, help='Show real-time progress')
def provision(plan_file: str, progress: bool):
    """Execute a deployment plan to provision cloud resources."""
    output_handler = ColoredOutput()

    try:
        # Load the plan
        manager = PlanManager()
        deployment_plan = manager.load_plan(Path(plan_file))

        output_handler.info(f"Executing plan: {deployment_plan.name}")

        # Execute provisioning
        from sentinel.provisioning.engine import DefaultProvisioningEngine
        engine = DefaultProvisioningEngine()

        if progress:
            from .output import ProgressDisplay
            progress_display = ProgressDisplay()
            progress_display.start_operation("Provisioning resources", len(deployment_plan.resources))

            # Provision each resource with progress updates
            results = []
            for _i, resource in enumerate(deployment_plan.resources):
                progress_display.update_progress(f"Provisioning {resource.service} {resource.resource_type}")
                result = engine.provision_resource(resource)
                results.append(result)

            progress_display.finish_operation("Provisioning complete")

            # Show results
            successful = [r for r in results if r.state.value == "ready"]
            failed = [r for r in results if r.state.value == "failed"]

            output_handler.success(f"Successfully provisioned {len(successful)} resources")
            if failed:
                output_handler.error(f"Failed to provision {len(failed)} resources")
        else:
            # Execute plan without progress display
            plan_result = engine.provision_plan(deployment_plan)

            if plan_result.state.value == "ready":
                output_handler.success("All resources provisioned successfully")
            else:
                output_handler.error("Some resources failed to provision")

            output_handler.info(f"Deployment ID: {plan_result.deployment_id}")

    except Exception as e:
        output_handler.error(f"Failed to provision resources: {str(e)}")


@cli.command()
@click.option('--deployment-id', help='Specific deployment ID to check')
@click.option('--all', 'show_all', is_flag=True, help='Show all active deployments')
def status(deployment_id: str | None, show_all: bool):
    """Check deployment status and resource health."""
    output_handler = ColoredOutput()

    try:
        from sentinel.provisioning.engine import DefaultProvisioningEngine
        engine = DefaultProvisioningEngine()

        if deployment_id:
            # Check specific deployment
            deployment_status = engine.get_provisioning_status(deployment_id)

            if deployment_status:
                output_handler.info(f"Deployment: {deployment_status.deployment_id}")
                output_handler.info(f"Plan: {deployment_status.plan.name}")
                output_handler.info(f"State: {deployment_status.state.value}")
                output_handler.info(f"Started: {deployment_status.started_at}")

                if deployment_status.completed_at:
                    output_handler.info(f"Completed: {deployment_status.completed_at}")

                # Show resource status
                for result in deployment_status.resource_results:
                    output_handler.info(f"  {result.resource.service} {result.resource.resource_type}: {result.state.value}")
            else:
                output_handler.error(f"Deployment {deployment_id} not found")
        else:
            output_handler.info("No deployment ID specified. Use --deployment-id or --all")

    except Exception as e:
        output_handler.error(f"Failed to check status: {str(e)}")


@cli.command()
@click.option('--provider', type=click.Choice(['oci']), default='oci', help='Cloud provider (currently OCI only)')
@click.option('--shape', default='VM.Standard.A1.Flex', help='Compute shape to hunt for')
@click.option('--ocpus', default=1, type=int, help='Number of OCPUs (for flex shapes)')
@click.option('--memory', default=6, type=int, help='Memory in GB (for flex shapes)')
@click.option('--interval', default=30.0, type=float, help='Poll interval in seconds')
@click.option('--max-attempts', default=0, type=int, help='Max attempts (0=unlimited)')
@click.option('--max-duration', default=0, type=int, help='Max duration in seconds (0=unlimited)')
@click.option('--image-id', help='Boot image OCID (required for auto-provision)')
@click.option('--subnet-id', help='Subnet OCID (required for auto-provision)')
@click.option('--ssh-key', type=click.Path(exists=True), help='Path to SSH public key file')
@click.option('--name', default='free-tier-instance', help='Instance display name')
@click.option('--dry-run', is_flag=True, help='Check capacity only, do not provision')
@click.option('--oci-config', type=click.Path(exists=True), help='Path to OCI config file')
@click.option('--oci-profile', default='DEFAULT', help='OCI config profile name')
def hunt(provider: str, shape: str, ocpus: int, memory: int, interval: float,
         max_attempts: int, max_duration: int, image_id: str | None, subnet_id: str | None,
         ssh_key: str | None, name: str, dry_run: bool, oci_config: str | None, oci_profile: str):
    """Hunt for scarce free-tier capacity (e.g., OCI A1 instances).

    Continuously polls for available capacity across all availability domains
    and automatically provisions when capacity is found.

    Examples:

        # Check capacity only (no provisioning):
        sentinel hunt --dry-run

        # Hunt and auto-provision when found:
        sentinel hunt --image-id ocid1.image... --subnet-id ocid1.subnet... --ssh-key ~/.ssh/id_rsa.pub

        # Hunt with custom configuration:
        sentinel hunt --shape VM.Standard.A1.Flex --ocpus 2 --memory 12 --interval 15
    """
    output_handler = ColoredOutput()

    output_handler.info("🎯 Free-Tier Capacity Hunter")
    output_handler.info(f"   Provider: {provider.upper()}")
    output_handler.info(f"   Shape: {shape}")
    output_handler.info(f"   OCPUs: {ocpus}, Memory: {memory}GB")
    output_handler.info(f"   Poll interval: {interval}s")

    if dry_run:
        output_handler.warning("   Mode: DRY-RUN (capacity check only)")
    else:
        if not image_id or not subnet_id:
            output_handler.error("--image-id and --subnet-id are required for auto-provisioning")
            output_handler.info("Use --dry-run to check capacity without provisioning")
            return
        output_handler.success("   Mode: AUTO-PROVISION")

    # Load SSH key if provided
    ssh_public_key = None
    if ssh_key:
        with open(ssh_key) as f:
            ssh_public_key = f.read().strip()
        output_handler.info(f"   SSH key: {ssh_key}")

    try:
        from sentinel.capacity.hunter import (
            CapacityHunter,
            HuntConfig,
            HuntStatus,
            HuntTarget,
        )
        from sentinel.capacity.oci_checker import OCICapacityChecker

        output_handler.info("\n📡 Connecting to OCI...")

        # Initialize OCI checker
        checker = OCICapacityChecker(config_file=oci_config, profile=oci_profile)
        output_handler.success(f"   Home region: {checker.home_region}")

        # Get availability domains
        ads = checker.get_availability_domains()
        output_handler.info(f"   Availability domains: {len(ads)}")
        for ad in ads:
            output_handler.info(f"      - {ad['name']}")

        # Create hunt config with callbacks for live updates
        def on_status_change(status: HuntStatus, message: str) -> None:
            timestamp = click.style(f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}]", dim=True)
            if status == HuntStatus.HUNTING:
                click.echo(f"{timestamp} 🔍 {message}")
            elif status == HuntStatus.FOUND_CAPACITY:
                click.echo(f"{timestamp} ✨ {click.style(message, fg='green', bold=True)}")
            elif status == HuntStatus.PROVISIONING:
                click.echo(f"{timestamp} 🚀 {click.style(message, fg='yellow')}")
            elif status == HuntStatus.SUCCESS:
                click.echo(f"{timestamp} 🎉 {click.style(message, fg='green', bold=True)}")
            elif status == HuntStatus.FAILED:
                click.echo(f"{timestamp} ❌ {click.style(message, fg='red')}")
            elif status == HuntStatus.CANCELLED:
                click.echo(f"{timestamp} ⏹️  {message}")

        def on_capacity_found(ad_name: str, result) -> None:
            output_handler.success(f"   Capacity found in {ad_name} (level: {result.capacity_level:.0%})")

        config = HuntConfig(
            poll_interval_seconds=interval,
            max_attempts=max_attempts if max_attempts > 0 else 0,
            max_duration_seconds=float(max_duration) if max_duration > 0 else 0,
            auto_provision=not dry_run,
            on_status_change=on_status_change,
            on_capacity_found=on_capacity_found,
        )

        # Create hunt target
        target = HuntTarget(
            provider=provider,
            resource_type=shape,
            ocpus=ocpus,
            memory_gb=memory,
            display_name=name,
            image_id=image_id,
            subnet_id=subnet_id,
            ssh_public_key=ssh_public_key,
        )

        # Start hunting
        output_handler.info("\n🏹 Starting capacity hunt... (Ctrl+C to stop)\n")

        hunter = CapacityHunter(checker, config)

        try:
            result = hunter.hunt(target)

            # Show results
            click.echo("\n" + "="*60)
            if result.status == HuntStatus.SUCCESS:
                output_handler.success("🎉 SUCCESS! Instance provisioned!")
                output_handler.info(f"   AD: {result.successful_ad}")
                if result.instance_details:
                    output_handler.info(f"   Instance ID: {result.instance_details.get('instance_id', 'N/A')}")
                    output_handler.info(f"   State: {result.instance_details.get('lifecycle_state', 'N/A')}")
            elif result.status == HuntStatus.CANCELLED:
                output_handler.warning("Hunt cancelled by user")
            else:
                output_handler.error(f"Hunt ended: {result.error_message}")

            output_handler.info(f"\nTotal attempts: {result.attempts}")
            if result.started_at and result.completed_at:
                duration = (result.completed_at - result.started_at).total_seconds()
                output_handler.info(f"Duration: {duration:.1f}s")

        except KeyboardInterrupt:
            output_handler.warning("\n\nHunt cancelled by user (Ctrl+C)")
            hunter.stop_hunt()

    except ImportError as e:
        output_handler.error(f"Missing dependency: {e}")
        output_handler.info("Install OCI SDK with: pip install oci")
    except Exception as e:
        output_handler.error(f"Hunt failed: {str(e)}")
        if "NotAuthenticated" in str(e) or "config" in str(e).lower():
            output_handler.info("\nMake sure your OCI config is set up:")
            output_handler.info("  1. Install OCI CLI: pip install oci-cli")
            output_handler.info("  2. Run: oci setup config")
            output_handler.info("  3. Or specify --oci-config and --oci-profile")


if __name__ == '__main__':
    cli()
