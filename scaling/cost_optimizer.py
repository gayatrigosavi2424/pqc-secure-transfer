"""
Cost optimization and resource management for PQC Secure Transfer auto-scaling.
Optimizes costs through spot instances, right-sizing, and intelligent scheduling.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)


class InstanceType(Enum):
    """Types of compute instances."""
    ON_DEMAND = "on_demand"
    SPOT = "spot"
    RESERVED = "reserved"


@dataclass
class InstanceSpec:
    """Specification for a compute instance."""
    instance_type: str  # e.g., "t3.medium", "c5.large"
    vcpus: int
    memory_gb: float
    network_performance: str
    cost_per_hour: float
    spot_cost_per_hour: Optional[float] = None
    availability_zones: List[str] = field(default_factory=list)
    
    def get_cost(self, instance_pricing: InstanceType) -> float:
        """Get cost per hour for the specified pricing model."""
        if instance_pricing == InstanceType.SPOT and self.spot_cost_per_hour:
            return self.spot_cost_per_hour
        return self.cost_per_hour


@dataclass
class CostOptimizationPolicy:
    """Policy for cost optimization decisions."""
    # Spot instance configuration
    max_spot_percentage: float = 0.7  # Max 70% spot instances
    spot_interruption_tolerance: float = 0.1  # 10% interruption rate tolerance
    
    # Instance type preferences
    preferred_instance_families: List[str] = field(default_factory=lambda: ["t3", "c5", "m5"])
    min_vcpus_per_instance: int = 1
    max_vcpus_per_instance: int = 16
    
    # Cost thresholds
    max_hourly_cost: Optional[float] = None
    cost_increase_threshold: float = 0.2  # 20% cost increase threshold
    
    # Scheduling preferences
    enable_scheduled_scaling: bool = True
    low_cost_hours: List[int] = field(default_factory=lambda: [2, 3, 4, 5, 6])  # 2-6 AM
    high_cost_hours: List[int] = field(default_factory=lambda: [9, 10, 11, 17, 18, 19])  # Business hours
    
    # Resource right-sizing
    enable_right_sizing: bool = True
    cpu_utilization_target: float = 70.0
    memory_utilization_target: float = 80.0
    right_sizing_evaluation_days: int = 7


@dataclass
class CostRecommendation:
    """Cost optimization recommendation."""
    recommendation_id: str
    recommendation_type: str
    description: str
    current_cost_per_hour: float
    optimized_cost_per_hour: float
    potential_savings_percent: float
    confidence: float
    implementation_complexity: str  # "low", "medium", "high"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'recommendation_id': self.recommendation_id,
            'recommendation_type': self.recommendation_type,
            'description': self.description,
            'current_cost_per_hour': self.current_cost_per_hour,
            'optimized_cost_per_hour': self.optimized_cost_per_hour,
            'potential_savings_percent': self.potential_savings_percent,
            'confidence': self.confidence,
            'implementation_complexity': self.implementation_complexity,
            'metadata': self.metadata
        }


class InstanceCatalog:
    """Catalog of available instance types and their specifications."""
    
    def __init__(self):
        # AWS instance specifications (simplified)
        self.instances = {
            "t3.micro": InstanceSpec("t3.micro", 2, 1.0, "Low to Moderate", 0.0104, 0.0031),
            "t3.small": InstanceSpec("t3.small", 2, 2.0, "Low to Moderate", 0.0208, 0.0062),
            "t3.medium": InstanceSpec("t3.medium", 2, 4.0, "Low to Moderate", 0.0416, 0.0125),
            "t3.large": InstanceSpec("t3.large", 2, 8.0, "Low to Moderate", 0.0832, 0.0250),
            "c5.large": InstanceSpec("c5.large", 2, 4.0, "Up to 10 Gigabit", 0.085, 0.0255),
            "c5.xlarge": InstanceSpec("c5.xlarge", 4, 8.0, "Up to 10 Gigabit", 0.17, 0.051),
            "c5.2xlarge": InstanceSpec("c5.2xlarge", 8, 16.0, "Up to 10 Gigabit", 0.34, 0.102),
            "m5.large": InstanceSpec("m5.large", 2, 8.0, "Up to 10 Gigabit", 0.096, 0.0288),
            "m5.xlarge": InstanceSpec("m5.xlarge", 4, 16.0, "Up to 10 Gigabit", 0.192, 0.0576),
            "m5.2xlarge": InstanceSpec("m5.2xlarge", 8, 32.0, "Up to 10 Gigabit", 0.384, 0.1152),
        }
        
        logger.info(f"Instance catalog initialized with {len(self.instances)} instance types")
    
    def get_instance(self, instance_type: str) -> Optional[InstanceSpec]:
        """Get instance specification by type."""
        return self.instances.get(instance_type)
    
    def find_suitable_instances(self, min_vcpus: int, min_memory_gb: float,
                               max_cost_per_hour: Optional[float] = None) -> List[InstanceSpec]:
        """Find instances that meet the specified requirements."""
        suitable = []
        
        for instance in self.instances.values():
            if (instance.vcpus >= min_vcpus and 
                instance.memory_gb >= min_memory_gb):
                
                if max_cost_per_hour is None or instance.cost_per_hour <= max_cost_per_hour:
                    suitable.append(instance)
        
        # Sort by cost efficiency (performance per dollar)
        suitable.sort(key=lambda x: (x.vcpus + x.memory_gb) / x.cost_per_hour, reverse=True)
        
        return suitable
    
    def get_cost_efficient_alternative(self, current_type: str, 
                                     target_vcpus: int, target_memory_gb: float) -> Optional[InstanceSpec]:
        """Find a more cost-efficient alternative to the current instance type."""
        current = self.get_instance(current_type)
        if not current:
            return None
        
        alternatives = self.find_suitable_instances(target_vcpus, target_memory_gb)
        
        # Find alternatives that are more cost-efficient
        for alt in alternatives:
            if (alt.instance_type != current_type and 
                alt.cost_per_hour < current.cost_per_hour):
                return alt
        
        return None


class SpotInstanceManager:
    """Manages spot instance recommendations and interruption handling."""
    
    def __init__(self, policy: CostOptimizationPolicy):
        self.policy = policy
        self.spot_price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self.interruption_history: Dict[str, List[datetime]] = {}
    
    def update_spot_prices(self, instance_type: str, price: float):
        """Update spot price history for an instance type."""
        if instance_type not in self.spot_price_history:
            self.spot_price_history[instance_type] = []
        
        self.spot_price_history[instance_type].append((datetime.utcnow(), price))
        
        # Keep only recent history (last 7 days)
        cutoff = datetime.utcnow() - timedelta(days=7)
        self.spot_price_history[instance_type] = [
            (ts, price) for ts, price in self.spot_price_history[instance_type]
            if ts > cutoff
        ]
    
    def record_spot_interruption(self, instance_type: str):
        """Record a spot instance interruption."""
        if instance_type not in self.interruption_history:
            self.interruption_history[instance_type] = []
        
        self.interruption_history[instance_type].append(datetime.utcnow())
        
        # Keep only recent history (last 30 days)
        cutoff = datetime.utcnow() - timedelta(days=30)
        self.interruption_history[instance_type] = [
            ts for ts in self.interruption_history[instance_type]
            if ts > cutoff
        ]
    
    def get_spot_interruption_rate(self, instance_type: str, days: int = 7) -> float:
        """Calculate spot interruption rate for an instance type."""
        if instance_type not in self.interruption_history:
            return 0.0
        
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_interruptions = [
            ts for ts in self.interruption_history[instance_type]
            if ts > cutoff
        ]
        
        # Estimate interruption rate (interruptions per day)
        return len(recent_interruptions) / days
    
    def is_spot_instance_suitable(self, instance_type: str, workload_criticality: str = "normal") -> bool:
        """Determine if spot instances are suitable for the workload."""
        interruption_rate = self.get_spot_interruption_rate(instance_type)
        
        # Adjust tolerance based on workload criticality
        tolerance = self.policy.spot_interruption_tolerance
        if workload_criticality == "critical":
            tolerance *= 0.5  # More strict for critical workloads
        elif workload_criticality == "low":
            tolerance *= 2.0  # More lenient for low-priority workloads
        
        return interruption_rate <= tolerance
    
    def recommend_spot_mix(self, total_instances: int, instance_type: str) -> Dict[str, int]:
        """Recommend optimal mix of spot and on-demand instances."""
        if not self.is_spot_instance_suitable(instance_type):
            return {"on_demand": total_instances, "spot": 0}
        
        max_spot = int(total_instances * self.policy.max_spot_percentage)
        min_on_demand = total_instances - max_spot
        
        return {
            "on_demand": min_on_demand,
            "spot": max_spot
        }


class ResourceRightSizer:
    """Analyzes resource utilization and recommends right-sizing."""
    
    def __init__(self, policy: CostOptimizationPolicy, instance_catalog: InstanceCatalog):
        self.policy = policy
        self.instance_catalog = instance_catalog
        self.utilization_history: List[Dict[str, Any]] = []
    
    def add_utilization_data(self, instance_type: str, cpu_utilization: float, 
                           memory_utilization: float, timestamp: Optional[datetime] = None):
        """Add utilization data for analysis."""
        self.utilization_history.append({
            'timestamp': timestamp or datetime.utcnow(),
            'instance_type': instance_type,
            'cpu_utilization': cpu_utilization,
            'memory_utilization': memory_utilization
        })
        
        # Keep only recent history
        cutoff = datetime.utcnow() - timedelta(days=self.policy.right_sizing_evaluation_days)
        self.utilization_history = [
            data for data in self.utilization_history
            if data['timestamp'] > cutoff
        ]
    
    def analyze_right_sizing_opportunity(self, instance_type: str) -> Optional[CostRecommendation]:
        """Analyze if the instance type can be right-sized."""
        if not self.utilization_history:
            return None
        
        # Filter data for this instance type
        instance_data = [
            data for data in self.utilization_history
            if data['instance_type'] == instance_type
        ]
        
        if len(instance_data) < 10:  # Need sufficient data
            return None
        
        # Calculate average utilization
        avg_cpu = sum(data['cpu_utilization'] for data in instance_data) / len(instance_data)
        avg_memory = sum(data['memory_utilization'] for data in instance_data) / len(instance_data)
        
        current_instance = self.instance_catalog.get_instance(instance_type)
        if not current_instance:
            return None
        
        # Check if we can downsize
        if (avg_cpu < self.policy.cpu_utilization_target * 0.6 and 
            avg_memory < self.policy.memory_utilization_target * 0.6):
            
            # Find smaller instance
            target_vcpus = max(1, int(current_instance.vcpus * avg_cpu / self.policy.cpu_utilization_target))
            target_memory = max(1, current_instance.memory_gb * avg_memory / self.policy.memory_utilization_target)
            
            alternative = self.instance_catalog.get_cost_efficient_alternative(
                instance_type, target_vcpus, target_memory
            )
            
            if alternative and alternative.cost_per_hour < current_instance.cost_per_hour:
                savings_percent = ((current_instance.cost_per_hour - alternative.cost_per_hour) / 
                                 current_instance.cost_per_hour) * 100
                
                return CostRecommendation(
                    recommendation_id=f"rightsize_{instance_type}_{int(datetime.utcnow().timestamp())}",
                    recommendation_type="right_sizing",
                    description=f"Downsize from {instance_type} to {alternative.instance_type}",
                    current_cost_per_hour=current_instance.cost_per_hour,
                    optimized_cost_per_hour=alternative.cost_per_hour,
                    potential_savings_percent=savings_percent,
                    confidence=0.8,
                    implementation_complexity="medium",
                    metadata={
                        'current_instance': instance_type,
                        'recommended_instance': alternative.instance_type,
                        'avg_cpu_utilization': avg_cpu,
                        'avg_memory_utilization': avg_memory,
                        'data_points': len(instance_data)
                    }
                )
        
        return None


class CostOptimizer:
    """Main cost optimization engine."""
    
    def __init__(self, policy: Optional[CostOptimizationPolicy] = None):
        self.policy = policy or CostOptimizationPolicy()
        self.instance_catalog = InstanceCatalog()
        self.spot_manager = SpotInstanceManager(self.policy)
        self.right_sizer = ResourceRightSizer(self.policy, self.instance_catalog)
        self.recommendations: List[CostRecommendation] = []
        
        logger.info("Cost optimizer initialized")
    
    def add_utilization_data(self, instance_type: str, cpu_utilization: float, 
                           memory_utilization: float):
        """Add utilization data for cost optimization analysis."""
        self.right_sizer.add_utilization_data(instance_type, cpu_utilization, memory_utilization)
    
    def update_spot_prices(self, spot_prices: Dict[str, float]):
        """Update spot price information."""
        for instance_type, price in spot_prices.items():
            self.spot_manager.update_spot_prices(instance_type, price)
    
    async def generate_cost_recommendations(self, current_deployment: Dict[str, Any]) -> List[CostRecommendation]:
        """Generate cost optimization recommendations."""
        recommendations = []
        
        current_instance_type = current_deployment.get('instance_type', 't3.medium')
        current_instance_count = current_deployment.get('instance_count', 2)
        
        # Right-sizing recommendation
        right_sizing_rec = self.right_sizer.analyze_right_sizing_opportunity(current_instance_type)
        if right_sizing_rec:
            recommendations.append(right_sizing_rec)
        
        # Spot instance recommendation
        spot_rec = self._generate_spot_recommendation(current_instance_type, current_instance_count)
        if spot_rec:
            recommendations.append(spot_rec)
        
        # Scheduled scaling recommendation
        scheduled_rec = self._generate_scheduled_scaling_recommendation(current_deployment)
        if scheduled_rec:
            recommendations.append(scheduled_rec)
        
        # Instance family optimization
        family_rec = self._generate_instance_family_recommendation(current_instance_type)
        if family_rec:
            recommendations.append(family_rec)
        
        self.recommendations.extend(recommendations)
        
        # Keep only recent recommendations
        cutoff = datetime.utcnow() - timedelta(days=30)
        self.recommendations = [
            rec for rec in self.recommendations
            if datetime.fromisoformat(rec.recommendation_id.split('_')[-1]) > cutoff.timestamp()
        ]
        
        logger.info(f"Generated {len(recommendations)} cost optimization recommendations")
        return recommendations
    
    def _generate_spot_recommendation(self, instance_type: str, instance_count: int) -> Optional[CostRecommendation]:
        """Generate spot instance recommendation."""
        if not self.spot_manager.is_spot_instance_suitable(instance_type):
            return None
        
        instance_spec = self.instance_catalog.get_instance(instance_type)
        if not instance_spec or not instance_spec.spot_cost_per_hour:
            return None
        
        spot_mix = self.spot_manager.recommend_spot_mix(instance_count, instance_type)
        
        current_cost = instance_count * instance_spec.cost_per_hour
        optimized_cost = (spot_mix['on_demand'] * instance_spec.cost_per_hour + 
                         spot_mix['spot'] * instance_spec.spot_cost_per_hour)
        
        if optimized_cost < current_cost:
            savings_percent = ((current_cost - optimized_cost) / current_cost) * 100
            
            return CostRecommendation(
                recommendation_id=f"spot_{instance_type}_{int(datetime.utcnow().timestamp())}",
                recommendation_type="spot_instances",
                description=f"Use {spot_mix['spot']} spot instances and {spot_mix['on_demand']} on-demand",
                current_cost_per_hour=current_cost,
                optimized_cost_per_hour=optimized_cost,
                potential_savings_percent=savings_percent,
                confidence=0.7,
                implementation_complexity="low",
                metadata={
                    'spot_instances': spot_mix['spot'],
                    'on_demand_instances': spot_mix['on_demand'],
                    'interruption_rate': self.spot_manager.get_spot_interruption_rate(instance_type)
                }
            )
        
        return None
    
    def _generate_scheduled_scaling_recommendation(self, current_deployment: Dict[str, Any]) -> Optional[CostRecommendation]:
        """Generate scheduled scaling recommendation."""
        if not self.policy.enable_scheduled_scaling:
            return None
        
        current_hour = datetime.utcnow().hour
        instance_count = current_deployment.get('instance_count', 2)
        instance_type = current_deployment.get('instance_type', 't3.medium')
        
        instance_spec = self.instance_catalog.get_instance(instance_type)
        if not instance_spec:
            return None
        
        # Recommend scaling down during low-cost hours
        if current_hour in self.policy.low_cost_hours and instance_count > 1:
            reduced_instances = max(1, int(instance_count * 0.5))
            current_cost = instance_count * instance_spec.cost_per_hour
            optimized_cost = reduced_instances * instance_spec.cost_per_hour
            savings_percent = ((current_cost - optimized_cost) / current_cost) * 100
            
            return CostRecommendation(
                recommendation_id=f"scheduled_{instance_type}_{int(datetime.utcnow().timestamp())}",
                recommendation_type="scheduled_scaling",
                description=f"Scale down to {reduced_instances} instances during low-demand hours",
                current_cost_per_hour=current_cost,
                optimized_cost_per_hour=optimized_cost,
                potential_savings_percent=savings_percent,
                confidence=0.6,
                implementation_complexity="medium",
                metadata={
                    'current_instances': instance_count,
                    'recommended_instances': reduced_instances,
                    'low_cost_hours': self.policy.low_cost_hours
                }
            )
        
        return None
    
    def _generate_instance_family_recommendation(self, current_instance_type: str) -> Optional[CostRecommendation]:
        """Generate instance family optimization recommendation."""
        current_instance = self.instance_catalog.get_instance(current_instance_type)
        if not current_instance:
            return None
        
        # Find more cost-efficient alternatives in preferred families
        alternatives = self.instance_catalog.find_suitable_instances(
            current_instance.vcpus, current_instance.memory_gb
        )
        
        for alt in alternatives:
            if (alt.instance_type != current_instance_type and
                alt.cost_per_hour < current_instance.cost_per_hour * 0.9):  # At least 10% savings
                
                savings_percent = ((current_instance.cost_per_hour - alt.cost_per_hour) / 
                                 current_instance.cost_per_hour) * 100
                
                return CostRecommendation(
                    recommendation_id=f"family_{current_instance_type}_{int(datetime.utcnow().timestamp())}",
                    recommendation_type="instance_family",
                    description=f"Switch from {current_instance_type} to {alt.instance_type}",
                    current_cost_per_hour=current_instance.cost_per_hour,
                    optimized_cost_per_hour=alt.cost_per_hour,
                    potential_savings_percent=savings_percent,
                    confidence=0.8,
                    implementation_complexity="low",
                    metadata={
                        'current_instance': current_instance_type,
                        'recommended_instance': alt.instance_type,
                        'performance_comparison': {
                            'vcpus': f"{current_instance.vcpus} -> {alt.vcpus}",
                            'memory_gb': f"{current_instance.memory_gb} -> {alt.memory_gb}"
                        }
                    }
                )
        
        return None
    
    def get_cost_summary(self, current_deployment: Dict[str, Any]) -> Dict[str, Any]:
        """Get current cost summary and optimization potential."""
        instance_type = current_deployment.get('instance_type', 't3.medium')
        instance_count = current_deployment.get('instance_count', 2)
        
        instance_spec = self.instance_catalog.get_instance(instance_type)
        if not instance_spec:
            return {'error': f'Unknown instance type: {instance_type}'}
        
        current_hourly_cost = instance_count * instance_spec.cost_per_hour
        current_monthly_cost = current_hourly_cost * 24 * 30  # Approximate
        
        # Calculate potential savings from recommendations
        total_potential_savings = 0.0
        for rec in self.recommendations:
            if rec.recommendation_type in ['spot_instances', 'right_sizing', 'instance_family']:
                savings = current_hourly_cost - rec.optimized_cost_per_hour
                total_potential_savings += max(0, savings)
        
        return {
            'current_hourly_cost': current_hourly_cost,
            'current_monthly_cost': current_monthly_cost,
            'potential_hourly_savings': total_potential_savings,
            'potential_monthly_savings': total_potential_savings * 24 * 30,
            'optimization_opportunities': len(self.recommendations),
            'instance_details': {
                'type': instance_type,
                'count': instance_count,
                'vcpus_per_instance': instance_spec.vcpus,
                'memory_gb_per_instance': instance_spec.memory_gb,
                'cost_per_hour_per_instance': instance_spec.cost_per_hour
            }
        }


# Global cost optimizer instance
_cost_optimizer: Optional[CostOptimizer] = None


def initialize_cost_optimizer(policy: Optional[CostOptimizationPolicy] = None) -> CostOptimizer:
    """Initialize the global cost optimizer."""
    global _cost_optimizer
    _cost_optimizer = CostOptimizer(policy)
    logger.info("Cost optimizer initialized")
    return _cost_optimizer


def get_cost_optimizer() -> Optional[CostOptimizer]:
    """Get the global cost optimizer instance."""
    return _cost_optimizer