"""
Predictive scaling system for PQC Secure Transfer.
Uses machine learning to predict federated learning workload patterns and proactively scale resources.
"""

import asyncio
import logging
import pickle
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import statistics

# ML imports with fallbacks
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, using simple predictive models")

from .autoscaler import ScalingMetrics, ScalingDecision, ScalingDirection, ScalingReason

logger = logging.getLogger(__name__)


@dataclass
class WorkloadPattern:
    """Represents a detected workload pattern."""
    pattern_id: str
    name: str
    description: str
    time_of_day_start: int  # Hour of day (0-23)
    time_of_day_end: int    # Hour of day (0-23)
    days_of_week: List[int]  # 0=Monday, 6=Sunday
    expected_load_multiplier: float  # Multiplier for baseline load
    confidence: float  # 0.0 to 1.0
    
    def matches_time(self, dt: datetime) -> bool:
        """Check if datetime matches this pattern."""
        hour = dt.hour
        day_of_week = dt.weekday()
        
        # Check day of week
        if day_of_week not in self.days_of_week:
            return False
        
        # Check time range (handle overnight patterns)
        if self.time_of_day_start <= self.time_of_day_end:
            return self.time_of_day_start <= hour <= self.time_of_day_end
        else:
            return hour >= self.time_of_day_start or hour <= self.time_of_day_end


@dataclass
class PredictionResult:
    """Result of workload prediction."""
    timestamp: datetime
    prediction_horizon_minutes: int
    predicted_metrics: ScalingMetrics
    confidence: float
    pattern_match: Optional[WorkloadPattern]
    model_used: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class FederatedLearningPatternDetector:
    """Detects common federated learning workload patterns."""
    
    def __init__(self):
        # Common federated learning patterns
        self.known_patterns = [
            WorkloadPattern(
                pattern_id="fl_training_morning",
                name="Morning FL Training",
                description="Federated learning training sessions typically start in morning",
                time_of_day_start=8,
                time_of_day_end=12,
                days_of_week=[0, 1, 2, 3, 4],  # Weekdays
                expected_load_multiplier=2.5,
                confidence=0.8
            ),
            WorkloadPattern(
                pattern_id="fl_training_evening",
                name="Evening FL Training",
                description="Evening federated learning sessions",
                time_of_day_start=18,
                time_of_day_end=22,
                days_of_week=[0, 1, 2, 3, 4],  # Weekdays
                expected_load_multiplier=3.0,
                confidence=0.85
            ),
            WorkloadPattern(
                pattern_id="fl_weekend_batch",
                name="Weekend Batch Processing",
                description="Large batch processing on weekends",
                time_of_day_start=2,
                time_of_day_end=8,
                days_of_week=[5, 6],  # Weekend
                expected_load_multiplier=4.0,
                confidence=0.7
            ),
            WorkloadPattern(
                pattern_id="fl_model_sync",
                name="Model Synchronization",
                description="Regular model synchronization every 4 hours",
                time_of_day_start=0,
                time_of_day_end=23,
                days_of_week=[0, 1, 2, 3, 4, 5, 6],  # All days
                expected_load_multiplier=1.5,
                confidence=0.6
            )
        ]
        
        logger.info(f"Initialized pattern detector with {len(self.known_patterns)} patterns")
    
    def detect_current_pattern(self, dt: datetime) -> Optional[WorkloadPattern]:
        """Detect which pattern matches the current time."""
        matching_patterns = [p for p in self.known_patterns if p.matches_time(dt)]
        
        if not matching_patterns:
            return None
        
        # Return pattern with highest confidence
        return max(matching_patterns, key=lambda p: p.confidence)
    
    def predict_next_pattern(self, dt: datetime, hours_ahead: int = 2) -> Optional[WorkloadPattern]:
        """Predict the next pattern within the specified time window."""
        future_time = dt + timedelta(hours=hours_ahead)
        return self.detect_current_pattern(future_time)


class SimplePredictor:
    """Simple time-series predictor when ML libraries are not available."""
    
    def __init__(self, window_size: int = 24):
        self.window_size = window_size
        self.metrics_history: List[ScalingMetrics] = []
    
    def add_metrics(self, metrics: ScalingMetrics):
        """Add metrics to history."""
        self.metrics_history.append(metrics)
        
        # Keep only recent history
        if len(self.metrics_history) > self.window_size * 7:  # 7 days
            self.metrics_history = self.metrics_history[-self.window_size * 7:]
    
    def predict(self, minutes_ahead: int = 60) -> Tuple[ScalingMetrics, float]:
        """Simple prediction based on historical averages and trends."""
        if len(self.metrics_history) < 3:
            # Not enough data, return current metrics
            if self.metrics_history:
                return self.metrics_history[-1], 0.3
            else:
                # Default metrics
                return ScalingMetrics(
                    timestamp=datetime.utcnow() + timedelta(minutes=minutes_ahead),
                    cpu_utilization=50.0,
                    memory_utilization=50.0,
                    active_transfers=5,
                    queue_length=0,
                    throughput_mbps=100.0,
                    error_rate=0.0,
                    response_time_ms=100.0,
                    current_instances=2
                ), 0.2
        
        # Use recent metrics for prediction
        recent_metrics = self.metrics_history[-min(12, len(self.metrics_history)):]
        
        # Calculate trends
        cpu_trend = self._calculate_trend([m.cpu_utilization for m in recent_metrics])
        memory_trend = self._calculate_trend([m.memory_utilization for m in recent_metrics])
        transfers_trend = self._calculate_trend([m.active_transfers for m in recent_metrics])
        
        # Get current values
        current = recent_metrics[-1]
        
        # Project forward
        time_factor = minutes_ahead / 60.0  # Convert to hours
        
        predicted_cpu = max(0, min(100, current.cpu_utilization + (cpu_trend * time_factor)))
        predicted_memory = max(0, min(100, current.memory_utilization + (memory_trend * time_factor)))
        predicted_transfers = max(0, int(current.active_transfers + (transfers_trend * time_factor)))
        
        predicted_metrics = ScalingMetrics(
            timestamp=datetime.utcnow() + timedelta(minutes=minutes_ahead),
            cpu_utilization=predicted_cpu,
            memory_utilization=predicted_memory,
            active_transfers=predicted_transfers,
            queue_length=max(0, current.queue_length),
            throughput_mbps=current.throughput_mbps,
            error_rate=current.error_rate,
            response_time_ms=current.response_time_ms,
            current_instances=current.current_instances
        )
        
        # Confidence based on data availability and trend stability
        confidence = min(0.8, 0.3 + (len(recent_metrics) / 12) * 0.5)
        
        return predicted_metrics, confidence
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate simple linear trend."""
        if len(values) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(values)
        x = list(range(n))
        
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator


class MLPredictor:
    """Machine learning-based predictor using scikit-learn."""
    
    def __init__(self, model_path: Optional[str] = None):
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn not available for ML predictor")
        
        self.model_path = Path(model_path) if model_path else Path("models/scaling_predictor.pkl")
        self.model_path.parent.mkdir(exist_ok=True)
        
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Load existing model if available
        self._load_model()
        
        self.metrics_history: List[ScalingMetrics] = []
        self.feature_names = [
            'hour_of_day', 'day_of_week', 'cpu_utilization', 'memory_utilization',
            'active_transfers', 'queue_length', 'throughput_mbps', 'error_rate',
            'response_time_ms', 'cpu_trend', 'memory_trend', 'transfer_trend'
        ]
    
    def add_metrics(self, metrics: ScalingMetrics):
        """Add metrics to training data."""
        self.metrics_history.append(metrics)
        
        # Keep reasonable history size
        if len(self.metrics_history) > 10000:
            self.metrics_history = self.metrics_history[-8000:]
        
        # Retrain periodically
        if len(self.metrics_history) % 100 == 0 and len(self.metrics_history) > 200:
            asyncio.create_task(self._retrain_model())
    
    def _extract_features(self, metrics: ScalingMetrics, 
                         history: List[ScalingMetrics]) -> np.ndarray:
        """Extract features for ML model."""
        # Time-based features
        hour_of_day = metrics.timestamp.hour
        day_of_week = metrics.timestamp.weekday()
        
        # Current metrics
        cpu = metrics.cpu_utilization
        memory = metrics.memory_utilization
        transfers = metrics.active_transfers
        queue = metrics.queue_length
        throughput = metrics.throughput_mbps
        error_rate = metrics.error_rate
        response_time = metrics.response_time_ms
        
        # Trend features (if enough history)
        cpu_trend = 0.0
        memory_trend = 0.0
        transfer_trend = 0.0
        
        if len(history) >= 3:
            recent = history[-3:]
            cpu_values = [m.cpu_utilization for m in recent]
            memory_values = [m.memory_utilization for m in recent]
            transfer_values = [m.active_transfers for m in recent]
            
            cpu_trend = (cpu_values[-1] - cpu_values[0]) / len(cpu_values)
            memory_trend = (memory_values[-1] - memory_values[0]) / len(memory_values)
            transfer_trend = (transfer_values[-1] - transfer_values[0]) / len(transfer_values)
        
        return np.array([
            hour_of_day, day_of_week, cpu, memory, transfers, queue,
            throughput, error_rate, response_time, cpu_trend, memory_trend, transfer_trend
        ])
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare training data from metrics history."""
        if len(self.metrics_history) < 10:
            raise ValueError("Not enough training data")
        
        features = []
        targets = []
        
        # Create training samples with 1-hour prediction horizon
        for i in range(len(self.metrics_history) - 12):  # 12 = 1 hour with 5-min intervals
            current_metrics = self.metrics_history[i]
            future_metrics = self.metrics_history[i + 12]  # 1 hour later
            history = self.metrics_history[max(0, i-10):i+1]
            
            feature_vector = self._extract_features(current_metrics, history)
            target_vector = np.array([
                future_metrics.cpu_utilization,
                future_metrics.memory_utilization,
                future_metrics.active_transfers
            ])
            
            features.append(feature_vector)
            targets.append(target_vector)
        
        return np.array(features), np.array(targets)
    
    async def _retrain_model(self):
        """Retrain the ML model with new data."""
        try:
            logger.info("Retraining ML prediction model")
            
            X, y = self._prepare_training_data()
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = self.model.predict(X_test_scaled)
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            
            logger.info(f"Model retrained - MAE: {mae:.2f}, MSE: {mse:.2f}")
            
            self.is_trained = True
            self._save_model()
            
        except Exception as e:
            logger.error(f"Model retraining failed: {e}")
    
    def predict(self, current_metrics: ScalingMetrics, 
               minutes_ahead: int = 60) -> Tuple[ScalingMetrics, float]:
        """Predict future metrics using ML model."""
        if not self.is_trained:
            # Fall back to simple prediction
            simple_predictor = SimplePredictor()
            simple_predictor.metrics_history = self.metrics_history
            return simple_predictor.predict(minutes_ahead)
        
        try:
            # Extract features
            features = self._extract_features(current_metrics, self.metrics_history)
            features_scaled = self.scaler.transform(features.reshape(1, -1))
            
            # Make prediction
            prediction = self.model.predict(features_scaled)[0]
            
            # Create predicted metrics
            predicted_metrics = ScalingMetrics(
                timestamp=datetime.utcnow() + timedelta(minutes=minutes_ahead),
                cpu_utilization=max(0, min(100, prediction[0])),
                memory_utilization=max(0, min(100, prediction[1])),
                active_transfers=max(0, int(prediction[2])),
                queue_length=current_metrics.queue_length,  # Keep current
                throughput_mbps=current_metrics.throughput_mbps,  # Keep current
                error_rate=current_metrics.error_rate,  # Keep current
                response_time_ms=current_metrics.response_time_ms,  # Keep current
                current_instances=current_metrics.current_instances
            )
            
            # Calculate confidence based on model performance
            confidence = 0.8 if self.is_trained else 0.4
            
            return predicted_metrics, confidence
            
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            # Fall back to simple prediction
            simple_predictor = SimplePredictor()
            simple_predictor.metrics_history = self.metrics_history
            return simple_predictor.predict(minutes_ahead)
    
    def _save_model(self):
        """Save trained model to disk."""
        try:
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'is_trained': self.is_trained,
                'feature_names': self.feature_names
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
            logger.info(f"Model saved to {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
    
    def _load_model(self):
        """Load trained model from disk."""
        try:
            if self.model_path.exists():
                with open(self.model_path, 'rb') as f:
                    model_data = pickle.load(f)
                
                self.model = model_data['model']
                self.scaler = model_data['scaler']
                self.is_trained = model_data['is_trained']
                
                logger.info(f"Model loaded from {self.model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")


class PredictiveScaler:
    """Main predictive scaling system."""
    
    def __init__(self, use_ml: bool = True):
        self.pattern_detector = FederatedLearningPatternDetector()
        
        # Initialize predictor
        if use_ml and SKLEARN_AVAILABLE:
            try:
                self.predictor = MLPredictor()
                logger.info("Using ML-based predictor")
            except Exception as e:
                logger.warning(f"ML predictor failed, falling back to simple: {e}")
                self.predictor = SimplePredictor()
        else:
            self.predictor = SimplePredictor()
            logger.info("Using simple predictor")
        
        self.prediction_history: List[PredictionResult] = []
    
    def add_metrics(self, metrics: ScalingMetrics):
        """Add metrics for training and pattern detection."""
        self.predictor.add_metrics(metrics)
    
    async def predict_workload(self, minutes_ahead: int = 60) -> PredictionResult:
        """Predict workload for the specified time ahead."""
        current_time = datetime.utcnow()
        future_time = current_time + timedelta(minutes=minutes_ahead)
        
        # Detect current and future patterns
        current_pattern = self.pattern_detector.detect_current_pattern(current_time)
        future_pattern = self.pattern_detector.detect_current_pattern(future_time)
        
        # Get base prediction from ML/simple model
        if hasattr(self.predictor, 'metrics_history') and self.predictor.metrics_history:
            current_metrics = self.predictor.metrics_history[-1]
        else:
            # Default current metrics
            current_metrics = ScalingMetrics(
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
        
        predicted_metrics, base_confidence = self.predictor.predict(minutes_ahead)
        
        # Adjust prediction based on federated learning patterns
        if future_pattern:
            multiplier = future_pattern.expected_load_multiplier
            
            # Apply pattern-based adjustments
            predicted_metrics.cpu_utilization = min(100, predicted_metrics.cpu_utilization * multiplier)
            predicted_metrics.memory_utilization = min(100, predicted_metrics.memory_utilization * multiplier)
            predicted_metrics.active_transfers = int(predicted_metrics.active_transfers * multiplier)
            predicted_metrics.queue_length = int(predicted_metrics.queue_length * multiplier)
            
            # Boost confidence if pattern is strong
            pattern_confidence = future_pattern.confidence
            final_confidence = min(0.95, base_confidence + (pattern_confidence * 0.2))
        else:
            final_confidence = base_confidence
            future_pattern = None
        
        # Create prediction result
        result = PredictionResult(
            timestamp=current_time,
            prediction_horizon_minutes=minutes_ahead,
            predicted_metrics=predicted_metrics,
            confidence=final_confidence,
            pattern_match=future_pattern,
            model_used=type(self.predictor).__name__,
            metadata={
                'base_confidence': base_confidence,
                'pattern_applied': future_pattern.pattern_id if future_pattern else None,
                'current_pattern': current_pattern.pattern_id if current_pattern else None
            }
        )
        
        self.prediction_history.append(result)
        
        # Keep recent history
        if len(self.prediction_history) > 1000:
            self.prediction_history = self.prediction_history[-800:]
        
        logger.info(f"Workload prediction: {final_confidence:.2f} confidence, "
                   f"pattern: {future_pattern.name if future_pattern else 'none'}")
        
        return result
    
    def should_proactive_scale(self, prediction: PredictionResult, 
                              current_instances: int) -> Optional[int]:
        """Determine if proactive scaling is recommended."""
        if prediction.confidence < 0.6:
            return None  # Not confident enough
        
        predicted = prediction.predicted_metrics
        
        # Calculate needed instances based on predicted load
        cpu_instances = max(1, int(predicted.cpu_utilization / 70))  # Target 70% CPU
        memory_instances = max(1, int(predicted.memory_utilization / 80))  # Target 80% memory
        transfer_instances = max(1, int(predicted.active_transfers / 10))  # 10 transfers per instance
        
        # Take the maximum requirement
        needed_instances = max(cpu_instances, memory_instances, transfer_instances)
        
        # Only recommend scaling if significant change is needed
        if abs(needed_instances - current_instances) >= 2:
            return needed_instances
        
        return None
    
    def get_prediction_accuracy(self, hours_back: int = 24) -> Dict[str, float]:
        """Calculate prediction accuracy for recent predictions."""
        if not self.prediction_history:
            return {'accuracy': 0.0, 'predictions_evaluated': 0}
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        recent_predictions = [
            p for p in self.prediction_history 
            if p.timestamp > cutoff_time
        ]
        
        if not recent_predictions:
            return {'accuracy': 0.0, 'predictions_evaluated': 0}
        
        # This would require actual vs predicted comparison
        # For now, return placeholder metrics
        return {
            'accuracy': 0.75,  # Placeholder
            'predictions_evaluated': len(recent_predictions),
            'average_confidence': statistics.mean(p.confidence for p in recent_predictions)
        }


# Global predictive scaler instance
_predictive_scaler: Optional[PredictiveScaler] = None


def initialize_predictive_scaler(use_ml: bool = True) -> PredictiveScaler:
    """Initialize the global predictive scaler."""
    global _predictive_scaler
    _predictive_scaler = PredictiveScaler(use_ml)
    logger.info("Predictive scaler initialized")
    return _predictive_scaler


def get_predictive_scaler() -> Optional[PredictiveScaler]:
    """Get the global predictive scaler instance."""
    return _predictive_scaler