"""
Unit tests for PerformanceMonitor class.

Tests cover:
- Metrics collection for vision response times
- Action success rate tracking
- Cache hit rate calculation
- Performance statistics reporting
- Alert generation for performance degradation
"""

import pytest
import asyncio
import time
from app.performance_monitor import (
    PerformanceMonitor,
    PerformanceMetrics,
    get_performance_monitor,
    reset_performance_monitor
)


class TestPerformanceMetrics:
    """Test the PerformanceMetrics dataclass."""
    
    def test_metrics_initialization(self):
        """Test that metrics are properly initialized."""
        metrics = PerformanceMetrics()
        
        assert len(metrics.vision_response_times) == 0
        assert len(metrics.action_success_rates) == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.total_vision_calls == 0
        assert metrics.failed_vision_calls == 0
        assert metrics.slow_response_count == 0
    
    def test_metrics_reset(self):
        """Test that reset clears all metrics."""
        metrics = PerformanceMetrics()
        
        # Add some data
        metrics.vision_response_times.append(1.5)
        metrics.action_success_rates.append(1)
        metrics.cache_hits = 10
        metrics.cache_misses = 5
        metrics.total_vision_calls = 15
        metrics.failed_vision_calls = 2
        metrics.slow_response_count = 3
        
        # Reset
        metrics.reset()
        
        # Verify all cleared
        assert len(metrics.vision_response_times) == 0
        assert len(metrics.action_success_rates) == 0
        assert metrics.cache_hits == 0
        assert metrics.cache_misses == 0
        assert metrics.total_vision_calls == 0
        assert metrics.failed_vision_calls == 0
        assert metrics.slow_response_count == 0


class TestPerformanceMonitor:
    """Test the PerformanceMonitor class."""
    
    @pytest.fixture
    def monitor(self):
        """Create a fresh PerformanceMonitor for each test."""
        return PerformanceMonitor(slow_response_threshold=3.0)
    
    def test_initialization(self, monitor):
        """Test that monitor initializes correctly."""
        assert monitor.slow_response_threshold == 3.0
        assert monitor.metrics.total_vision_calls == 0
        assert monitor.start_time > 0
    
    @pytest.mark.asyncio
    async def test_monitor_vision_call_success(self, monitor):
        """Test monitoring a successful vision call."""
        async def mock_vision_call():
            await asyncio.sleep(0.1)
            return "Screen description"
        
        result = await monitor.monitor_vision_call(mock_vision_call)
        
        assert result == "Screen description"
        assert monitor.metrics.total_vision_calls == 1
        assert monitor.metrics.failed_vision_calls == 0
        assert len(monitor.metrics.vision_response_times) == 1
        assert monitor.metrics.vision_response_times[0] >= 0.1
    
    @pytest.mark.asyncio
    async def test_monitor_vision_call_failure(self, monitor):
        """Test monitoring a failed vision call."""
        async def mock_failing_call():
            await asyncio.sleep(0.05)
            raise ValueError("API error")
        
        with pytest.raises(ValueError, match="API error"):
            await monitor.monitor_vision_call(mock_failing_call)
        
        assert monitor.metrics.total_vision_calls == 1
        assert monitor.metrics.failed_vision_calls == 1
        assert len(monitor.metrics.vision_response_times) == 0  # Failed calls don't record time
    
    @pytest.mark.asyncio
    async def test_monitor_vision_call_slow_response(self, monitor):
        """Test that slow responses are detected and alerted."""
        async def mock_slow_call():
            await asyncio.sleep(3.5)
            return "Slow response"
        
        result = await monitor.monitor_vision_call(mock_slow_call)
        
        assert result == "Slow response"
        assert monitor.metrics.slow_response_count == 1
        assert monitor.metrics.vision_response_times[0] >= 3.5
    
    def test_record_action_result_success(self, monitor):
        """Test recording successful action results."""
        monitor.record_action_result(True)
        monitor.record_action_result(True)
        monitor.record_action_result(True)
        
        assert len(monitor.metrics.action_success_rates) == 3
        assert sum(monitor.metrics.action_success_rates) == 3
    
    def test_record_action_result_failure(self, monitor):
        """Test recording failed action results."""
        monitor.record_action_result(False)
        monitor.record_action_result(False)
        
        assert len(monitor.metrics.action_success_rates) == 2
        assert sum(monitor.metrics.action_success_rates) == 0
    
    def test_record_action_result_mixed(self, monitor):
        """Test recording mixed action results."""
        monitor.record_action_result(True)
        monitor.record_action_result(False)
        monitor.record_action_result(True)
        monitor.record_action_result(True)
        
        assert len(monitor.metrics.action_success_rates) == 4
        assert sum(monitor.metrics.action_success_rates) == 3
    
    def test_record_cache_hit(self, monitor):
        """Test recording cache hits."""
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        
        assert monitor.metrics.cache_hits == 3
        assert monitor.metrics.cache_misses == 0
    
    def test_record_cache_miss(self, monitor):
        """Test recording cache misses."""
        monitor.record_cache_miss()
        monitor.record_cache_miss()
        
        assert monitor.metrics.cache_hits == 0
        assert monitor.metrics.cache_misses == 2
    
    def test_get_cache_hit_rate_no_operations(self, monitor):
        """Test cache hit rate with no operations."""
        assert monitor.get_cache_hit_rate() == 0.0
    
    def test_get_cache_hit_rate_all_hits(self, monitor):
        """Test cache hit rate with all hits."""
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        
        assert monitor.get_cache_hit_rate() == 100.0
    
    def test_get_cache_hit_rate_all_misses(self, monitor):
        """Test cache hit rate with all misses."""
        monitor.record_cache_miss()
        monitor.record_cache_miss()
        
        assert monitor.get_cache_hit_rate() == 0.0
    
    def test_get_cache_hit_rate_mixed(self, monitor):
        """Test cache hit rate with mixed hits and misses."""
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()  # 7 hits
        monitor.record_cache_miss()
        monitor.record_cache_miss()
        monitor.record_cache_miss()  # 3 misses
        
        # 7 hits out of 10 total = 70%
        assert monitor.get_cache_hit_rate() == 70.0
    
    def test_get_action_success_rate_no_actions(self, monitor):
        """Test action success rate with no actions."""
        assert monitor.get_action_success_rate() == 0.0
    
    def test_get_action_success_rate_all_success(self, monitor):
        """Test action success rate with all successes."""
        monitor.record_action_result(True)
        monitor.record_action_result(True)
        monitor.record_action_result(True)
        
        assert monitor.get_action_success_rate() == 100.0
    
    def test_get_action_success_rate_all_failures(self, monitor):
        """Test action success rate with all failures."""
        monitor.record_action_result(False)
        monitor.record_action_result(False)
        
        assert monitor.get_action_success_rate() == 0.0
    
    def test_get_action_success_rate_mixed(self, monitor):
        """Test action success rate with mixed results."""
        monitor.record_action_result(True)
        monitor.record_action_result(True)
        monitor.record_action_result(False)
        monitor.record_action_result(True)
        
        # 3 successes out of 4 = 75%
        assert monitor.get_action_success_rate() == 75.0
    
    def test_get_vision_success_rate_no_calls(self, monitor):
        """Test vision success rate with no calls."""
        assert monitor.get_vision_success_rate() == 0.0
    
    @pytest.mark.asyncio
    async def test_get_vision_success_rate_all_success(self, monitor):
        """Test vision success rate with all successful calls."""
        async def mock_call():
            return "Success"
        
        await monitor.monitor_vision_call(mock_call)
        await monitor.monitor_vision_call(mock_call)
        await monitor.monitor_vision_call(mock_call)
        
        assert monitor.get_vision_success_rate() == 100.0
    
    @pytest.mark.asyncio
    async def test_get_vision_success_rate_mixed(self, monitor):
        """Test vision success rate with mixed results."""
        async def mock_success():
            return "Success"
        
        async def mock_failure():
            raise ValueError("Error")
        
        await monitor.monitor_vision_call(mock_success)
        await monitor.monitor_vision_call(mock_success)
        
        try:
            await monitor.monitor_vision_call(mock_failure)
        except ValueError:
            pass
        
        await monitor.monitor_vision_call(mock_success)
        
        # 3 successes out of 4 = 75%
        assert monitor.get_vision_success_rate() == 75.0
    
    @pytest.mark.asyncio
    async def test_get_performance_stats_comprehensive(self, monitor):
        """Test comprehensive performance statistics."""
        # Add vision calls
        async def mock_call(duration):
            await asyncio.sleep(duration)
            return "Result"
        
        await monitor.monitor_vision_call(mock_call, 0.5)
        await monitor.monitor_vision_call(mock_call, 1.0)
        await monitor.monitor_vision_call(mock_call, 1.5)
        
        # Add action results
        monitor.record_action_result(True)
        monitor.record_action_result(True)
        monitor.record_action_result(False)
        
        # Add cache operations
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_hit()
        monitor.record_cache_miss()
        monitor.record_cache_miss()
        monitor.record_cache_miss()
        
        stats = monitor.get_performance_stats()
        
        # Verify structure
        assert "vision_metrics" in stats
        assert "action_metrics" in stats
        assert "cache_metrics" in stats
        assert "system_metrics" in stats
        assert "alerts" in stats
        
        # Verify vision metrics
        assert stats["vision_metrics"]["total_calls"] == 3
        assert stats["vision_metrics"]["failed_calls"] == 0
        assert stats["vision_metrics"]["success_rate"] == 100.0
        assert stats["vision_metrics"]["avg_response_time"] > 0
        
        # Verify action metrics
        assert stats["action_metrics"]["total_actions"] == 3
        assert stats["action_metrics"]["success_rate"] == pytest.approx(66.67, rel=0.1)
        
        # Verify cache metrics
        assert stats["cache_metrics"]["hits"] == 7
        assert stats["cache_metrics"]["misses"] == 3
        assert stats["cache_metrics"]["hit_rate"] == 70.0
        
        # Verify system metrics
        assert stats["system_metrics"]["uptime_seconds"] > 0
        assert stats["system_metrics"]["uptime_hours"] >= 0  # Can be 0 for very short tests
    
    def test_generate_alerts_no_data(self, monitor):
        """Test alert generation with no data."""
        alerts = monitor._generate_alerts()
        assert alerts == []
    
    @pytest.mark.asyncio
    async def test_generate_alerts_slow_average_response(self, monitor):
        """Test alert for slow average response time."""
        async def mock_slow_call():
            await asyncio.sleep(2.5)
            return "Result"
        
        # Add multiple slow calls to get average > 2 seconds
        await monitor.monitor_vision_call(mock_slow_call)
        await monitor.monitor_vision_call(mock_slow_call)
        await monitor.monitor_vision_call(mock_slow_call)
        
        alerts = monitor._generate_alerts()
        
        # Should have alert for slow average response
        assert any(alert["metric"] == "vision_response_time" for alert in alerts)
        assert any("exceeds 2 second target" in alert["message"] for alert in alerts)
    
    @pytest.mark.asyncio
    async def test_generate_alerts_low_vision_success_rate(self, monitor):
        """Test alert for low vision success rate."""
        async def mock_success():
            return "Success"
        
        async def mock_failure():
            raise ValueError("Error")
        
        # Create 15 calls with 80% success rate (below 95% threshold)
        for _ in range(12):
            await monitor.monitor_vision_call(mock_success)
        
        for _ in range(3):
            try:
                await monitor.monitor_vision_call(mock_failure)
            except ValueError:
                pass
        
        alerts = monitor._generate_alerts()
        
        # Should have alert for low success rate
        assert any(alert["metric"] == "vision_success_rate" for alert in alerts)
        assert any("below 95% threshold" in alert["message"] for alert in alerts)
    
    def test_generate_alerts_low_cache_hit_rate(self, monitor):
        """Test alert for low cache hit rate."""
        # Create 30 cache operations with 60% hit rate (below 70% threshold)
        for _ in range(18):
            monitor.record_cache_hit()
        for _ in range(12):
            monitor.record_cache_miss()
        
        alerts = monitor._generate_alerts()
        
        # Should have alert for low cache hit rate
        assert any(alert["metric"] == "cache_hit_rate" for alert in alerts)
        assert any("below 70% target" in alert["message"] for alert in alerts)
    
    @pytest.mark.asyncio
    async def test_generate_alerts_multiple_slow_responses(self, monitor):
        """Test alert for multiple slow responses."""
        async def mock_very_slow_call():
            await asyncio.sleep(3.5)
            return "Result"
        
        # Create 6 slow responses (> threshold of 5)
        for _ in range(6):
            await monitor.monitor_vision_call(mock_very_slow_call)
        
        alerts = monitor._generate_alerts()
        
        # Should have alert for slow responses
        assert any(alert["metric"] == "slow_responses" for alert in alerts)
        assert any("slow responses" in alert["message"] for alert in alerts)
    
    def test_reset_metrics(self, monitor):
        """Test that reset_metrics clears all data."""
        # Add some data
        monitor.metrics.vision_response_times.append(1.5)
        monitor.metrics.action_success_rates.append(1)
        monitor.metrics.cache_hits = 10
        monitor.metrics.total_vision_calls = 5
        
        # Reset
        monitor.reset_metrics()
        
        # Verify cleared
        assert len(monitor.metrics.vision_response_times) == 0
        assert len(monitor.metrics.action_success_rates) == 0
        assert monitor.metrics.cache_hits == 0
        assert monitor.metrics.total_vision_calls == 0


class TestGlobalPerformanceMonitor:
    """Test the global performance monitor functions."""
    
    def test_get_performance_monitor_singleton(self):
        """Test that get_performance_monitor returns a singleton."""
        reset_performance_monitor()
        
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2
    
    def test_reset_performance_monitor(self):
        """Test that reset creates a new instance."""
        monitor1 = get_performance_monitor()
        reset_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is not monitor2


class TestPerformanceMonitorEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @pytest.fixture
    def monitor(self):
        """Create a fresh PerformanceMonitor for each test."""
        return PerformanceMonitor()
    
    def test_deque_maxlen_enforcement(self, monitor):
        """Test that deques enforce maxlen of 100."""
        # Add 150 vision response times
        for i in range(150):
            monitor.metrics.vision_response_times.append(float(i))
        
        # Should only keep last 100
        assert len(monitor.metrics.vision_response_times) == 100
        assert monitor.metrics.vision_response_times[0] == 50.0
        assert monitor.metrics.vision_response_times[-1] == 149.0
    
    @pytest.mark.asyncio
    async def test_monitor_with_zero_duration(self, monitor):
        """Test monitoring a call that completes instantly."""
        async def instant_call():
            return "Instant"
        
        result = await monitor.monitor_vision_call(instant_call)
        
        assert result == "Instant"
        assert len(monitor.metrics.vision_response_times) == 1
        assert monitor.metrics.vision_response_times[0] >= 0
    
    def test_percentile_calculation_single_value(self, monitor):
        """Test p95 calculation with a single value."""
        monitor.metrics.vision_response_times.append(1.5)
        
        stats = monitor.get_performance_stats()
        
        # With single value, p95 should equal that value
        assert stats["vision_metrics"]["p95_response_time"] == 1.5
    
    def test_custom_slow_response_threshold(self):
        """Test custom slow response threshold."""
        monitor = PerformanceMonitor(slow_response_threshold=5.0)
        
        assert monitor.slow_response_threshold == 5.0
