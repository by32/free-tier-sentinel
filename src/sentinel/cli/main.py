"""Main CLI interface using Click."""

import click
from pathlib import Path
from typing import Optional

from .planning import InteractivePlanner
from .enhanced_wizard import EnhancedInteractivePlanner
from .config import ConfigLoader
from .plan_manager import PlanManager
from .output import PlanFormatter, ColoredOutput
from .dry_run import DryRunValidator


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
def plan(interactive: bool, config: Optional[str], dry_run: bool, provider: Optional[str], 
         region: Optional[str], resource: tuple, output: Optional[str], enhanced: bool):
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
            from datetime import datetime, UTC
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
            planner = CommandLinePlanner()
            deployment_plan = planner.create_plan_from_args(provider, region, resource)
            
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
            for i, resource in enumerate(deployment_plan.resources):
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
def status(deployment_id: Optional[str], show_all: bool):
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
                    state_color = "green" if result.state.value == "ready" else "red"
                    output_handler.info(f"  {result.resource.service} {result.resource.resource_type}: {result.state.value}")
            else:
                output_handler.error(f"Deployment {deployment_id} not found")
        else:
            output_handler.info("No deployment ID specified. Use --deployment-id or --all")
            
    except Exception as e:
        output_handler.error(f"Failed to check status: {str(e)}")


if __name__ == '__main__':
    cli()