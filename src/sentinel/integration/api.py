"""REST API endpoints for automation and integration."""

from typing import List, Dict, Any, Optional
from datetime import datetime, UTC
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uuid

from sentinel.models.core import Plan, Resource
from sentinel.cli.plan_manager import PlanManager
from sentinel.provisioning.engine import DefaultProvisioningEngine


# API Models
class CreatePlanRequest(BaseModel):
    """Request model for creating a plan."""
    name: str
    description: str
    resources: List[Dict[str, Any]]


class PlanResponse(BaseModel):
    """Response model for plan operations."""
    id: str
    name: str
    description: str
    resources: List[Dict[str, Any]]
    estimated_cost: float
    created_at: str
    status: str


class ProvisionRequest(BaseModel):
    """Request model for provisioning."""
    plan_id: str
    dry_run: bool = False


class ProvisionResponse(BaseModel):
    """Response model for provision operations."""
    deployment_id: str
    plan_id: str
    status: str
    started_at: str
    resources_provisioned: int


class SentinelAPI:
    """REST API for Free-Tier Sentinel automation."""
    
    def __init__(self):
        """Initialize the API."""
        self.app = FastAPI(
            title="Free-Tier Sentinel API",
            description="REST API for multi-cloud free-tier resource planning and provisioning",
            version="1.0.0"
        )
        self.plan_manager = PlanManager()
        self.provisioning_engine = DefaultProvisioningEngine()
        self._plans: Dict[str, Plan] = {}
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}
        
        @self.app.post("/plans", response_model=PlanResponse)
        async def create_plan(request: CreatePlanRequest):
            """Create a new deployment plan."""
            plan_id = str(uuid.uuid4())
            
            # Convert request resources to Resource objects
            resources = []
            for resource_data in request.resources:
                resource = Resource(
                    provider=resource_data["provider"],
                    service=resource_data["service"],
                    resource_type=resource_data["resource_type"],
                    region=resource_data["region"],
                    quantity=resource_data.get("quantity", 1),
                    estimated_monthly_usage=resource_data.get("estimated_monthly_usage", 100)
                )
                resources.append(resource)
            
            plan = Plan(
                name=request.name,
                description=request.description,
                resources=resources
            )
            
            self._plans[plan_id] = plan
            
            return self._plan_to_response(plan_id, plan)
        
        @self.app.get("/plans", response_model=List[PlanResponse])
        async def list_plans():
            """List all deployment plans."""
            return [self._plan_to_response(plan_id, plan) 
                   for plan_id, plan in self._plans.items()]
        
        @self.app.get("/plans/{plan_id}", response_model=PlanResponse)
        async def get_plan(plan_id: str):
            """Get a specific deployment plan."""
            if plan_id not in self._plans:
                raise HTTPException(status_code=404, detail="Plan not found")
            
            return self._plan_to_response(plan_id, self._plans[plan_id])
        
        @self.app.post("/plans/{plan_id}/validate")
        async def validate_plan(plan_id: str):
            """Validate a deployment plan."""
            if plan_id not in self._plans:
                raise HTTPException(status_code=404, detail="Plan not found")
            
            plan = self._plans[plan_id]
            
            # Simple validation
            validation_result = {
                "valid": len(plan.resources) > 0,
                "warnings": [],
                "estimated_cost": float(plan.total_estimated_cost),
                "resource_count": len(plan.resources)
            }
            
            # Add warnings for non-free-tier resources
            free_tier_types = {"t2.micro", "t3.micro", "e2-micro", "f1-micro"}
            for resource in plan.resources:
                if resource.resource_type not in free_tier_types:
                    validation_result["warnings"].append(
                        f"Resource {resource.resource_type} may not be free-tier eligible"
                    )
            
            return validation_result
        
        @self.app.post("/plans/{plan_id}/provision", response_model=ProvisionResponse)
        async def provision_plan(plan_id: str, request: ProvisionRequest, background_tasks: BackgroundTasks):
            """Provision a deployment plan."""
            if plan_id not in self._plans:
                raise HTTPException(status_code=404, detail="Plan not found")
            
            plan = self._plans[plan_id]
            
            if request.dry_run:
                # Dry run - just validate
                return ProvisionResponse(
                    deployment_id=f"dry-run-{uuid.uuid4()}",
                    plan_id=plan_id,
                    status="validated",
                    started_at=datetime.now(UTC).isoformat(),
                    resources_provisioned=0
                )
            
            # Start actual provisioning
            deployment_result = self.provisioning_engine.provision_plan(plan)
            
            return ProvisionResponse(
                deployment_id=deployment_result.deployment_id,
                plan_id=plan_id,
                status=deployment_result.state.value,
                started_at=deployment_result.started_at.isoformat(),
                resources_provisioned=len(deployment_result.resource_results)
            )
        
        @self.app.get("/deployments/{deployment_id}")
        async def get_plan_status(deployment_id: str):
            """Get deployment status."""
            status = self.provisioning_engine.get_provisioning_status(deployment_id)
            
            if not status:
                raise HTTPException(status_code=404, detail="Deployment not found")
            
            return {
                "deployment_id": deployment_id,
                "plan_name": status.plan.name,
                "status": status.state.value,
                "started_at": status.started_at.isoformat(),
                "completed_at": status.completed_at.isoformat() if status.completed_at else None,
                "resources": [
                    {
                        "service": result.resource.service,
                        "type": result.resource.resource_type,
                        "status": result.state.value,
                        "resource_id": result.resource_id
                    }
                    for result in status.resource_results
                ]
            }
    
    def _plan_to_response(self, plan_id: str, plan: Plan) -> PlanResponse:
        """Convert Plan to API response format."""
        return PlanResponse(
            id=plan_id,
            name=plan.name,
            description=plan.description,
            resources=[
                {
                    "provider": resource.provider,
                    "service": resource.service,
                    "resource_type": resource.resource_type,
                    "region": resource.region,
                    "quantity": resource.quantity,
                    "estimated_monthly_usage": resource.estimated_monthly_usage
                }
                for resource in plan.resources
            ],
            estimated_cost=float(plan.total_estimated_cost),
            created_at=plan.created_at.isoformat(),
            status="active"
        )
    
    # Main interface methods for testing
    def create_plan(self, name: str, description: str, resources: List[Resource]) -> str:
        """Create a plan programmatically."""
        plan_id = str(uuid.uuid4())
        plan = Plan(name=name, description=description, resources=resources)
        self._plans[plan_id] = plan
        return plan_id
    
    def validate_plan(self, plan_id: str) -> Dict[str, Any]:
        """Validate a plan programmatically."""
        if plan_id not in self._plans:
            return {"valid": False, "error": "Plan not found"}
        
        plan = self._plans[plan_id]
        return {
            "valid": len(plan.resources) > 0,
            "resource_count": len(plan.resources),
            "estimated_cost": float(plan.total_estimated_cost)
        }
    
    def provision_plan(self, plan_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """Provision a plan programmatically."""
        if plan_id not in self._plans:
            return {"status": "error", "message": "Plan not found"}
        
        plan = self._plans[plan_id]
        
        if dry_run:
            return {
                "status": "validated",
                "deployment_id": f"dry-run-{uuid.uuid4()}",
                "resources_provisioned": 0
            }
        
        result = self.provisioning_engine.provision_plan(plan)
        return {
            "status": result.state.value,
            "deployment_id": result.deployment_id,
            "resources_provisioned": len(result.resource_results)
        }
    
    def get_plan_status(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment status programmatically."""
        status = self.provisioning_engine.get_provisioning_status(deployment_id)
        
        if not status:
            return None
        
        return {
            "deployment_id": deployment_id,
            "status": status.state.value,
            "plan_name": status.plan.name,
            "resources": len(status.resource_results)
        }
    
    def list_plans(self) -> List[Dict[str, Any]]:
        """List all plans programmatically."""
        return [
            {
                "id": plan_id,
                "name": plan.name,
                "description": plan.description,
                "resource_count": len(plan.resources)
            }
            for plan_id, plan in self._plans.items()
        ]