"""Resource dependency management and deployment ordering."""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Set
from collections import defaultdict, deque

from sentinel.models.core import Resource


class DependencyType(Enum):
    """Types of resource dependencies."""
    NETWORK = "network"
    DATA = "data"
    COMPUTE = "compute"
    SECURITY = "security"


@dataclass
class Dependency:
    """Represents a dependency relationship between resources."""
    dependent: Resource
    dependency: Resource
    dependency_type: DependencyType


@dataclass
class ValidationResult:
    """Result of dependency validation."""
    has_circular_dependencies: bool
    circular_dependency_chains: List[List[Resource]]
    missing_dependencies: List[Resource]
    warnings: List[str]


class DependencyGraph:
    """Graph for managing resource dependencies."""
    
    def __init__(self):
        """Initialize the dependency graph."""
        self._dependencies: List[Dependency] = []
        self._dependents: Dict[Resource, List[Dependency]] = defaultdict(list)
        self._dependencies_of: Dict[Resource, List[Dependency]] = defaultdict(list)
    
    def add_dependency(self, dependent: Resource, dependency: Resource, dependency_type: DependencyType):
        """Add a dependency relationship."""
        dep = Dependency(
            dependent=dependent,
            dependency=dependency,
            dependency_type=dependency_type
        )
        
        self._dependencies.append(dep)
        self._dependents[dependency].append(dep)
        self._dependencies_of[dependent].append(dep)
    
    def get_dependencies(self, resource: Resource) -> List[Dependency]:
        """Get all dependencies for a resource."""
        return self._dependencies_of[resource]
    
    def get_dependents(self, resource: Resource) -> List[Dependency]:
        """Get all resources that depend on this resource."""
        return self._dependents[resource]
    
    def validate_dependencies(self) -> ValidationResult:
        """Validate the dependency graph for issues."""
        circular_chains = self._find_circular_dependencies()
        
        return ValidationResult(
            has_circular_dependencies=len(circular_chains) > 0,
            circular_dependency_chains=circular_chains,
            missing_dependencies=[],  # Could be expanded to check for missing resources
            warnings=[]
        )
    
    def get_deployment_order(self, resources: List[Resource]) -> List[Resource]:
        """Calculate optimal deployment order based on dependencies."""
        # Use topological sort to order resources
        in_degree = defaultdict(int)
        adjacency_list = defaultdict(list)
        
        # Build adjacency list and calculate in-degrees
        for dep in self._dependencies:
            if dep.dependent in resources and dep.dependency in resources:
                adjacency_list[dep.dependency].append(dep.dependent)
                in_degree[dep.dependent] += 1
        
        # Initialize in-degree for all resources
        for resource in resources:
            if resource not in in_degree:
                in_degree[resource] = 0
        
        # Topological sort using Kahn's algorithm
        queue = deque([resource for resource in resources if in_degree[resource] == 0])
        deployment_order = []
        
        while queue:
            resource = queue.popleft()
            deployment_order.append(resource)
            
            for dependent in adjacency_list[resource]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # If we couldn't order all resources, there might be circular dependencies
        if len(deployment_order) != len(resources):
            # Fall back to original order for remaining resources
            remaining = [r for r in resources if r not in deployment_order]
            deployment_order.extend(remaining)
        
        return deployment_order
    
    def _find_circular_dependencies(self) -> List[List[Resource]]:
        """Find circular dependency chains using DFS."""
        visited = set()
        rec_stack = set()
        circular_chains = []
        
        def dfs(resource: Resource, path: List[Resource]) -> bool:
            visited.add(resource)
            rec_stack.add(resource)
            current_path = path + [resource]
            
            for dep in self._dependencies_of[resource]:
                dependency = dep.dependency
                
                if dependency not in visited:
                    if dfs(dependency, current_path):
                        return True
                elif dependency in rec_stack:
                    # Found a cycle
                    cycle_start = current_path.index(dependency)
                    circular_chains.append(current_path[cycle_start:] + [dependency])
                    return True
            
            rec_stack.remove(resource)
            return False
        
        # Check all resources
        all_resources = set()
        for dep in self._dependencies:
            all_resources.add(dep.dependent)
            all_resources.add(dep.dependency)
        
        for resource in all_resources:
            if resource not in visited:
                dfs(resource, [])
        
        return circular_chains