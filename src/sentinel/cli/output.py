"""Rich output formatting and progress display."""

import sys
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

from sentinel.models.core import Plan, Resource


class PlanFormatter:
    """Format deployment plans for display."""
    
    def __init__(self):
        self.console = Console()
    
    def format_plan(self, plan: Plan) -> str:
        """Format a deployment plan for console display."""
        # Create a table for resources
        table = Table(title=f"Deployment Plan: {plan.name}")
        table.add_column("Provider", style="cyan")
        table.add_column("Service", style="magenta")
        table.add_column("Type", style="green")
        table.add_column("Region", style="yellow")
        table.add_column("Quantity", justify="right", style="blue")
        table.add_column("Usage/Month", justify="right", style="red")
        
        for resource in plan.resources:
            table.add_row(
                resource.provider,
                resource.service,
                resource.resource_type,
                resource.region,
                str(resource.quantity),
                str(resource.estimated_monthly_usage)
            )
        
        # Create panel with description
        panel = Panel(
            plan.description,
            title="Description",
            border_style="blue"
        )
        
        # Capture output to string
        with self.console.capture() as capture:
            self.console.print(panel)
            self.console.print(table)
            self.console.print(f"\nEstimated Cost: ${plan.total_estimated_cost}")
        
        return capture.get()


class ProgressDisplay:
    """Display progress for long-running operations."""
    
    def __init__(self):
        self.progress: Optional[Progress] = None
        self.task_id: Optional[int] = None
        self.current_step = 0
        self.total_steps = 0
        self.is_complete = False
    
    def start_operation(self, description: str, total_steps: int):
        """Start a progress display for an operation."""
        self.total_steps = total_steps
        self.current_step = 0
        self.is_complete = False
        
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=Console()
        )
        
        self.progress.start()
        self.task_id = self.progress.add_task(description, total=total_steps)
    
    def update_progress(self, status_message: str):
        """Update progress with a status message."""
        if self.progress and self.task_id is not None:
            self.current_step += 1
            self.progress.update(
                self.task_id,
                advance=1,
                description=status_message
            )
    
    def finish_operation(self, final_message: str):
        """Finish the progress display."""
        if self.progress and self.task_id is not None:
            self.progress.update(
                self.task_id,
                description=final_message,
                completed=self.total_steps
            )
            self.progress.stop()
            self.is_complete = True


class ColoredOutput:
    """Provide colored console output for different message types."""
    
    def __init__(self):
        self.console = Console()
    
    def success(self, message: str):
        """Display a success message in green."""
        self.console.print(f"✅ {message}", style="green")
    
    def error(self, message: str):
        """Display an error message in red."""
        self.console.print(f"❌ {message}", style="red")
    
    def warning(self, message: str):
        """Display a warning message in yellow."""
        self.console.print(f"⚠️  {message}", style="yellow")
    
    def info(self, message: str):
        """Display an info message in blue."""
        self.console.print(f"ℹ️  {message}", style="blue")