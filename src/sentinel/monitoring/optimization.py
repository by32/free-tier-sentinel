"""Advanced optimization algorithms for resource planning."""

import random
import math
import copy
from enum import Enum
from typing import List, Tuple
from dataclasses import dataclass

from sentinel.models.core import Resource, Plan


class OptimizationObjective(Enum):
    """Optimization objectives for multi-objective optimization."""
    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_PERFORMANCE = "maximize_performance"
    MAXIMIZE_AVAILABILITY = "maximize_availability"
    MINIMIZE_CARBON_FOOTPRINT = "minimize_carbon"


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    original_plan: Plan
    optimized_plan: Plan
    improvement_score: float
    iterations: int
    convergence_achieved: bool


class GeneticAlgorithmOptimizer:
    """Genetic algorithm optimizer for resource planning."""
    
    def __init__(self, population_size: int = 50, generations: int = 100, 
                 mutation_rate: float = 0.1, crossover_rate: float = 0.8):
        """Initialize the genetic algorithm optimizer."""
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
    
    def optimize_plan(self, plan: Plan) -> Plan:
        """Optimize a deployment plan using genetic algorithm."""
        # Initialize population with variations of the original plan
        population = self._initialize_population(plan)
        
        for generation in range(self.generations):
            # Evaluate fitness for each individual
            fitness_scores = [self.fitness_function(individual) for individual in population]
            
            # Select parents for reproduction
            parents = self._selection(population, fitness_scores)
            
            # Create new generation
            new_population = []
            for i in range(0, len(parents), 2):
                parent1 = parents[i]
                parent2 = parents[i + 1] if i + 1 < len(parents) else parents[0]
                
                # Crossover
                if random.random() < self.crossover_rate:
                    child1, child2 = self._crossover(parent1, parent2)
                else:
                    child1, child2 = parent1, parent2
                
                # Mutation
                if random.random() < self.mutation_rate:
                    child1 = self._mutate(child1)
                if random.random() < self.mutation_rate:
                    child2 = self._mutate(child2)
                
                new_population.extend([child1, child2])
            
            population = new_population[:self.population_size]
        
        # Return best individual
        fitness_scores = [self.fitness_function(individual) for individual in population]
        best_index = fitness_scores.index(max(fitness_scores))
        best_plan = population[best_index]
        
        # Ensure the plan has a proper name
        best_plan.name = f"optimized-{plan.name}"
        
        return best_plan
    
    def fitness_function(self, plan: Plan) -> float:
        """Calculate fitness score for a plan."""
        score = 0.0
        
        for resource in plan.resources:
            # Prefer free-tier resources
            if resource.resource_type in ["t2.micro", "t3.micro", "e2-micro", "f1-micro"]:
                score += 10.0
            
            # Prefer optimal quantities
            if resource.quantity == 1:
                score += 5.0
            elif resource.quantity <= 3:
                score += 2.0
            
            # Prefer reasonable usage levels
            if 50 <= resource.estimated_monthly_usage <= 200:
                score += 3.0
        
        return score
    
    def _initialize_population(self, plan: Plan) -> List[Plan]:
        """Initialize population with plan variations."""
        population = [copy.deepcopy(plan)]
        
        free_tier_types = {
            "ec2": ["t2.micro", "t3.micro"],
            "compute": ["e2-micro", "f1-micro"],
            "vm": ["Standard_B1s"]
        }
        
        for _ in range(self.population_size - 1):
            individual = copy.deepcopy(plan)
            
            # Randomly modify resources
            for resource in individual.resources:
                # Change resource type to free-tier alternatives
                if resource.service in free_tier_types:
                    resource.resource_type = random.choice(free_tier_types[resource.service])
                
                # Adjust quantities
                if random.random() < 0.3:
                    resource.quantity = random.randint(1, 3)
                
                # Adjust usage
                if random.random() < 0.3:
                    resource.estimated_monthly_usage = random.randint(50, 200)
            
            population.append(individual)
        
        return population
    
    def _selection(self, population: List[Plan], fitness_scores: List[float]) -> List[Plan]:
        """Select parents using tournament selection."""
        parents = []
        tournament_size = 3
        
        for _ in range(self.population_size):
            tournament_indices = random.sample(range(len(population)), tournament_size)
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            winner_index = tournament_indices[tournament_fitness.index(max(tournament_fitness))]
            parents.append(copy.deepcopy(population[winner_index]))
        
        return parents
    
    def _crossover(self, parent1: Plan, parent2: Plan) -> Tuple[Plan, Plan]:
        """Perform crossover between two plans."""
        child1 = copy.deepcopy(parent1)
        child2 = copy.deepcopy(parent2)
        
        # Simple crossover: exchange some resources
        if len(child1.resources) > 1 and len(child2.resources) > 1:
            crossover_point = random.randint(1, min(len(child1.resources), len(child2.resources)) - 1)
            
            # Exchange resources after crossover point
            child1.resources[crossover_point:], child2.resources[crossover_point:] = \
                child2.resources[crossover_point:], child1.resources[crossover_point:]
        
        return child1, child2
    
    def _mutate(self, plan: Plan) -> Plan:
        """Mutate a plan."""
        mutated = copy.deepcopy(plan)
        
        if mutated.resources:
            resource = random.choice(mutated.resources)
            
            # Mutate resource type
            if random.random() < 0.5:
                if resource.service == "ec2":
                    resource.resource_type = random.choice(["t2.micro", "t3.micro"])
                elif resource.service == "compute":
                    resource.resource_type = random.choice(["e2-micro", "f1-micro"])
            
            # Mutate quantity
            if random.random() < 0.3:
                resource.quantity = random.randint(1, 3)
            
            # Mutate usage
            if random.random() < 0.3:
                resource.estimated_monthly_usage = random.randint(50, 200)
        
        return mutated


class SimulatedAnnealingOptimizer:
    """Simulated annealing optimizer for resource planning."""
    
    def __init__(self, initial_temperature: float = 100.0, cooling_rate: float = 0.95, 
                 min_temperature: float = 0.1):
        """Initialize the simulated annealing optimizer."""
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.min_temperature = min_temperature
    
    def optimize_plan(self, plan: Plan) -> Plan:
        """Optimize a deployment plan using simulated annealing."""
        current_plan = copy.deepcopy(plan)
        best_plan = copy.deepcopy(plan)
        
        current_cost = self._calculate_cost(current_plan)
        best_cost = current_cost
        
        temperature = self.initial_temperature
        
        while temperature > self.min_temperature:
            # Generate neighbor solution
            neighbor_plan = self._generate_neighbor(current_plan)
            neighbor_cost = self._calculate_cost(neighbor_plan)
            
            # Accept or reject the neighbor
            if (neighbor_cost < current_cost or 
                random.random() < self.acceptance_probability(current_cost, neighbor_cost, temperature)):
                current_plan = neighbor_plan
                current_cost = neighbor_cost
                
                # Update best solution
                if current_cost < best_cost:
                    best_plan = copy.deepcopy(current_plan)
                    best_cost = current_cost
            
            # Cool down
            temperature *= self.cooling_rate
        
        best_plan.name = f"optimized-{plan.name}"
        return best_plan
    
    def acceptance_probability(self, current_cost: float, neighbor_cost: float, temperature: float) -> float:
        """Calculate acceptance probability for worse solutions."""
        if neighbor_cost < current_cost:
            return 1.0
        return math.exp(-(neighbor_cost - current_cost) / temperature)
    
    def _calculate_cost(self, plan: Plan) -> float:
        """Calculate cost metric for a plan."""
        total_cost = 0.0
        
        cost_map = {
            "t2.micro": 0.0116,
            "t3.micro": 0.0104,
            "t2.small": 0.023,
            "e2-micro": 0.0104,
            "f1-micro": 0.0084
        }
        
        for resource in plan.resources:
            hourly_rate = cost_map.get(resource.resource_type, 0.02)
            total_cost += hourly_rate * resource.estimated_monthly_usage * resource.quantity
        
        return total_cost
    
    def _generate_neighbor(self, plan: Plan) -> Plan:
        """Generate a neighbor solution."""
        neighbor = copy.deepcopy(plan)
        
        if neighbor.resources:
            resource = random.choice(neighbor.resources)
            
            modification = random.choice(["type", "quantity", "usage"])
            
            if modification == "type" and resource.service == "ec2":
                resource.resource_type = random.choice(["t2.micro", "t3.micro", "t2.small"])
            elif modification == "quantity":
                resource.quantity = max(1, resource.quantity + random.choice([-1, 1]))
            elif modification == "usage":
                resource.estimated_monthly_usage = max(50, 
                    resource.estimated_monthly_usage + random.randint(-20, 20))
        
        return neighbor


class MultiObjectiveOptimizer:
    """Multi-objective optimizer using NSGA-II algorithm."""
    
    def __init__(self, objectives: List[OptimizationObjective]):
        """Initialize multi-objective optimizer."""
        self.objectives = objectives
    
    def optimize_plan(self, plan: Plan) -> List[Plan]:
        """Optimize plan for multiple objectives, returning Pareto front."""
        # Simple implementation - in reality, this would use NSGA-II
        solutions = []
        
        # Generate variations focusing on different objectives
        for objective in self.objectives:
            solution = self._optimize_for_objective(plan, objective)
            solutions.append(solution)
        
        # Add some balanced solutions
        balanced_solution = copy.deepcopy(plan)
        balanced_solution.name = f"balanced-{plan.name}"
        solutions.append(balanced_solution)
        
        return solutions
    
    def _optimize_for_objective(self, plan: Plan, objective: OptimizationObjective) -> Plan:
        """Optimize plan for a specific objective."""
        optimized = copy.deepcopy(plan)
        optimized.name = f"{objective.value}-{plan.name}"
        
        if objective == OptimizationObjective.MINIMIZE_COST:
            # Use free-tier resources
            for resource in optimized.resources:
                if resource.service == "ec2":
                    resource.resource_type = "t2.micro"
                elif resource.service == "compute":
                    resource.resource_type = "e2-micro"
                resource.quantity = 1
        
        elif objective == OptimizationObjective.MAXIMIZE_PERFORMANCE:
            # Use slightly better instance types
            for resource in optimized.resources:
                if resource.service == "ec2":
                    resource.resource_type = "t3.micro"
                elif resource.service == "compute":
                    resource.resource_type = "e2-micro"
        
        elif objective == OptimizationObjective.MAXIMIZE_AVAILABILITY:
            # Increase quantities for redundancy
            for resource in optimized.resources:
                resource.quantity = min(3, resource.quantity + 1)
        
        return optimized