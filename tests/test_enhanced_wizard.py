"""Tests for enhanced interactive wizard."""

import pytest
from unittest.mock import patch, MagicMock
from sentinel.cli.enhanced_wizard import EnhancedInteractivePlanner
from sentinel.models.core import Plan, Resource


class TestEnhancedInteractivePlanner:
    """Test the enhanced interactive planner."""
    
    def test_plan_creation_cancelled(self):
        """Test that plan creation can be cancelled gracefully."""
        planner = EnhancedInteractivePlanner()
        
        with patch('questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = None
            
            with pytest.raises(KeyboardInterrupt, match="Provider selection cancelled"):
                planner._select_provider_enhanced()
    
    def test_region_selection_cancelled(self):
        """Test that region selection can be cancelled gracefully."""
        planner = EnhancedInteractivePlanner()
        
        with patch('questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = None
            
            with pytest.raises(KeyboardInterrupt, match="Region selection cancelled"):
                planner._select_region_enhanced('aws')
    
    def test_plan_metadata_cancelled(self):
        """Test that plan metadata input can be cancelled gracefully."""
        planner = EnhancedInteractivePlanner()
        
        with patch('questionary.text') as mock_text:
            mock_text.return_value.ask.return_value = None
            
            with pytest.raises(KeyboardInterrupt, match="Plan name input cancelled"):
                planner._get_plan_metadata()
    
    def test_successful_provider_selection(self):
        """Test successful provider selection."""
        planner = EnhancedInteractivePlanner()
        
        with patch('questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = 'aws'
            
            provider = planner._select_provider_enhanced()
            assert provider == 'aws'
    
    def test_successful_region_selection(self):
        """Test successful region selection."""
        planner = EnhancedInteractivePlanner()
        
        with patch('questionary.select') as mock_select:
            mock_select.return_value.ask.return_value = 'us-east-1'
            
            region = planner._select_region_enhanced('aws')
            assert region == 'us-east-1'
    
    def test_successful_plan_metadata(self):
        """Test successful plan metadata input."""
        planner = EnhancedInteractivePlanner()
        
        with patch('questionary.text') as mock_text:
            # First call for plan name, second for description
            mock_text.return_value.ask.side_effect = ['my-test-plan', 'Test description']
            
            name, description = planner._get_plan_metadata()
            assert name == 'my-test-plan'
            assert description == 'Test description'
    
    def test_plan_confirmation_accepted(self):
        """Test plan confirmation when accepted."""
        planner = EnhancedInteractivePlanner()
        
        test_plan = Plan(
            name="test-plan",
            description="Test plan",
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
        
        with patch('questionary.confirm') as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            
            result = planner._review_and_confirm_plan(test_plan)
            assert result is True
    
    def test_plan_confirmation_declined(self):
        """Test plan confirmation when declined."""
        planner = EnhancedInteractivePlanner()
        
        test_plan = Plan(
            name="test-plan",
            description="Test plan",
            resources=[]
        )
        
        with patch('questionary.confirm') as mock_confirm:
            mock_confirm.return_value.ask.return_value = False
            
            result = planner._review_and_confirm_plan(test_plan)
            assert result is False
    
    def test_complete_wizard_flow(self):
        """Test complete wizard flow from start to finish."""
        planner = EnhancedInteractivePlanner()
        
        with patch('questionary.select') as mock_select, \
             patch('questionary.text') as mock_text, \
             patch('questionary.confirm') as mock_confirm:
            
            # Mock selections
            mock_select.return_value.ask.side_effect = [
                'aws',  # provider
                'us-east-1',  # region
                'done'  # finish adding resources
            ]
            
            # Mock text inputs
            mock_text.return_value.ask.side_effect = [
                'test-plan',  # plan name
                'Test description'  # plan description
            ]
            
            # Mock confirmation
            mock_confirm.return_value.ask.return_value = True
            
            # Execute wizard
            plan = planner.create_plan()
            
            # Verify plan
            assert plan.name == 'test-plan'
            assert plan.description == 'Test description'
            assert len(plan.resources) == 1  # Default resource added
            assert plan.resources[0].provider == 'aws'
            assert plan.resources[0].region == 'us-east-1'