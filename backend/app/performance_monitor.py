"""
Performance monitoring for Spectra vision system and actions.

This module provides comprehensive performance tracking for:
- Vision API response times
- Action success rates
- Cache hit rates
- Performance degradation alerts
"""

import time
import logging
from collections import deque
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    vision_response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    action_success_rates: deque = field(default_factory=lambda: deque(maxlen=100))
    cache_hits: int = 0
    cache_misses: int = 0
    total_vision_calls: int = 0
    failed_vision_calls: int = 0
    slow_response_count: int = 0  # Responses > 3 seconds
    
    def reset(self):
        """Reset all metrics."""
        self.vision_response_times.clear()
        self.action_success_rates.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_vision_calls = 0
        self.failed_vision_calls = 0
        self.slow_response_count = 0


class PerformanceMonitor:
    """
    Monitor and track performance metrics for Spectra's vision system and actions.
    
    Features:
    - Vision API response time tracking
    - Action success rate monitoring
    - Cache hit rate calculation
    - Automatic alerts for performance degradation
    - Performance statistics reporting
    """
    
    def __init__(self, slow_response_threshold: float = 3.0):
        """
        Initialize the performance monitor.
        
        Args:
            slow_response_threshold: Threshold in seconds for slow response alerts (default: 3.0)
        """
        self.metrics = PerformanceMetrics()
        self.slow_response_threshold = slow_response_threshold
        self.start_time = time.time()
        
        logger.info(f"PerformanceMonitor initialized with slow_response_threshold={slow_response_threshold}s")
    
    async def monitor_vision_call(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Monitor a vision API call and track its performance.
        
        Args:
            func: The async function to monitor
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            The result from the monitored function
            
        Raises:
            Exception: Re-raises any exception from the monitored function
        """
        start_time = time.time()
        self.metrics.total_vision_calls += 1
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record successful response time
            self.metrics.vision_response_times.append(duration)
            
            # Alert if response is slow
            if duration > self.slow_response_threshold:
                self.metrics.slow_response_count += 1
                logger.warning(
                    f"Slow vision response detected: {duration:.2f}s "
                    f"(threshold: {self.slow_response_threshold}s)"
                )
            
            logger.debug(f"Vision call completed in {duration:.2f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.failed_vision_calls += 1
            
            logger.error(
                f"Vision call failed after {duration:.2f}s: {type(e).__name__}: {str(e)}"
            )
            raise
    
    def record_action_result(self, success: bool):
        """
        Record the result of an action execution.
        
        Args:
            success: Whether the action succeeded
        """
        self.metrics.action_success_rates.append(1 if success else 0)
        logger.debug(f"Action result recorded: {'success' if success else 'failure'}")
    
    def record_cache_hit(self):
        """Record a cache hit."""
        self.metrics.cache_hits += 1
        logger.debug("Cache hit recorded")
    
    def record_cache_miss(self):
        """Record a cache miss."""
        self.metrics.cache_misses += 1
        logger.debug("Cache miss recorded")
    
    def get_cache_hit_rate(self) -> float:
        """
        Calculate the cache hit rate.
        
        Returns:
            Cache hit rate as a percentage (0-100), or 0 if no cache operations
        """
        total_cache_ops = self.metrics.cache_hits + self.metrics.cache_misses
        if total_cache_ops == 0:
            return 0.0
        return (self.metrics.cache_hits / total_cache_ops) * 100
    
    def get_action_success_rate(self) -> float:
        """
        Calculate the action success rate.
        
        Returns:
            Action success rate as a percentage (0-100), or 0 if no actions
        """
        if not self.metrics.action_success_rates:
            return 0.0
        return (sum(self.metrics.action_success_rates) / len(self.metrics.action_success_rates)) * 100
    
    def get_vision_success_rate(self) -> float:
        """
        Calculate the vision API success rate.
        
        Returns:
            Vision success rate as a percentage (0-100), or 0 if no calls
        """
        if self.metrics.total_vision_calls == 0:
            return 0.0
        successful_calls = self.metrics.total_vision_calls - self.metrics.failed_vision_calls
        return (successful_calls / self.metrics.total_vision_calls) * 100
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive performance statistics.
        
        Returns:
            Dictionary containing all performance metrics
        """
        vision_times = list(self.metrics.vision_response_times)
        
        # Calculate vision response time statistics
        if vision_times:
            avg_vision_response = sum(vision_times) / len(vision_times)
            sorted_times = sorted(vision_times)
            p95_index = int(len(sorted_times) * 0.95)
            vision_p95 = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
            min_response = min(vision_times)
            max_response = max(vision_times)
        else:
            avg_vision_response = 0.0
            vision_p95 = 0.0
            min_response = 0.0
            max_response = 0.0
        
        # Calculate uptime
        uptime_seconds = time.time() - self.start_time
        
        stats = {
            "vision_metrics": {
                "avg_response_time": round(avg_vision_response, 3),
                "p95_response_time": round(vision_p95, 3),
                "min_response_time": round(min_response, 3),
                "max_response_time": round(max_response, 3),
                "total_calls": self.metrics.total_vision_calls,
                "failed_calls": self.metrics.failed_vision_calls,
                "success_rate": round(self.get_vision_success_rate(), 2),
                "slow_responses": self.metrics.slow_response_count,
                "slow_response_threshold": self.slow_response_threshold
            },
            "action_metrics": {
                "total_actions": len(self.metrics.action_success_rates),
                "success_rate": round(self.get_action_success_rate(), 2)
            },
            "cache_metrics": {
                "hits": self.metrics.cache_hits,
                "misses": self.metrics.cache_misses,
                "hit_rate": round(self.get_cache_hit_rate(), 2),
                "total_operations": self.metrics.cache_hits + self.metrics.cache_misses
            },
            "system_metrics": {
                "uptime_seconds": round(uptime_seconds, 1),
                "uptime_hours": round(uptime_seconds / 3600, 2)
            },
            "alerts": self._generate_alerts()
        }
        
        return stats
    
    def _generate_alerts(self) -> list[Dict[str, str]]:
        """
        Generate performance alerts based on current metrics.
        
        Returns:
            List of alert dictionaries with severity and message
        """
        alerts = []
        
        # Check vision response time
        vision_times = list(self.metrics.vision_response_times)
        if vision_times:
            avg_response = sum(vision_times) / len(vision_times)
            if avg_response > 2.0:
                alerts.append({
                    "severity": "warning",
                    "metric": "vision_response_time",
                    "message": f"Average vision response time ({avg_response:.2f}s) exceeds 2 second target"
                })
        
        # Check vision success rate
        vision_success_rate = self.get_vision_success_rate()
        if self.metrics.total_vision_calls > 10 and vision_success_rate < 95.0:
            alerts.append({
                "severity": "critical",
                "metric": "vision_success_rate",
                "message": f"Vision success rate ({vision_success_rate:.1f}%) below 95% threshold"
            })
        
        # Check cache hit rate
        cache_hit_rate = self.get_cache_hit_rate()
        total_cache_ops = self.metrics.cache_hits + self.metrics.cache_misses
        if total_cache_ops > 20 and cache_hit_rate < 70.0:
            alerts.append({
                "severity": "warning",
                "metric": "cache_hit_rate",
                "message": f"Cache hit rate ({cache_hit_rate:.1f}%) below 70% target"
            })
        
        # Check slow response count
        if self.metrics.slow_response_count > 5:
            alerts.append({
                "severity": "warning",
                "metric": "slow_responses",
                "message": f"{self.metrics.slow_response_count} slow responses (>{self.slow_response_threshold}s) detected"
            })
        
        return alerts
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        logger.info("Resetting performance metrics")
        self.metrics.reset()
        self.start_time = time.time()
    
    def log_performance_summary(self):
        """Log a summary of current performance metrics."""
        stats = self.get_performance_stats()
        
        logger.info("=== Performance Summary ===")
        logger.info(f"Vision: {stats['vision_metrics']['avg_response_time']}s avg, "
                   f"{stats['vision_metrics']['success_rate']}% success rate")
        logger.info(f"Actions: {stats['action_metrics']['success_rate']}% success rate")
        logger.info(f"Cache: {stats['cache_metrics']['hit_rate']}% hit rate")
        logger.info(f"Uptime: {stats['system_metrics']['uptime_hours']} hours")
        
        if stats['alerts']:
            logger.warning(f"Active alerts: {len(stats['alerts'])}")
            for alert in stats['alerts']:
                logger.warning(f"  [{alert['severity'].upper()}] {alert['message']}")


# Global performance monitor instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    Get the global performance monitor instance.
    
    Returns:
        The global PerformanceMonitor instance
    """
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def reset_performance_monitor():
    """Reset the global performance monitor instance."""
    global _performance_monitor
    _performance_monitor = None
