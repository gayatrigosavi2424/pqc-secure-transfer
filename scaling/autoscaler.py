"""
Intelligent auto-scaling system for PQC Secure Transfer.
Provides metrics-based scaling optimized for large file transfer workloads and federated learning patterns.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import statistics
import math

from monitoring.pqc_metrics_integration import get_metrics_integration, update_queue_length
from monitoring.metrics import get_metrics_collector

logger = logging.getLogger(__name__)


class ScalingDirection(Enum):
    """Direction of scaling operation."""
    UP = "up"
    DOWN = "down"
    NONE = "none"


class ScalingReason(Enum):
    """Reason for scaling decision."""
    CPU_HIGH = "cpu_high"
    CPU_LOW = "cpu_low"
    MEMORY_HIGH = "memory_high"
    MEMORY_LOW = "memory_low"
    QUEUE_LENGTH = "queue_length"
    ACTIVE_TRANSFERS = "active_transfers"
    THROUGHPUT_LOW = "throughput_low"
    PREDICTIVE = "predictive"
    COST_OPTIMIZATION = "cost_optimization"
    MANUAL = "manual"


@dataclass
class ScalingMetrics:
    """Current system metrics for scaling decisions."""
    timestamp: datetime
    cpu_utilization: float
    memory_utilization: float
    active_transfers: int
    queue_length: int
    throughput_mbps: float
    error_rate: float
    response_time_ms: float
    current_instances: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'cpu_utilization': self.cpu_utilization,
            'memory_utilization': self.memory_utilization,
            'active_transfers': self.active_transfers,
            'queue_length': self.queue_length,
            'throughput_mbps': self.throughput_mbps,
            'error_rate': self.error_rate,
            'response_time_ms': self.response_time_ms,
            'current_instances': self.current_instances
        }


@dataclass
class ScalingPolicy:
    """Configuration for scaling policies."""
    # CPU thresholds
    cpu_scale_up_threshold: float = 70.0
    cpu_scale_down_threshold: float = 30.0
    
    # Memory thresholds
    memory_scale_up_threshold: float = 80.0
    memory_scale_down_threshold: float = 40.0
    
    # Transfer-specific thresholds
    max_active_transfers_per_instance: int = 10
    max_queue_length: int = 20
    min_throughput_mbps: float = 50.0
    
    # Instance limits
    min_instances: int = 1
    max_instances: int = 50
    
    # Scaling behavior
    scale_up_cooldown_seconds: int = 300  # 5 minutes
    scale_down_cooldown_seconds: int = 600  # 10 minutes
    evaluation_periods: int = 3  # Number of periods to evaluate
    
    # Cost optimization
    enable_cost_optimization: bool = True
    preferred_instance_types: List[str] = field(default_factory=lambda: ["t3.medium", "t3.large"])
    spot_instance_percentage: float = 0.7  # 70% spot instances
    
    def validate(self) -> List[str]:
        """Validate scaling policy configuration."""
        errors = []
        
        if self.cpu_scale_up_threshold <= self.cpu_scale_down_threshold:
            errors.append("CPU scale up threshold must be higher than scale down threshold")
        
        if self.memory_scale_up_threshold <= self.memory_scale_down_threshold:
            errors.append("Memory scale up threshold must be higher than scale down threshold")
        
        if self.min_instances < 1:
            errors.append("Minimum instances must be at least 1")
        
        if self.max_instances <= self.min_instances:
            errors.append("Maximum instances must be greater than minimum instances")
        
        if self.scale_up_cooldown_seconds < 60:
            errors.append("Scale up cooldown must be at least 60 seconds")
        
        if self.scale_down_cooldown_seconds < self.scale_up_cooldown_seconds:
            errors.append("Scale down cooldown should be longer than scale up cooldown")
        
        return errors


@dataclass
class ScalingDecision:
    """Represents a scaling decision."""
    timestamp: datetime
    direction: ScalingDirection
    reason: ScalingReason
    current_instances: int
    target_instances: int
    confidence: float  # 0.0 to 1.0
    metrics: ScalingMetrics
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'direction': self.direction.value,
            'reason': self.reason.value,
            'current_instances': self.current_instances,
            'target_instances': self.target_instances,
            'confidence': self.confidence,
            'metrics': self.metrics.to_dict(),
            'metadata': self.metadata
        }


class MetricsCollector:
    """Collects current system metrics for scaling decisions."""
    
    def __init__(self):
        self.metrics_integration = get_metrics_integration()
        self.metrics_collector = get_metrics_collector()
    
    async def collect_current_metrics(self) -> ScalingMetrics:
        """Collect current system metrics."""
        try:
            # Get metrics from Prometheus/monitoring system
            # In a real implementation, this would query Prometheus
            # For now, we'll simulate with reasonable values
            
            current_time = datetime.utcnow()
            
            # Simulate metric collection
            # In production, these would come from actual monitoring
            cpu_utilization = await self._get_cpu_utilization()
            memory_utilization = await self._get_memory_utilization()
            active_transfers = await self._get_active_transfers()
            queue_length = await self._get_queue_length()
            throughput_mbps = await self._get_throughput()
            error_rate = await self._get_error_rate()
            response_time_ms = await self._get_response_time()
            current_instances = await self._get_current_instances()
            
            return ScalingMetrics(
                timestamp=current_time,
                cpu_utilization=cpu_utilization,
                memory_utilization=memory_utilization,
                active_transfers=active_transfers,
                queue_length=queue_length,
                throughput_mbps=throughput_mbps,
                error_rate=error_rate,
                response_time_ms=response_time_ms,
                current_instances=current_instances
            )
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            # Return default metrics
            return ScalingMetrics(
                timestamp=datetime.utcnow(),
                cpu_utilization=50.0,
                memory_utilization=50.0,
                active_transfers=5,
                queue_length=0,
                throughput_mbps=100.0,
                error_rate=0.0,
                response_time_ms=100.0,
                current_instances=2
            )
    
    async def _get_cpu_utilization(self) -> float:
        """Get current CPU utilization percentage."""
        # Simulate CPU utilization
        import random
        return random.uniform(20.0, 90.0)
    
    async def _get_memory_utilization(self) -> float:
        """Get current memory utilization percentage."""
        # Simulate memory utilization
        import random
        return random.uniform(30.0, 85.0)
    
    async def _get_active_transfers(self) -> int:
        """Get number of active file transfers."""
        # Simulate active transfers
        import random
        return random.randint(0, 25)
    
    async def _get_queue_length(self) -> int:
        """Get current transfer queue length."""
        # Simulate queue length
        import random
        return random.randint(0, 15)
    
    async def _get_throughput(self) -> float:
        """Get current throughput in MB/s."""
        # Simulate throughput
        import random
        return random.uniform(30.0, 150.0)
    
    async def _get_error_rate(self) -> float:
        """Get current error rate percentage."""
        # Simulate error rate
        import random
        return random.uniform(0.0, 5.0)
    
    async def _get_response_time(self) -> float:
        """Get current response time in milliseconds."""
        # Simulate response time
        import random
        return random.uniform(50.0, 500.0)
    
    async def _get_current_instances(self) -> int:
        """Get current number of running instances."""
        # Simulate current instances
        import random
        return random.randint(1, 10)


class ScalingEngine:
    """Core scaling decision engine."""
    
    def __init__(self, policy: ScalingPolicy):
        self.policy = policy
        self.metrics_history: List[ScalingMetrics] = []
        self.scaling_history: List[ScalingDecision] = []
        self.last_scale_up_time: Optional[datetime] = None
        self.last_scale_down_time: Optional[datetime] = None
        
        # Validate policy
        errors = policy.validate()
        if errors:
            raise ValueError(f"Invalid scaling policy: {errors}")
        
        logger.info("Scaling engine initialized")
    
    def add_metrics(self, metrics: ScalingMetrics):
        """Add metrics to history for decision making."""
        self.metrics_history.append(metrics)
        
        # Keep only recent metrics (last hour)
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        self.metrics_history = [
            m for m in self.metrics_history 
            if m.timestamp > cutoff_time
        ]
    
    def make_scaling_decision(self, current_metrics: ScalingMetrics) -> ScalingDecision:
        """Make a scaling decision based on current and historical metrics."""
        self.add_metrics(current_metrics)
        
        # Check cooldown periods
        now = datetime.utcnow()
        
        if self.last_scale_up_time:
            time_since_scale_up = (now - self.last_scale_up_time).total_seconds()
            if time_since_scale_up < self.policy.scale_up_cooldown_seconds:
                return self._no_scaling_decision(current_metrics, "Scale up cooldown active")
        
        if self.last_scale_down_time:
            time_since_scale_down = (now - self.last_scale_down_time).total_seconds()
            if time_since_scale_down < self.policy.scale_down_cooldown_seconds:
                return self._no_scaling_decision(current_metrics, "Scale down cooldown active")
        
        # Evaluate scaling conditions
        scale_up_reasons = self._evaluate_scale_up_conditions(current_metrics)
        scale_down_reasons = self._evaluate_scale_down_conditions(current_metrics)
        
        # Prioritize scale up over scale down
        if scale_up_reasons:
            return self._create_scale_up_decision(current_metrics, scale_up_reasons)
        elif scale_down_reasons:
            return self._create_scale_down_decision(current_metrics, scale_down_reasons)
        else:
            return self._no_scaling_decision(current_metrics, "No scaling conditions met")
    
    def _evaluate_scale_up_conditions(self, metrics: ScalingMetrics) -> List[ScalingReason]:
        """Evaluate conditions that would trigger scale up."""
        reasons = []
        
        # Check if we're already at max instances
        if metrics.current_instances >= self.policy.max_instances:
            return []
        
        # CPU threshold
        if metrics.cpu_utilization > self.policy.cpu_scale_up_threshold:
            reasons.append(ScalingReason.CPU_HIGH)
        
        # Memory threshold
        if metrics.memory_utilization > self.policy.memory_scale_up_threshold:
            reasons.append(ScalingReason.MEMORY_HIGH)
        
        # Active transfers per instance
        transfers_per_instance = metrics.active_transfers / max(metrics.current_instances, 1)
        if transfers_per_instance > self.policy.max_active_transfers_per_instance:
            reasons.append(ScalingReason.ACTIVE_TRANSFERS)
        
        # Queue length
        if metrics.queue_length > self.policy.max_queue_length:
            reasons.append(ScalingReason.QUEUE_LENGTH)
        
        # Low throughput (might indicate overload)
        if metrics.throughput_mbps < self.policy.min_throughput_mbps:
            reasons.append(ScalingReason.THROUGHPUT_LOW)
        
        return reasons
    
    def _evaluate_scale_down_conditions(self, metrics: ScalingMetrics) -> List[ScalingReason]:
        """Evaluate conditions that would trigger scale down."""
        reasons = []
        
        # Check if we're already at min instances
        if metrics.current_instances <= self.policy.min_instances:
            return []
        
        # Need sustained low utilization for scale down
        if len(self.metrics_history) < self.policy.evaluation_periods:
            return []
        
        recent_metrics = self.metrics_history[-self.policy.evaluation_periods:]
        
        # CPU consistently low
        avg_cpu = statistics.mean(m.cpu_utilization for m in recent_metrics)
        if avg_cpu < self.policy.cpu_scale_down_threshold:
            reasons.append(ScalingReason.CPU_LOW)
        
        # Memory consistently low
        avg_memory = statistics.mean(m.memory_utilization for m in recent_metrics)
        if avg_memory < self.policy.memory_scale_down_threshold:
            reasons.append(ScalingReason.MEMORY_LOW)
        
        # Low transfer activity
        max_transfers = max(m.active_transfers for m in recent_metrics)
        transfers_per_instance = max_transfers / max(metrics.current_instances, 1)
        if transfers_per_instance < self.policy.max_active_transfers_per_instance * 0.3:  # 30% of max
            reasons.append(ScalingReason.ACTIVE_TRANSFERS)
        
        # Only scale down if multiple conditions are met
        return reasons if len(reasons) >= 2 else []
    
    def _create_scale_up_decision(self, metrics: ScalingMetrics, 
                                 reasons: List[ScalingReason]) -> ScalingDecision:
        """Create a scale up decision."""
        # Calculate target instances based on the most critical reason
        target_instances = self._calculate_scale_up_target(metrics, reasons)
        
        # Calculate confidence based on how many conditions are met
        confidence = min(0.9, 0.3 + (len(reasons) * 0.2))
        
        decision = ScalingDecision(
            timestamp=datetime.utcnow(),
            direction=ScalingDirection.UP,
            reason=reasons[0],  # Primary reason
            current_instances=metrics.current_instances,
            target_instances=target_instances,
            confidence=confidence,
            metrics=metrics,
            metadata={
                'all_reasons': [r.value for r in reasons],
                'evaluation_periods': len(self.metrics_history)
            }
        )
        
        self.scaling_history.append(decision)
        self.last_scale_up_time = decision.timestamp
        
        logger.info(f"Scale up decision: {metrics.current_instances} -> {target_instances} "
                   f"(reasons: {[r.value for r in reasons]})")
        
        return decision
    
    def _create_scale_down_decision(self, metrics: ScalingMetrics, 
                                   reasons: List[ScalingReason]) -> ScalingDecision:
        """Create a scale down decision."""
        # Conservative scale down - reduce by 1 instance at a time
        target_instances = max(
            self.policy.min_instances,
            metrics.current_instances - 1
        )
        
        # Lower confidence for scale down to be conservative
        confidence = min(0.7, 0.2 + (len(reasons) * 0.15))
        
        decision = ScalingDecision(
            timestamp=datetime.utcnow(),
            direction=ScalingDirection.DOWN,
            reason=reasons[0],  # Primary reason
            current_instances=metrics.current_instances,
            target_instances=target_instances,
            confidence=confidence,
            metrics=metrics,
            metadata={
                'all_reasons': [r.value for r in reasons],
                'evaluation_periods': len(self.metrics_history)
            }
        )
        
        self.scaling_history.append(decision)
        self.last_scale_down_time = decision.timestamp
        
        logger.info(f"Scale down decision: {metrics.current_instances} -> {target_instances} "
                   f"(reasons: {[r.value for r in reasons]})")
        
        return decision
    
    def _calculate_scale_up_target(self, metrics: ScalingMetrics, 
                                  reasons: List[ScalingReason]) -> int:
        """Calculate target instances for scale up."""
        current = metrics.current_instances
        
        # Start with current + 1
        target = current + 1
        
        # Adjust based on specific conditions
        if ScalingReason.QUEUE_LENGTH in reasons:
            # Scale more aggressively for queue backlog
            queue_factor = math.ceil(metrics.queue_length / self.policy.max_queue_length)
            target = min(current + queue_factor, current * 2)
        
        if ScalingReason.ACTIVE_TRANSFERS in reasons:
            # Scale based on transfer load
            needed_instances = math.ceil(
                metrics.active_transfers / self.policy.max_active_transfers_per_instance
            )
            target = max(target, needed_instances)
        
        if ScalingReason.CPU_HIGH in reasons and metrics.cpu_utilization > 90:
            # Aggressive scaling for very high CPU
            target = min(current + 2, current * 1.5)
        
        # Cap at max instances
        return min(int(target), self.policy.max_instances)
    
    def _no_scaling_decision(self, metrics: ScalingMetrics, reason: str) -> ScalingDecision:
        """Create a no-scaling decision."""
        return ScalingDecision(
            timestamp=datetime.utcnow(),
            direction=ScalingDirection.NONE,
            reason=ScalingReason.MANUAL,  # Generic reason
            current_instances=metrics.current_instances,
            target_instances=metrics.current_instances,
            confidence=1.0,
            metrics=metrics,
            metadata={'reason': reason}
        )
    
    def get_scaling_history(self, limit: int = 100) -> List[ScalingDecision]:
        """Get recent scaling decisions."""
        return self.scaling_history[-limit:]
    
    def get_metrics_history(self, limit: int = 100) -> List[ScalingMetrics]:
        """Get recent metrics."""
        return self.metrics_history[-limit:]


class AutoScaler:
    """Main auto-scaling coordinator."""
    
    def __init__(self, policy: ScalingPolicy, 
                 scaling_executor: Optional[Callable[[ScalingDecision], bool]] = None):
        self.policy = policy
        self.scaling_engine = ScalingEngine(policy)
        self.metrics_collector = MetricsCollector()
        self.scaling_executor = scaling_executor or self._default_scaling_executor
        
        # State
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.evaluation_interval = 60  # seconds
        
        logger.info("Auto-scaler initialized")
    
    async def start(self, evaluation_interval: int = 60):
        """Start the auto-scaling loop."""
        if self.running:
            logger.warning("Auto-scaler is already running")
            return
        
        self.running = True
        self.evaluation_interval = evaluation_interval
        self.task = asyncio.create_task(self._scaling_loop())
        
        logger.info(f"Auto-scaler started (evaluation interval: {evaluation_interval}s)")
    
    async def stop(self):
        """Stop the auto-scaling loop."""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Auto-scaler stopped")
    
    async def _scaling_loop(self):
        """Main auto-scaling evaluation loop."""
        while self.running:
            try:
                # Collect current metrics
                metrics = await self.metrics_collector.collect_current_metrics()
                
                # Make scaling decision
                decision = self.scaling_engine.make_scaling_decision(metrics)
                
                # Execute scaling if needed
                if decision.direction != ScalingDirection.NONE:
                    success = await self._execute_scaling(decision)
                    decision.metadata['execution_success'] = success
                    
                    if success:
                        logger.info(f"Scaling executed successfully: {decision.direction.value}")
                    else:
                        logger.error(f"Scaling execution failed: {decision.direction.value}")
                
                # Update queue length metric
                update_queue_length("normal", metrics.queue_length)
                
                # Wait for next evaluation
                await asyncio.sleep(self.evaluation_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Auto-scaling loop error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _execute_scaling(self, decision: ScalingDecision) -> bool:
        """Execute a scaling decision."""
        try:
            return self.scaling_executor(decision)
        except Exception as e:
            logger.error(f"Scaling execution error: {e}")
            return False
    
    def _default_scaling_executor(self, decision: ScalingDecision) -> bool:
        """Default scaling executor (placeholder)."""
        logger.info(f"Would execute scaling: {decision.current_instances} -> {decision.target_instances}")
        # In a real implementation, this would call cloud provider APIs
        # to actually scale the infrastructure
        return True
    
    def force_scaling_evaluation(self) -> ScalingDecision:
        """Force an immediate scaling evaluation."""
        logger.info("Forcing scaling evaluation")
        
        # This would be implemented as an async method in practice
        # For now, return a placeholder decision
        current_time = datetime.utcnow()
        metrics = ScalingMetrics(
            timestamp=current_time,
            cpu_utilization=50.0,
            memory_utilization=50.0,
            active_transfers=5,
            queue_length=0,
            throughput_mbps=100.0,
            error_rate=0.0,
            response_time_ms=100.0,
            current_instances=2
        )
        
        return self.scaling_engine.make_scaling_decision(metrics)
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current auto-scaler status."""
        return {
            'running': self.running,
            'evaluation_interval': self.evaluation_interval,
            'policy': {
                'min_instances': self.policy.min_instances,
                'max_instances': self.policy.max_instances,
                'cpu_thresholds': {
                    'scale_up': self.policy.cpu_scale_up_threshold,
                    'scale_down': self.policy.cpu_scale_down_threshold
                },
                'memory_thresholds': {
                    'scale_up': self.policy.memory_scale_up_threshold,
                    'scale_down': self.policy.memory_scale_down_threshold
                }
            },
            'recent_decisions': [
                d.to_dict() for d in self.scaling_engine.get_scaling_history(5)
            ],
            'metrics_history_count': len(self.scaling_engine.get_metrics_history())
        }


# Global auto-scaler instance
_autoscaler: Optional[AutoScaler] = None


def initialize_autoscaler(policy: Optional[ScalingPolicy] = None,
                         scaling_executor: Optional[Callable[[ScalingDecision], bool]] = None) -> AutoScaler:
    """Initialize the global auto-scaler."""
    global _autoscaler
    
    if not policy:
        # Create default policy based on environment
        import os
        env = os.getenv('ENVIRONMENT', 'dev')
        
        if env == 'prod':
            policy = ScalingPolicy(
                min_instances=3,
                max_instances=50,
                cpu_scale_up_threshold=70.0,
                cpu_scale_down_threshold=30.0,
                memory_scale_up_threshold=80.0,
                memory_scale_down_threshold=40.0,
                scale_up_cooldown_seconds=300,
                scale_down_cooldown_seconds=600
            )
        elif env == 'staging':
            policy = ScalingPolicy(
                min_instances=2,
                max_instances=20,
                cpu_scale_up_threshold=75.0,
                cpu_scale_down_threshold=35.0,
                memory_scale_up_threshold=85.0,
                memory_scale_down_threshold=45.0
            )
        else:  # dev
            policy = ScalingPolicy(
                min_instances=1,
                max_instances=5,
                cpu_scale_up_threshold=80.0,
                cpu_scale_down_threshold=40.0,
                memory_scale_up_threshold=90.0,
                memory_scale_down_threshold=50.0
            )
    
    _autoscaler = AutoScaler(policy, scaling_executor)
    logger.info("Auto-scaler initialized")
    return _autoscaler


def get_autoscaler() -> Optional[AutoScaler]:
    """Get the global auto-scaler instance."""
    return _autoscaler


async def start_autoscaler(evaluation_interval: int = 60):
    """Start the global auto-scaler."""
    if _autoscaler:
        await _autoscaler.start(evaluation_interval)


async def stop_autoscaler():
    """Stop the global auto-scaler."""
    if _autoscaler:
        await _autoscaler.stop()