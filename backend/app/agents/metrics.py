"""Metrics collection and structured logging for Spectra orchestrator."""

import time
import logging
import json
from typing import Optional, Dict, Any
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading


# Structured logger
class StructuredLogger:
    """Logger that outputs structured JSON logs."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.correlation_id: Optional[str] = None
    
    def _log(self, level: int, message: str, **kwargs):
        """Log with structured data."""
        log_data = {
            "timestamp": time.time(),
            "message": message,
            "level": logging.getLevelName(level),
        }
        
        if self.correlation_id:
            log_data["correlation_id"] = self.correlation_id
        
        log_data.update(kwargs)
        
        self.logger.log(level, json.dumps(log_data))
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracing."""
        self.correlation_id = correlation_id
    
    def clear_correlation_id(self):
        """Clear correlation ID."""
        self.correlation_id = None


# Metrics collector
@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str]
    metric_type: str  # counter, gauge, histogram, timer


class MetricsCollector:
    """Collect and aggregate metrics."""
    
    def __init__(self):
        self._metrics: Dict[str, list] = defaultdict(list)
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()
    
    def counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        with self._lock:
            key = self._make_key(name, tags)
            self._counters[key] += value
            
            metric = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                tags=tags or {},
                metric_type="counter"
            )
            self._metrics[name].append(metric)
    
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric."""
        with self._lock:
            key = self._make_key(name, tags)
            self._gauges[key] = value
            
            metric = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                tags=tags or {},
                metric_type="gauge"
            )
            self._metrics[name].append(metric)
    
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Record a histogram value."""
        with self._lock:
            key = self._make_key(name, tags)
            self._histograms[key].append(value)
            
            metric = MetricPoint(
                name=name,
                value=value,
                timestamp=time.time(),
                tags=tags or {},
                metric_type="histogram"
            )
            self._metrics[name].append(metric)
    
    def timer(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timer metric (in seconds)."""
        self.histogram(name, duration, tags)
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> float:
        """Get current counter value."""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0.0)
    
    def get_gauge(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current gauge value."""
        key = self._make_key(name, tags)
        return self._gauges.get(key)
    
    def get_histogram_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        key = self._make_key(name, tags)
        values = self._histograms.get(key, [])
        
        if not values:
            return {}
        
        sorted_values = sorted(values)
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / len(values),
            "median": sorted_values[len(values) // 2],
            "p95": sorted_values[int(len(values) * 0.95)],
            "p99": sorted_values[int(len(values) * 0.99)],
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: self.get_histogram_stats(name)
                    for name in self._histograms.keys()
                },
            }
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self._metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
    
    @staticmethod
    def _make_key(name: str, tags: Optional[Dict[str, str]]) -> str:
        """Create a unique key for a metric."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


# Global instances
structured_logger = StructuredLogger("spectra.orchestrator")
metrics = MetricsCollector()


# Decorators
def track_performance(metric_name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to track function performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                
                metrics.timer(f"{metric_name}.duration", duration, tags)
                metrics.counter(f"{metric_name}.success", 1.0, tags)
                
                structured_logger.debug(
                    f"{func.__name__} completed",
                    duration_ms=duration * 1000,
                    function=func.__name__,
                    **tags or {}
                )
                
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                
                metrics.counter(f"{metric_name}.error", 1.0, tags)
                metrics.timer(f"{metric_name}.duration", duration, tags)
                
                structured_logger.error(
                    f"{func.__name__} failed",
                    duration_ms=duration * 1000,
                    function=func.__name__,
                    error=str(e),
                    error_type=type(e).__name__,
                    **tags or {}
                )
                
                raise
        
        return wrapper
    return decorator


@contextmanager
def track_operation(operation_name: str, tags: Optional[Dict[str, str]] = None):
    """Context manager to track operation performance."""
    start = time.perf_counter()
    
    structured_logger.debug(
        f"{operation_name} started",
        operation=operation_name,
        **tags or {}
    )
    
    try:
        yield
        duration = time.perf_counter() - start
        
        metrics.timer(f"{operation_name}.duration", duration, tags)
        metrics.counter(f"{operation_name}.success", 1.0, tags)
        
        structured_logger.info(
            f"{operation_name} completed",
            operation=operation_name,
            duration_ms=duration * 1000,
            **tags or {}
        )
    except Exception as e:
        duration = time.perf_counter() - start
        
        metrics.counter(f"{operation_name}.error", 1.0, tags)
        metrics.timer(f"{operation_name}.duration", duration, tags)
        
        structured_logger.error(
            f"{operation_name} failed",
            operation=operation_name,
            duration_ms=duration * 1000,
            error=str(e),
            error_type=type(e).__name__,
            **tags or {}
        )
        
        raise


# Orchestrator-specific metrics
class OrchestratorMetrics:
    """Orchestrator-specific metrics tracking."""
    
    @staticmethod
    def track_narration_removal(input_length: int, output_length: int, duration: float):
        """Track narration removal metrics."""
        metrics.histogram("orchestrator.narration_removal.input_length", input_length)
        metrics.histogram("orchestrator.narration_removal.output_length", output_length)
        metrics.histogram("orchestrator.narration_removal.reduction_ratio", 
                         (input_length - output_length) / input_length if input_length > 0 else 0)
        metrics.timer("orchestrator.narration_removal.duration", duration)
        
        structured_logger.debug(
            "Narration removal completed",
            input_length=input_length,
            output_length=output_length,
            reduction_pct=((input_length - output_length) / input_length * 100) if input_length > 0 else 0,
            duration_ms=duration * 1000
        )
    
    @staticmethod
    def track_vision_error(error_type: str, should_retry: bool):
        """Track vision error classification."""
        metrics.counter("orchestrator.vision_error.total", 1.0, {"type": error_type})
        if should_retry:
            metrics.counter("orchestrator.vision_error.retryable", 1.0, {"type": error_type})
        
        structured_logger.warning(
            "Vision error classified",
            error_type=error_type,
            should_retry=should_retry
        )
    
    @staticmethod
    def track_validation_violation(violation_type: str):
        """Track system instruction violations."""
        metrics.counter("orchestrator.validation.violation", 1.0, {"type": violation_type})
        
        structured_logger.warning(
            "System instruction violation detected",
            violation_type=violation_type
        )
    
    @staticmethod
    def track_interaction_logged(quality: str, tool_count: int):
        """Track interaction logging."""
        metrics.counter("orchestrator.interaction.logged", 1.0, {"quality": quality})
        metrics.histogram("orchestrator.interaction.tool_count", tool_count)
        
        structured_logger.info(
            "Interaction logged",
            quality=quality,
            tool_count=tool_count
        )
    
    @staticmethod
    def track_state_update(app_type: str):
        """Track state machine updates."""
        metrics.counter("orchestrator.state.update", 1.0, {"app": app_type})
        metrics.gauge("orchestrator.state.current_app", 1.0, {"app": app_type})
        
        structured_logger.debug(
            "State updated",
            app_type=app_type
        )
    
    @staticmethod
    def track_log_rotation(old_size_mb: float):
        """Track log file rotation."""
        metrics.counter("orchestrator.log.rotation", 1.0)
        metrics.histogram("orchestrator.log.rotated_size_mb", old_size_mb)
        
        structured_logger.info(
            "Log file rotated",
            old_size_mb=old_size_mb
        )


# Export convenience functions
def get_metrics_summary() -> Dict[str, Any]:
    """Get a summary of all metrics."""
    return metrics.get_all_metrics()


def reset_metrics():
    """Reset all metrics."""
    metrics.reset()


def set_correlation_id(correlation_id: str):
    """Set correlation ID for request tracing."""
    structured_logger.set_correlation_id(correlation_id)


def clear_correlation_id():
    """Clear correlation ID."""
    structured_logger.clear_correlation_id()


# ━━━ CONVENIENCE TRACKING FUNCTIONS ━━━

def track_narration_removal(had_violations: bool):
    """Track narration removal effectiveness."""
    metrics.counter("narration_removal_total")
    if had_violations:
        metrics.counter("narration_removal_violations")


def track_vision_error(error_type: str):
    """Track vision error by type."""
    metrics.counter(f"vision_error_{error_type}")
    metrics.counter("vision_error_total")


def track_tool_call(tool_name: str):
    """Track tool usage."""
    metrics.counter(f"tool_{tool_name}")
    metrics.counter("tool_total")


def track_interaction(quality: str):
    """Track interaction quality."""
    metrics.counter(f"interaction_{quality}")
    metrics.counter("interaction_total")


def monitor_performance(operation: Optional[str] = None):
    """Decorator to monitor function performance.
    
    Args:
        operation: Operation name (defaults to function name)
    
    Example:
        @monitor_performance("narration_removal")
        def remove_narration(text: str) -> str:
            ...
    """
    def decorator(func):
        op_name = operation or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                
                metrics.timer(f"{op_name}.duration", duration)
                metrics.counter(f"{op_name}.success")
                
                # Log slow operations
                if duration > 0.1:  # > 100ms
                    structured_logger.warning(
                        f"Slow operation: {op_name}",
                        operation=op_name,
                        duration_ms=duration * 1000
                    )
                
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                
                metrics.counter(f"{op_name}.error")
                metrics.timer(f"{op_name}.duration", duration)
                
                structured_logger.error(
                    f"Operation failed: {op_name}",
                    operation=op_name,
                    duration_ms=duration * 1000,
                    error=str(e),
                    error_type=type(e).__name__
                )
                
                raise
        
        return wrapper
    return decorator


# ━━━ METRICS EXPORT ━━━

def export_metrics() -> Dict[str, Any]:
    """Export all metrics for monitoring systems."""
    return {
        "timestamp": time.time(),
        "metrics": get_metrics_summary()
    }


def export_metrics_prometheus() -> str:
    """Export metrics in Prometheus format."""
    lines = []
    all_metrics = get_metrics_summary()
    
    # Counters
    for name, value in all_metrics.get("counters", {}).items():
        safe_name = name.replace("-", "_").replace(".", "_").replace("[", "_").replace("]", "")
        lines.append(f"# HELP spectra_{safe_name} Counter metric")
        lines.append(f"# TYPE spectra_{safe_name} counter")
        lines.append(f"spectra_{safe_name} {value}")
    
    # Gauges
    for name, value in all_metrics.get("gauges", {}).items():
        safe_name = name.replace("-", "_").replace(".", "_").replace("[", "_").replace("]", "")
        lines.append(f"# HELP spectra_{safe_name} Gauge metric")
        lines.append(f"# TYPE spectra_{safe_name} gauge")
        lines.append(f"spectra_{safe_name} {value}")
    
    return "\n".join(lines)


def get_metrics_collector():
    """Get global metrics collector."""
    return metrics


def get_business_metrics():
    """Get business metrics (alias for metrics)."""
    return metrics
