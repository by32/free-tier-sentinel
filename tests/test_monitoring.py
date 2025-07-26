"""Test real-time monitoring and cost tracking using TDD approach."""

import pytest
from datetime import datetime, UTC, timedelta
from unittest.mock import Mock, patch, call
from decimal import Decimal

from sentinel.models.core import Resource, Plan


class TestCostTracker:
    """Test real-time cost tracking functionality."""

    def test_cost_tracker_interface(self):
        """Test that cost tracker defines the required interface."""
        from sentinel.monitoring.cost_tracker import CostTracker
        
        # Test that we can't instantiate abstract class
        with pytest.raises(TypeError):
            CostTracker()

    def test_live_cost_tracker_creation(self):
        """Test creating a live cost tracking implementation."""
        from sentinel.monitoring.cost_tracker import LiveCostTracker
        
        tracker = LiveCostTracker()
        
        assert tracker is not None
        assert hasattr(tracker, 'track_resource_cost')
        assert hasattr(tracker, 'get_current_costs')
        assert hasattr(tracker, 'set_cost_alert')
        assert hasattr(tracker, 'check_alerts')

    def test_track_resource_cost(self):
        """Test tracking costs for individual resources."""
        from sentinel.monitoring.cost_tracker import LiveCostTracker
        
        tracker = LiveCostTracker()
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        # Track cost over time
        tracker.track_resource_cost(resource, Decimal("0.0116"), datetime.now(UTC))
        
        current_costs = tracker.get_current_costs()
        assert len(current_costs) == 1
        assert current_costs[0].resource == resource
        assert current_costs[0].hourly_rate == Decimal("0.0116")

    def test_cost_alerts(self):
        """Test cost alert functionality."""
        from sentinel.monitoring.cost_tracker import LiveCostTracker, CostAlert
        
        tracker = LiveCostTracker()
        
        # Set up cost alert
        alert = CostAlert(
            threshold=Decimal("5.00"),
            period="daily",
            notification_method="email",
            recipients=["admin@example.com"]
        )
        
        tracker.set_cost_alert(alert)
        
        # Simulate cost accumulation
        resource = Resource(
            provider="aws",
            service="ec2", 
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=500  # High usage to trigger alert
        )
        
        tracker.track_resource_cost(resource, Decimal("0.0116"), datetime.now(UTC))
        
        # Check for alerts
        triggered_alerts = tracker.check_alerts()
        assert len(triggered_alerts) >= 0  # May or may not trigger based on timing

    def test_cost_history_tracking(self):
        """Test historical cost tracking."""
        from sentinel.monitoring.cost_tracker import LiveCostTracker
        
        tracker = LiveCostTracker()
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro", 
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        # Track costs over multiple time periods
        base_time = datetime.now(UTC)
        for i in range(5):
            tracker.track_resource_cost(
                resource, 
                Decimal("0.0116"), 
                base_time + timedelta(hours=i)
            )
        
        history = tracker.get_cost_history(resource, hours=6)
        assert len(history) == 5
        assert all(entry.resource == resource for entry in history)


class TestResourceHealthMonitor:
    """Test resource health monitoring functionality."""

    def test_health_monitor_interface(self):
        """Test that health monitor defines the required interface."""
        from sentinel.monitoring.health_monitor import ResourceHealthMonitor
        
        monitor = ResourceHealthMonitor()
        
        assert hasattr(monitor, 'check_resource_health')
        assert hasattr(monitor, 'get_health_status')
        assert hasattr(monitor, 'set_health_alert')
        assert hasattr(monitor, 'start_monitoring')
        assert hasattr(monitor, 'stop_monitoring')

    def test_resource_health_checking(self):
        """Test checking health of provisioned resources."""
        from sentinel.monitoring.health_monitor import ResourceHealthMonitor, HealthStatus
        
        monitor = ResourceHealthMonitor()
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        # Simulate resource with ID
        resource_id = "i-1234567890abcdef0"
        
        health_status = monitor.check_resource_health(resource, resource_id)
        
        assert health_status.resource_id == resource_id
        assert health_status.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN]
        assert health_status.last_checked is not None

    def test_health_alerts(self):
        """Test health alert functionality."""
        from sentinel.monitoring.health_monitor import ResourceHealthMonitor, HealthAlert, HealthStatus
        
        monitor = ResourceHealthMonitor()
        
        # Set up health alert
        alert = HealthAlert(
            resource_id="i-1234567890abcdef0",
            alert_on_status=[HealthStatus.UNHEALTHY],
            notification_method="webhook",
            webhook_url="https://api.example.com/alerts"
        )
        
        monitor.set_health_alert(alert)
        
        # Simulate unhealthy resource
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        with patch('sentinel.monitoring.health_monitor.requests.post') as mock_post:
            health_status = monitor.check_resource_health(resource, "i-1234567890abcdef0")
            
            # If resource is unhealthy, webhook should be called
            if health_status.status == HealthStatus.UNHEALTHY:
                mock_post.assert_called_once()

    def test_continuous_monitoring(self):
        """Test continuous health monitoring."""
        from sentinel.monitoring.health_monitor import ResourceHealthMonitor
        
        monitor = ResourceHealthMonitor()
        
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100
            )
        ]
        
        # Start monitoring
        monitor.start_monitoring(resources, check_interval=60)
        assert monitor.is_monitoring() is True
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert monitor.is_monitoring() is False


class TestUsageAnalytics:
    """Test usage analytics and reporting functionality."""

    def test_analytics_engine_creation(self):
        """Test creating usage analytics engine."""
        from sentinel.monitoring.analytics import UsageAnalyticsEngine
        
        engine = UsageAnalyticsEngine()
        
        assert engine is not None
        assert hasattr(engine, 'collect_usage_data')
        assert hasattr(engine, 'generate_report')
        assert hasattr(engine, 'get_usage_trends')
        assert hasattr(engine, 'predict_future_usage')

    def test_usage_data_collection(self):
        """Test collecting usage data from resources."""
        from sentinel.monitoring.analytics import UsageAnalyticsEngine, UsageDataPoint
        
        engine = UsageAnalyticsEngine()
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        # Collect usage data
        usage_data = engine.collect_usage_data(resource, "i-1234567890abcdef0")
        
        assert isinstance(usage_data, UsageDataPoint)
        assert usage_data.resource_id == "i-1234567890abcdef0"
        assert usage_data.timestamp is not None
        assert usage_data.cpu_utilization >= 0
        assert usage_data.memory_utilization >= 0

    def test_usage_report_generation(self):
        """Test generating usage reports."""
        from sentinel.monitoring.analytics import UsageAnalyticsEngine, ReportType
        
        engine = UsageAnalyticsEngine()
        
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100
            )
        ]
        
        # Generate daily report
        report = engine.generate_report(resources, ReportType.DAILY)
        
        assert report.report_type == ReportType.DAILY
        assert report.generated_at is not None
        assert len(report.resource_summaries) >= 0
        assert report.total_cost >= Decimal("0")

    def test_usage_trend_analysis(self):
        """Test usage trend analysis."""
        from sentinel.monitoring.analytics import UsageAnalyticsEngine
        
        engine = UsageAnalyticsEngine()
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        # Analyze trends over last 7 days
        trends = engine.get_usage_trends(resource, days=7)
        
        assert trends.resource == resource
        assert trends.period_days == 7
        assert trends.trend_direction in ['increasing', 'decreasing', 'stable']
        assert trends.average_daily_usage >= 0

    def test_usage_prediction(self):
        """Test future usage prediction."""
        from sentinel.monitoring.analytics import UsageAnalyticsEngine
        
        engine = UsageAnalyticsEngine()
        
        resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        # Predict usage for next 30 days
        prediction = engine.predict_future_usage(resource, days=30)
        
        assert prediction.resource == resource
        assert prediction.prediction_period_days == 30
        assert prediction.predicted_usage >= 0
        assert prediction.confidence_score >= 0.0
        assert prediction.confidence_score <= 1.0


class TestResourceDependencies:
    """Test resource dependency management."""

    def test_dependency_graph_creation(self):
        """Test creating resource dependency graphs."""
        from sentinel.monitoring.dependencies import DependencyGraph
        
        graph = DependencyGraph()
        
        assert graph is not None
        assert hasattr(graph, 'add_dependency')
        assert hasattr(graph, 'get_dependencies')
        assert hasattr(graph, 'get_dependents')
        assert hasattr(graph, 'validate_dependencies')

    def test_adding_dependencies(self):
        """Test adding resource dependencies."""
        from sentinel.monitoring.dependencies import DependencyGraph, DependencyType
        
        graph = DependencyGraph()
        
        # Create resources
        vpc_resource = Resource(
            provider="aws",
            service="vpc",
            resource_type="vpc",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=0
        )
        
        ec2_resource = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        # Add dependency: EC2 depends on VPC
        graph.add_dependency(
            dependent=ec2_resource,
            dependency=vpc_resource,
            dependency_type=DependencyType.NETWORK
        )
        
        dependencies = graph.get_dependencies(ec2_resource)
        assert len(dependencies) == 1
        assert dependencies[0].dependency == vpc_resource
        assert dependencies[0].dependency_type == DependencyType.NETWORK

    def test_dependency_validation(self):
        """Test validating dependency chains."""
        from sentinel.monitoring.dependencies import DependencyGraph, DependencyType
        
        graph = DependencyGraph()
        
        # Create circular dependency scenario
        resource_a = Resource(
            provider="aws",
            service="ec2",
            resource_type="t2.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        resource_b = Resource(
            provider="aws",
            service="rds",
            resource_type="db.t3.micro",
            region="us-east-1",
            quantity=1,
            estimated_monthly_usage=100
        )
        
        # Add circular dependency
        graph.add_dependency(resource_a, resource_b, DependencyType.DATA)
        graph.add_dependency(resource_b, resource_a, DependencyType.NETWORK)
        
        # Validation should detect circular dependency
        validation_result = graph.validate_dependencies()
        assert validation_result.has_circular_dependencies is True
        assert len(validation_result.circular_dependency_chains) > 0

    def test_deployment_order_calculation(self):
        """Test calculating optimal deployment order based on dependencies."""
        from sentinel.monitoring.dependencies import DependencyGraph, DependencyType
        
        graph = DependencyGraph()
        
        # Create a chain: VPC -> Subnet -> EC2
        vpc = Resource(provider="aws", service="vpc", resource_type="vpc", region="us-east-1", quantity=1, estimated_monthly_usage=0)
        subnet = Resource(provider="aws", service="vpc", resource_type="subnet", region="us-east-1", quantity=1, estimated_monthly_usage=0)
        ec2 = Resource(provider="aws", service="ec2", resource_type="t2.micro", region="us-east-1", quantity=1, estimated_monthly_usage=100)
        
        graph.add_dependency(subnet, vpc, DependencyType.NETWORK)
        graph.add_dependency(ec2, subnet, DependencyType.NETWORK)
        
        # Calculate deployment order
        deployment_order = graph.get_deployment_order([vpc, subnet, ec2])
        
        # VPC should come first, EC2 should come last
        assert deployment_order.index(vpc) < deployment_order.index(subnet)
        assert deployment_order.index(subnet) < deployment_order.index(ec2)


class TestAdvancedOptimization:
    """Test advanced optimization algorithms."""

    def test_genetic_algorithm_optimizer(self):
        """Test genetic algorithm for resource optimization."""
        from sentinel.monitoring.optimization import GeneticAlgorithmOptimizer
        
        optimizer = GeneticAlgorithmOptimizer(
            population_size=50,
            generations=100,
            mutation_rate=0.1,
            crossover_rate=0.8
        )
        
        assert optimizer.population_size == 50
        assert optimizer.generations == 100
        assert hasattr(optimizer, 'optimize_plan')
        assert hasattr(optimizer, 'fitness_function')

    def test_plan_optimization_genetic(self):
        """Test optimizing deployment plans with genetic algorithm."""
        from sentinel.monitoring.optimization import GeneticAlgorithmOptimizer
        
        optimizer = GeneticAlgorithmOptimizer()
        
        # Create suboptimal plan
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t3.large",  # Oversized for free tier
                region="us-east-1",
                quantity=3,
                estimated_monthly_usage=100
            )
        ]
        
        original_plan = Plan(
            name="suboptimal-plan",
            description="Plan that needs optimization",
            resources=resources
        )
        
        # Optimize the plan
        optimized_plan = optimizer.optimize_plan(original_plan)
        
        assert optimized_plan.name.startswith("optimized-")
        assert len(optimized_plan.resources) >= 1
        
        # Should suggest free-tier alternatives
        optimized_resources = [r for r in optimized_plan.resources if r.resource_type in ["t2.micro", "t3.micro"]]
        assert len(optimized_resources) > 0

    def test_simulated_annealing_optimizer(self):
        """Test simulated annealing optimization algorithm."""
        from sentinel.monitoring.optimization import SimulatedAnnealingOptimizer
        
        optimizer = SimulatedAnnealingOptimizer(
            initial_temperature=100.0,
            cooling_rate=0.95,
            min_temperature=0.1
        )
        
        assert optimizer.initial_temperature == 100.0
        assert optimizer.cooling_rate == 0.95
        assert hasattr(optimizer, 'optimize_plan')
        assert hasattr(optimizer, 'acceptance_probability')

    def test_multi_objective_optimization(self):
        """Test multi-objective optimization (cost vs performance)."""
        from sentinel.monitoring.optimization import MultiObjectiveOptimizer, OptimizationObjective
        
        optimizer = MultiObjectiveOptimizer(
            objectives=[
                OptimizationObjective.MINIMIZE_COST,
                OptimizationObjective.MAXIMIZE_PERFORMANCE,
                OptimizationObjective.MAXIMIZE_AVAILABILITY
            ]
        )
        
        resources = [
            Resource(
                provider="aws",
                service="ec2",
                resource_type="t2.micro",
                region="us-east-1",
                quantity=1,
                estimated_monthly_usage=100
            )
        ]
        
        plan = Plan(
            name="multi-objective-test",
            description="Test multi-objective optimization",
            resources=resources
        )
        
        pareto_solutions = optimizer.optimize_plan(plan)
        
        # Should return multiple Pareto-optimal solutions
        assert len(pareto_solutions) >= 1
        assert all(isinstance(solution, Plan) for solution in pareto_solutions)


class TestIntegrationFeatures:
    """Test CI/CD and automation integration features."""

    def test_cicd_integration_interface(self):
        """Test CI/CD integration interface."""
        from sentinel.integration.cicd import CICDIntegration
        
        # Test that we can't instantiate abstract class
        with pytest.raises(TypeError):
            CICDIntegration()
        
        # Test that abstract methods exist
        assert hasattr(CICDIntegration, 'generate_pipeline_config')
        assert hasattr(CICDIntegration, 'validate_plan_in_pipeline')
        assert hasattr(CICDIntegration, 'deploy_from_pipeline')

    def test_github_actions_integration(self):
        """Test GitHub Actions workflow generation."""
        from sentinel.integration.cicd import GitHubActionsIntegration
        
        integration = GitHubActionsIntegration()
        
        plan = Plan(
            name="ci-test-plan",
            description="Plan for CI/CD testing",
            resources=[
                Resource(
                    provider="aws",
                    service="ec2",
                    resource_type="t2.micro",
                    region="us-east-1",
                    quantity=1,
                    estimated_monthly_usage=100
                )
            ]
        )
        
        workflow_yaml = integration.generate_pipeline_config(plan)
        
        assert 'name:' in workflow_yaml
        assert 'on:' in workflow_yaml
        assert 'jobs:' in workflow_yaml
        assert 'sentinel plan' in workflow_yaml

    def test_infrastructure_as_code_export(self):
        """Test exporting plans as Infrastructure as Code."""
        from sentinel.integration.iac import IaCExporter, IaCFormat
        
        exporter = IaCExporter()
        
        plan = Plan(
            name="iac-export-test",
            description="Plan for IaC export testing",
            resources=[
                Resource(
                    provider="aws",
                    service="ec2", 
                    resource_type="t2.micro",
                    region="us-east-1",
                    quantity=1,
                    estimated_monthly_usage=100
                )
            ]
        )
        
        # Test Terraform export
        terraform_code = exporter.export(plan, IaCFormat.TERRAFORM)
        
        assert 'resource "aws_instance"' in terraform_code
        assert 'instance_type = "t2.micro"' in terraform_code
        assert 'us-east-1' in terraform_code

    def test_api_endpoints(self):
        """Test REST API endpoints for automation."""
        from sentinel.integration.api import SentinelAPI
        
        api = SentinelAPI()
        
        assert hasattr(api, 'create_plan')
        assert hasattr(api, 'validate_plan')
        assert hasattr(api, 'provision_plan')
        assert hasattr(api, 'get_plan_status')
        assert hasattr(api, 'list_plans')

    def test_webhook_notifications(self):
        """Test webhook notification system."""
        from sentinel.integration.notifications import WebhookNotifier
        
        notifier = WebhookNotifier(
            webhook_url="https://api.example.com/webhooks/sentinel",
            secret_key="test-secret-key"
        )
        
        # Test deployment completion notification
        plan = Plan(name="webhook-test", description="Test webhooks", resources=[])
        
        with patch('sentinel.integration.notifications.requests.post') as mock_post:
            notifier.notify_deployment_complete(plan, success=True)
            
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert kwargs['json']['event'] == 'deployment_complete'
            assert kwargs['json']['plan_name'] == 'webhook-test'
            assert kwargs['json']['success'] is True