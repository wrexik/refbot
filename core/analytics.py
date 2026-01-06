"""Analytics Engine - Real-time metrics aggregation, alerting, and anomaly detection"""

import logging
import csv
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from collections import deque
from enum import Enum
from dataclasses import dataclass, asdict
import statistics

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data class"""
    metric_name: str
    message: str
    severity: AlertSeverity
    current_value: float
    threshold: float
    timestamp: datetime
    resolved: bool = False


class MetricsAggregator:
    """Real-time metrics aggregation with alerting and anomaly detection"""
    
    def __init__(self, retention_hours: int = 24, max_metrics_per_name: int = 100000):
        """
        Initialize metrics aggregator
        
        Args:
            retention_hours: How long to keep metrics in memory
            max_metrics_per_name: Maximum metrics per metric name
        """
        self.retention_hours = retention_hours
        self.max_metrics_per_name = max_metrics_per_name
        self.metrics: Dict[str, deque] = {}
        self.thresholds: Dict[str, Dict] = {}
        self.alerts: List[Alert] = []
        self.alert_callbacks: List = []
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict] = None, unit: str = "") -> None:
        """
        Record a metric value
        
        Args:
            metric_name: Name of the metric
            value: Numeric value
            tags: Optional tags dictionary
            unit: Unit of measurement
        """
        if metric_name not in self.metrics:
            self.metrics[metric_name] = deque(maxlen=self.max_metrics_per_name)
        
        record = {
            "timestamp": datetime.now(),
            "value": value,
            "tags": tags or {},
            "unit": unit
        }
        
        self.metrics[metric_name].append(record)
        
        # Check thresholds
        self._check_thresholds(metric_name, value)
    
    def set_alert_threshold(self, metric_name: str, upper_threshold: Optional[float] = None,
                           lower_threshold: Optional[float] = None,
                           severity: AlertSeverity = AlertSeverity.WARNING) -> None:
        """
        Set alert threshold for a metric
        
        Args:
            metric_name: Name of the metric
            upper_threshold: Upper limit for alerts
            lower_threshold: Lower limit for alerts
            severity: Alert severity level
        """
        if metric_name not in self.thresholds:
            self.thresholds[metric_name] = {}
        
        self.thresholds[metric_name] = {
            "upper_threshold": upper_threshold,
            "lower_threshold": lower_threshold,
            "severity": severity
        }
    
    def _check_thresholds(self, metric_name: str, value: float) -> None:
        """
        Check if value exceeds thresholds
        
        Args:
            metric_name: Name of the metric
            value: Current value
        """
        if metric_name not in self.thresholds:
            return
        
        threshold_config = self.thresholds[metric_name]
        upper = threshold_config.get("upper_threshold")
        lower = threshold_config.get("lower_threshold")
        severity = threshold_config.get("severity", AlertSeverity.WARNING)
        
        alert_created = False
        
        if upper is not None and value > upper:
            message = f"{metric_name} exceeded upper threshold: {value} > {upper}"
            self._create_alert(metric_name, message, severity, value, upper)
            alert_created = True
        
        if lower is not None and value < lower:
            message = f"{metric_name} below lower threshold: {value} < {lower}"
            self._create_alert(metric_name, message, severity, value, lower)
            alert_created = True
    
    def _create_alert(self, metric_name: str, message: str, severity: AlertSeverity,
                     current_value: float, threshold: float) -> None:
        """
        Create an alert
        
        Args:
            metric_name: Name of the metric
            message: Alert message
            severity: Alert severity
            current_value: Current metric value
            threshold: Threshold value
        """
        alert = Alert(
            metric_name=metric_name,
            message=message,
            severity=severity,
            current_value=current_value,
            threshold=threshold,
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        
        # Call alert callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def register_alert_callback(self, callback) -> None:
        """Register alert callback"""
        self.alert_callbacks.append(callback)
    
    def get_metric_statistics(self, metric_name: str) -> Optional[Dict]:
        """
        Get statistics for a metric
        
        Args:
            metric_name: Name of the metric
            
        Returns:
            Statistics dictionary
        """
        if metric_name not in self.metrics:
            return None
        
        values = [m["value"] for m in self.metrics[metric_name]]
        
        if not values:
            return None
        
        return {
            "metric_name": metric_name,
            "count": len(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "stdev": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "latest": values[-1] if values else None,
            "timestamp": self.metrics[metric_name][-1]["timestamp"]
        }
    
    def detect_anomalies(self, metric_name: str, method: str = "zscore",
                        lookback_count: int = 50, threshold: float = 2.0) -> List[Dict]:
        """
        Detect anomalies in metrics
        
        Args:
            metric_name: Name of the metric
            method: Detection method ('zscore' or 'iqr')
            lookback_count: Number of recent values to analyze
            threshold: Threshold for anomaly detection
            
        Returns:
            List of detected anomalies
        """
        if metric_name not in self.metrics:
            return []
        
        records = list(self.metrics[metric_name])[-lookback_count:]
        values = [m["value"] for m in records]
        
        if len(values) < 3:
            return []
        
        anomalies = []
        
        if method == "zscore":
            mean = statistics.mean(values)
            stdev = statistics.stdev(values) if len(values) > 1 else 0
            
            if stdev == 0:
                return []
            
            for i, record in enumerate(records):
                z_score = abs((record["value"] - mean) / stdev)
                if z_score > threshold:
                    anomalies.append({
                        "value": record["value"],
                        "timestamp": record["timestamp"],
                        "z_score": z_score,
                        "expected_range": (mean - threshold * stdev, mean + threshold * stdev)
                    })
        
        elif method == "iqr":
            sorted_values = sorted(values)
            q1 = sorted_values[len(sorted_values) // 4]
            q3 = sorted_values[3 * len(sorted_values) // 4]
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            
            for record in records:
                if record["value"] < lower_bound or record["value"] > upper_bound:
                    anomalies.append({
                        "value": record["value"],
                        "timestamp": record["timestamp"],
                        "bounds": (lower_bound, upper_bound)
                    })
        
        return anomalies
    
    def get_trend_analysis(self, metric_name: str, window_size: int = 10) -> Optional[Dict]:
        """
        Analyze trend in metrics
        
        Args:
            metric_name: Name of the metric
            window_size: Window size for trend calculation
            
        Returns:
            Trend analysis dictionary
        """
        if metric_name not in self.metrics:
            return None
        
        records = list(self.metrics[metric_name])
        values = [m["value"] for m in records]
        
        if len(values) < window_size:
            return None
        
        recent = values[-window_size:]
        older = values[-(window_size * 2):-window_size]
        
        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)
        
        change = recent_avg - older_avg
        change_percent = (change / older_avg * 100) if older_avg != 0 else 0
        
        trend = "increasing" if change > 0 else "decreasing" if change < 0 else "stable"
        
        return {
            "metric_name": metric_name,
            "trend": trend,
            "change": change,
            "change_percent": change_percent,
            "current_value": values[-1],
            "average_value": recent_avg,
            "previous_average": older_avg
        }
    
    def get_active_alerts(self, resolved: bool = False) -> List[Dict]:
        """
        Get active alerts
        
        Args:
            resolved: Include resolved alerts
            
        Returns:
            List of active alerts
        """
        alerts = [a for a in self.alerts if not a.resolved or resolved]
        return [asdict(a) for a in alerts[-100:]]  # Last 100 alerts
    
    def get_success_rate(self, metric_name: str) -> float:
        """
        Calculate success rate from error rate metric
        
        Args:
            metric_name: Metric name (typically 'error_rate')
            
        Returns:
            Success rate as percentage
        """
        if metric_name not in self.metrics:
            return 0.0
        
        values = [m["value"] for m in self.metrics[metric_name]]
        if not values:
            return 0.0
        
        avg_error_rate = statistics.mean(values)
        return (1 - avg_error_rate) * 100
    
    def get_reliability_score(self, metric_name: str) -> float:
        """
        Get reliability score (0-100)
        
        Args:
            metric_name: Metric name
            
        Returns:
            Reliability score
        """
        return self.get_success_rate(metric_name)
    
    def export_to_csv(self, filepath: str) -> bool:
        """
        Export metrics to CSV file
        
        Args:
            filepath: Output file path
            
        Returns:
            True if successful
        """
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'metric_name', 'value', 'tags', 'unit'])
                
                for metric_name, records in self.metrics.items():
                    for record in records:
                        writer.writerow([
                            record['timestamp'].isoformat(),
                            metric_name,
                            record['value'],
                            json.dumps(record['tags']),
                            record['unit']
                        ])
            
            logger.info(f"Exported metrics to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False
    
    def export_to_json(self, filepath: str) -> bool:
        """
        Export metrics to JSON file
        
        Args:
            filepath: Output file path
            
        Returns:
            True if successful
        """
        try:
            data = {}
            for metric_name, records in self.metrics.items():
                data[metric_name] = [
                    {
                        'timestamp': m['timestamp'].isoformat(),
                        'value': m['value'],
                        'tags': m['tags'],
                        'unit': m['unit']
                    }
                    for m in records
                ]
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Exported metrics to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export to JSON: {e}")
            return False
