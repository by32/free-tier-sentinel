#!/usr/bin/env python3
"""
Advanced features demonstration for Free-Tier Sentinel

Run with: uv run python examples/advanced_features.py
"""

from decimal import Decimal
from datetime import datetime, UTC
from sentinel.models.core import Resource, Plan
from sentinel.monitoring.cost_tracker import LiveCostTracker, CostAlert
from sentinel.monitoring.health_monitor import ResourceHealthMonitor, HealthAlert, HealthStatus
from sentinel.monitoring.analytics import UsageAnalyticsEngine, ReportType
from sentinel.monitoring.optimization import GeneticAlgorithmOptimizer, SimulatedAnnealingOptimizer
from sentinel.monitoring.dependencies import DependencyGraph, DependencyType
from sentinel.integration.cicd import GitHubActionsIntegration
from sentinel.integration.iac import IaCExporter, IaCFormat
from sentinel.integration.notifications import WebhookNotifier


def demo_cost_tracking():
    """Demo real-time cost tracking and alerts"""
    print("=== Cost Tracking Demo ===")
    
    tracker = LiveCostTracker()
    
    # Create test resources
    resources = [
        Resource(provider="aws", service="ec2", resource_type="t2.micro", region="us-east-1", quantity=1, estimated_monthly_usage=100),
        Resource(provider="gcp", service="compute", resource_type="e2-micro", region="us-central1", quantity=1, estimated_monthly_usage=100)
    ]
    
    # Track costs
    for resource in resources:
        hourly_rate = Decimal("0.0116") if resource.provider == "aws" else Decimal("0.0104")
        tracker.track_resource_cost(resource, hourly_rate, datetime.now(UTC))
    
    # Set up alerts
    alert = CostAlert(
        threshold=Decimal("5.00"),
        period="daily",
        notification_method="email",
        recipients=["admin@example.com"]
    )
    tracker.set_cost_alert(alert)
    
    # Check current costs
    current_costs = tracker.get_current_costs()
    print(f"Tracking {len(current_costs)} resources:")
    
    for cost in current_costs:
        print(f"  - {cost.resource.provider} {cost.resource.resource_type}: ${cost.hourly_rate}/hour")
    
    # Check alerts
    triggered = tracker.check_alerts()
    print(f"Active alerts: {len(triggered)}")


def demo_health_monitoring():
    """Demo resource health monitoring"""
    print("\n=== Health Monitoring Demo ===")
    
    monitor = ResourceHealthMonitor()
    
    # Create test resource
    resource = Resource(
        provider="aws",
        service="ec2", 
        resource_type="t2.micro",
        region="us-east-1",
        quantity=1,
        estimated_monthly_usage=100
    )
    
    # Check health
    resource_id = "i-1234567890abcdef0"
    health = monitor.check_resource_health(resource, resource_id)
    
    print(f"Resource {resource_id} health: {health.status.value}")
    print(f"Last checked: {health.last_checked}")
    print(f"Message: {health.message}")
    
    if health.metrics:
        print("Metrics:")
        for metric, value in health.metrics.items():
            print(f"  - {metric}: {value:.1f}%")
    
    # Set up health alert
    alert = HealthAlert(
        resource_id=resource_id,
        alert_on_status=[HealthStatus.UNHEALTHY],
        notification_method="webhook",
        webhook_url="https://api.example.com/alerts"
    )
    monitor.set_health_alert(alert)
    print("Health alert configured")


def demo_usage_analytics():
    """Demo usage analytics and reporting"""
    print("\n=== Usage Analytics Demo ===")
    
    engine = UsageAnalyticsEngine()
    
    # Create test resources
    resources = [
        Resource(provider="aws", service="ec2", resource_type="t2.micro", region="us-east-1", quantity=1, estimated_monthly_usage=100),
        Resource(provider="aws", service="s3", resource_type="standard_storage", region="us-east-1", quantity=1, estimated_monthly_usage=5)
    ]
    
    # Generate usage report
    report = engine.generate_report(resources, ReportType.WEEKLY)
    
    print(f"Usage Report ({report.report_type.value}):")
    print(f"Period: {report.period_start.date()} to {report.period_end.date()}")
    print(f"Total cost: ${report.total_cost}")
    print(f"Total usage hours: {report.total_usage_hours:.1f}")
    
    print("Resource summaries:")
    for summary in report.resource_summaries:
        print(f"  - {summary.resource.resource_type}: {summary.total_usage_hours:.1f}h, ${summary.total_cost}")
    
    # Analyze trends
    resource = resources[0]
    trends = engine.get_usage_trends(resource, days=7)
    print(f"\nTrend analysis for {resource.resource_type}:")
    print(f"  Direction: {trends.trend_direction}")
    print(f"  Average daily usage: {trends.average_daily_usage:.1f}h")
    print(f"  Peak usage: {trends.peak_usage:.1f}h")
    
    # Future prediction
    prediction = engine.predict_future_usage(resource, days=30)
    print(f"\n30-day prediction:")
    print(f"  Predicted usage: {prediction.predicted_usage:.1f}h")
    print(f"  Confidence: {prediction.confidence_score:.1%}")


def demo_optimization():
    """Demo advanced optimization algorithms"""
    print("\n=== Optimization Demo ===")
    
    # Create suboptimal plan
    resources = [
        Resource(provider="aws", service="ec2", resource_type="t3.large", region="us-east-1", quantity=3, estimated_monthly_usage=100),
        Resource(provider="aws", service="ec2", resource_type="m5.xlarge", region="us-west-2", quantity=2, estimated_monthly_usage=200)
    ]
    
    original_plan = Plan(
        name="suboptimal-plan",
        description="Plan that needs optimization",
        resources=resources
    )
    
    print("Original plan:")
    for resource in original_plan.resources:
        print(f"  - {resource.resource_type} x{resource.quantity} in {resource.region}")
    
    # Genetic Algorithm Optimization
    ga_optimizer = GeneticAlgorithmOptimizer(population_size=20, generations=10)
    ga_optimized = ga_optimizer.optimize_plan(original_plan)
    
    print("\nGenetic Algorithm optimized:")
    for resource in ga_optimized.resources:
        print(f"  - {resource.resource_type} x{resource.quantity} in {resource.region}")
    
    # Simulated Annealing Optimization
    sa_optimizer = SimulatedAnnealingOptimizer(initial_temperature=100.0, cooling_rate=0.95)
    sa_optimized = sa_optimizer.optimize_plan(original_plan)
    
    print("\nSimulated Annealing optimized:")
    for resource in sa_optimized.resources:
        print(f"  - {resource.resource_type} x{resource.quantity} in {resource.region}")


def demo_dependency_management():
    """Demo resource dependency management"""
    print("\n=== Dependency Management Demo ===")
    
    graph = DependencyGraph()
    
    # Create resources with dependencies
    vpc = Resource(provider="aws", service="vpc", resource_type="vpc", region="us-east-1", quantity=1, estimated_monthly_usage=0)
    subnet = Resource(provider="aws", service="vpc", resource_type="subnet", region="us-east-1", quantity=1, estimated_monthly_usage=0)
    ec2 = Resource(provider="aws", service="ec2", resource_type="t2.micro", region="us-east-1", quantity=1, estimated_monthly_usage=100)
    rds = Resource(provider="aws", service="rds", resource_type="db.t3.micro", region="us-east-1", quantity=1, estimated_monthly_usage=100)
    
    # Add dependencies
    graph.add_dependency(subnet, vpc, DependencyType.NETWORK)
    graph.add_dependency(ec2, subnet, DependencyType.NETWORK)
    graph.add_dependency(rds, subnet, DependencyType.NETWORK)
    graph.add_dependency(ec2, rds, DependencyType.DATA)
    
    # Validate dependencies
    validation = graph.validate_dependencies()
    print(f"Dependency validation:")
    print(f"  Has circular dependencies: {validation.has_circular_dependencies}")
    print(f"  Warnings: {len(validation.warnings)}")
    
    # Get deployment order
    all_resources = [vpc, subnet, ec2, rds]
    deployment_order = graph.get_deployment_order(all_resources)
    
    print("Recommended deployment order:")
    for i, resource in enumerate(deployment_order, 1):
        print(f"  {i}. {resource.service} {resource.resource_type}")


def demo_cicd_integration():
    """Demo CI/CD integration"""
    print("\n=== CI/CD Integration Demo ===")
    
    # Create plan for CI/CD
    resources = [
        Resource(provider="aws", service="ec2", resource_type="t2.micro", region="us-east-1", quantity=1, estimated_monthly_usage=100)
    ]
    
    plan = Plan(
        name="cicd-deployment",
        description="Plan for CI/CD deployment",
        resources=resources
    )
    
    # Generate GitHub Actions workflow
    github_integration = GitHubActionsIntegration()
    workflow = github_integration.generate_pipeline_config(plan)
    
    print("Generated GitHub Actions workflow:")
    print("=" * 50)
    print(workflow[:300] + "..." if len(workflow) > 300 else workflow)
    print("=" * 50)
    
    # Validate for CI/CD
    is_valid = github_integration.validate_plan_in_pipeline(plan)
    print(f"Plan valid for CI/CD: {is_valid}")


def demo_iac_export():
    """Demo Infrastructure as Code export"""
    print("\n=== Infrastructure as Code Demo ===")
    
    exporter = IaCExporter()
    
    # Create plan
    resources = [
        Resource(provider="aws", service="ec2", resource_type="t2.micro", region="us-east-1", quantity=1, estimated_monthly_usage=100),
        Resource(provider="aws", service="s3", resource_type="standard_storage", region="us-east-1", quantity=1, estimated_monthly_usage=5)
    ]
    
    plan = Plan(
        name="iac-export-demo",
        description="Demo plan for IaC export",
        resources=resources
    )
    
    # Export to different formats
    formats = [IaCFormat.TERRAFORM, IaCFormat.CLOUDFORMATION, IaCFormat.PULUMI]
    
    for format in formats:
        code = exporter.export(plan, format)
        print(f"\n{format.value.title()} export (first 200 chars):")
        print(code[:200] + "...")


def demo_webhooks():
    """Demo webhook notifications"""
    print("\n=== Webhook Notifications Demo ===")
    
    # Note: This uses a mock webhook URL for demo
    notifier = WebhookNotifier(
        webhook_url="https://api.example.com/webhooks/sentinel",
        secret_key="demo-secret-key"
    )
    
    # Create test plan
    plan = Plan(
        name="webhook-test",
        description="Test plan for webhook demo",
        resources=[]
    )
    
    print("Webhook notifier configured")
    print(f"URL: {notifier.webhook_url}")
    print("Secret key: configured (HMAC signing enabled)")
    
    # Note: In real usage, these would send actual HTTP requests
    print("\nWebhook events that would be sent:")
    print("- Deployment completion notifications")
    print("- Cost threshold alerts")
    print("- Resource health issues")


def main():
    """Run all advanced feature demos"""
    print("🚀 Free-Tier Sentinel - Advanced Features Demo")
    print("=" * 60)
    
    demos = [
        demo_cost_tracking,
        demo_health_monitoring,
        demo_usage_analytics,
        demo_optimization,
        demo_dependency_management,
        demo_cicd_integration,
        demo_iac_export,
        demo_webhooks
    ]
    
    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"Demo failed: {e}")
    
    print("\n🎉 Advanced features demonstration completed!")
    print("\nThese features showcase:")
    print("- Real-time monitoring and analytics")
    print("- AI-powered optimization algorithms")
    print("- Enterprise integration capabilities")
    print("- Production-ready automation tools")


if __name__ == "__main__":
    main()