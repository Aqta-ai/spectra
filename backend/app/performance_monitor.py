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
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class DegradationDetector:
    """Detects performance degradation using statistical analysis"""
    
    def __init__(self, window_size: int = 20, threshold: float = 1.5):
        self.window_size = window_size
        self.threshold = threshold  # Standard deviations above mean
        self.samples = deque(maxlen=window_size)
        self.baseline_mean = None
        self.baseline_std = None
    
    def add_sample(self, duration: float):
        """Add a new response time sample"""
        self.samples.append(duration)
        
        # Update baseline after collecting enough samples
        if len(self.samples) == self.window_size and self.baseline_mean is None:
            self._update_baseline()
    
    def _update_baseline(self):
        """Update baseline performance metrics"""
        if len(self.samples) < 10:
            return
        
        samples_list = list(self.samples)
        self.baseline_mean = sum(samples_list) / len(samples_list)
        
        # Calculate standard deviation
        variance = sum((x - self.baseline_mean) ** 2 for x in samples_list) / len(samples_list)
        self.baseline_std = variance ** 0.5
    
    def is_degrading(self) -> bool:
        """Check if performance is degrading"""
        if self.baseline_mean is None or len(self.samples) < self.window_size:
            return False
        
        # Check recent samples against baseline
        recent_samples = list(self.samples)[-5:]  # Last 5 samples
        recent_mean = sum(recent_samples) / len(recent_samples)
        
        # Degradation if recent mean is significantly higher than baseline
        threshold_value = self.baseline_mean + (self.threshold * self.baseline_std)
        return recent_mean > threshold_value
    
    def get_status(self) -> Dict[str, Any]:
        """Get current degradation detector status"""
        return {
            'samples_collected': len(self.samples),
            'baseline_established': self.baseline_mean is not None,
            'baseline_mean': self.baseline_mean,
            'baseline_std': self.baseline_std,
            'is_degrading': self.is_degrading() if self.baseline_mean else False
        }


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
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate from vision calls"""
        if self.total_vision_calls == 0:
            return 0.0
        return (self.total_vision_calls - self.failed_vision_calls) / self.total_vision_calls
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total_cache_requests = self.cache_hits + self.cache_misses
        if total_cache_requests == 0:
            return 0.0
        return self.cache_hits / total_cache_requests
    
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
        Initialize the enhanced performance monitor.
        
        Args:
            slow_response_threshold: Threshold in seconds for slow response alerts (default: 3.0)
        """
        self.metrics = PerformanceMetrics()
        self.slow_response_threshold = slow_response_threshold
        self.start_time = time.time()
        
        # Enhanced monitoring features
        self.ultra_fast_threshold = 0.2  # Sub-200ms responses
        self.performance_trends = deque(maxlen=50)  # Track performance over time
        self.optimization_suggestions = []
        self.smart_alerts = deque(maxlen=20)
        
        # Pattern detection
        self.response_patterns = {}
        self.degradation_detector = DegradationDetector()
        self.error_patterns = {}  # Initialize error patterns
        
        logger.info(f"Enhanced PerformanceMonitor initialized with thresholds: "
                   f"slow={slow_response_threshold}s, ultra_fast={self.ultra_fast_threshold}s")
    
    async def monitor_vision_call(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """
        Enhanced vision API call monitoring with smart insights.
        
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
            
            # Enhanced performance tracking
            self._track_performance_trend(duration)
            
            # Ultra-fast response detection
            if duration < self.ultra_fast_threshold:
                logger.info(f"⚡ Ultra-fast vision response: {duration*1000:.1f}ms")
            
            # Slow response detection with context
            elif duration > self.slow_response_threshold:
                self.metrics.slow_response_count += 1
                self._generate_slow_response_alert(duration)
            
            # Pattern detection
            self._detect_response_patterns(duration)
            
            # Check for performance degradation
            self.degradation_detector.add_sample(duration)
            if self.degradation_detector.is_degrading():
                self._generate_degradation_alert()
            
            logger.debug(f"Vision call completed in {duration:.3f}s")
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.metrics.failed_vision_calls += 1
            
            # Enhanced error tracking
            self._track_error_pattern(type(e).__name__, duration)
            
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
    
    def _track_performance_trend(self, duration: float):
        """Track performance trends over time"""
        current_time = time.time()
        self.performance_trends.append({
            'timestamp': current_time,
            'duration': duration,
            'is_ultra_fast': duration < self.ultra_fast_threshold,
            'is_slow': duration > self.slow_response_threshold
        })
    
    def get_error_rate(self) -> float:
        """Get current error rate"""
        if self.metrics.total_vision_calls == 0:
            return 0.0
        return self.metrics.failed_vision_calls / self.metrics.total_vision_calls
    
    def get_average_response_time(self) -> float:
        """Get average response time from recent samples"""
        if not self.metrics.vision_response_times:
            return 0.0
        return sum(self.metrics.vision_response_times) / len(self.metrics.vision_response_times)
    
    def _generate_slow_response_alert(self, duration: float):
        """Generate contextual slow response alert"""
        recent_avg = self.get_average_response_time()
        
        alert = {
            'type': 'slow_response',
            'duration': duration,
            'threshold': self.slow_response_threshold,
            'recent_average': recent_avg,
            'severity': 'critical' if duration > self.slow_response_threshold * 2 else 'warning',
            'timestamp': time.time(),
            'suggestion': self._get_slow_response_suggestion(duration, recent_avg)
        }
        
        self.smart_alerts.append(alert)
        
        logger.warning(
            f"Slow vision response: {duration:.2f}s (avg: {recent_avg:.2f}s) - {alert['suggestion']}"
        )
    
    def _get_slow_response_suggestion(self, duration: float, avg_duration: float) -> str:
        """Generate optimization suggestions for slow responses"""
        if duration > avg_duration * 3:
            return "Consider checking network connectivity or API rate limits"
        elif duration > avg_duration * 2:
            return "Frame caching might help reduce repeated analysis"
        else:
            return "Monitor for consistent slowdowns indicating system load"
    
    def _detect_response_patterns(self, duration: float):
        """Detect patterns in response times"""
        current_hour = datetime.now().hour
        
        if current_hour not in self.response_patterns:
            self.response_patterns[current_hour] = []
        
        self.response_patterns[current_hour].append(duration)
        
        # Keep only recent data (last 50 samples per hour)
        if len(self.response_patterns[current_hour]) > 50:
            self.response_patterns[current_hour].pop(0)
    
    def _track_error_pattern(self, error_type: str, duration: float):
        """Track error patterns for insights"""
        error_key = f"error_{error_type}"
        
        if error_key not in self.error_patterns:
            self.error_patterns[error_key] = []
        
        self.error_patterns[error_key].append({
            'timestamp': time.time(),
            'duration': duration
        })
    
    def _generate_degradation_alert(self):
        """Generate performance degradation alert"""
        alert = {
            'type': 'performance_degradation',
            'timestamp': time.time(),
            'severity': 'warning',
            'message': 'Performance degradation detected in recent responses',
            'suggestion': 'Consider system resource check or cache optimization'
        }
        
        self.smart_alerts.append(alert)
        logger.warning("Performance degradation detected - response times increasing")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get basic performance statistics"""
        if not self.metrics.vision_response_times:
            return {
                'total_calls': 0,
                'average_response_time': 0.0,
                'min_response_time': 0.0,
                'max_response_time': 0.0,
                'success_rate': 0.0,
                'cache_hit_rate': 0.0
            }
        
        response_times = self.metrics.vision_response_times
        return {
            'total_calls': len(response_times),
            'average_response_time': sum(response_times) / len(response_times),
            'min_response_time': min(response_times),
            'max_response_time': max(response_times),
            'success_rate': self.metrics.success_rate,
            'cache_hit_rate': self.metrics.cache_hit_rate
        }
    
    def get_enhanced_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics with insights"""
        base_stats = self.get_statistics()
        
        # Add enhanced metrics
        ultra_fast_count = sum(1 for t in self.performance_trends if t['is_ultra_fast'])
        total_trends = len(self.performance_trends)
        
        enhanced_stats = {
            **base_stats,
            'ultra_fast_responses': ultra_fast_count,
            'ultra_fast_percentage': (ultra_fast_count / max(total_trends, 1)) * 100,
            'performance_trend': self._calculate_performance_trend(),
            'hourly_patterns': self._get_hourly_performance_patterns(),
            'optimization_suggestions': self._generate_optimization_suggestions(),
            'recent_alerts': list(self.smart_alerts)[-5:],  # Last 5 alerts
            'degradation_status': self.degradation_detector.get_status()
        }
        
        return enhanced_stats
    
    def _calculate_performance_trend(self) -> str:
        """Calculate overall performance trend"""
        if len(self.performance_trends) < 5:  # Reduced from 10 to 5 for more responsive trend detection
            return "insufficient_data"
        
        recent_half = list(self.performance_trends)[-len(self.performance_trends)//2:]
        older_half = list(self.performance_trends)[:len(self.performance_trends)//2]
        
        recent_avg = sum(t['duration'] for t in recent_half) / len(recent_half)
        older_avg = sum(t['duration'] for t in older_half) / len(older_half)
        
        if recent_avg < older_avg * 0.9:
            return "improving"
        elif recent_avg > older_avg * 1.1:
            return "degrading"
        else:
            return "stable"
    
    def _get_hourly_performance_patterns(self) -> Dict[int, float]:
        """Get average performance by hour of day"""
        hourly_averages = {}
        
        for hour, durations in self.response_patterns.items():
            if durations:
                hourly_averages[hour] = sum(durations) / len(durations)
        
        return hourly_averages
    
    def _generate_optimization_suggestions(self) -> List[str]:
        """Generate smart optimization suggestions"""
        suggestions = []
        
        # Cache hit rate suggestions
        cache_hit_rate = self.get_cache_hit_rate()
        if cache_hit_rate < 60:
            suggestions.append(f"Low cache hit rate ({cache_hit_rate:.1f}%) - consider increasing cache size or TTL")
        
        # Response time suggestions
        avg_response = self.get_average_response_time()
        if avg_response > 1.0:
            suggestions.append(f"High average response time ({avg_response:.2f}s) - consider frame diff optimization")
        
        # Ultra-fast response suggestions
        ultra_fast_count = sum(1 for t in self.performance_trends if t['is_ultra_fast'])
        if ultra_fast_count > 0:
            suggestions.append(f"Achieving {ultra_fast_count} ultra-fast responses - great optimization!")
        
        # Error rate suggestions
        error_rate = self.get_error_rate()
        if error_rate > 5:
            suggestions.append(f"High error rate ({error_rate:.1f}%) - check API connectivity and rate limits")
        
        return suggestions
    
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
