"""
Tests for Fast Response Pipeline
"""

import pytest
import asyncio
import hashlib
from app.streaming.fast_pipeline import (
    FastResponsePipeline,
    ActionPredictor,
    FrameDiffDetector,
    LRUCache,
    TTLCache,
)


class TestLRUCache:
    """Test LRU cache implementation"""
    
    def test_basic_operations(self):
        cache = LRUCache(maxsize=3)
        
        # Add items
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        
        # Retrieve items
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") == 3
    
    def test_eviction(self):
        cache = LRUCache(maxsize=2)
        
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # Should evict "a"
        
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
    
    def test_lru_order(self):
        cache = LRUCache(maxsize=2)
        
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")  # Access "a", making it most recent
        cache.put("c", 3)  # Should evict "b", not "a"
        
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3


class TestTTLCache:
    """Test TTL cache implementation"""
    
    def test_basic_operations(self):
        cache = TTLCache(maxsize=10, ttl=1.0)
        
        cache.put("key", "value")
        assert cache.get("key") == "value"
    
    @pytest.mark.asyncio
    async def test_expiration(self):
        cache = TTLCache(maxsize=10, ttl=0.1)
        
        cache.put("key", "value")
        assert cache.get("key") == "value"
        
        # Wait for expiration
        await asyncio.sleep(0.15)
        assert cache.get("key") is None
    
    def test_maxsize(self):
        cache = TTLCache(maxsize=2, ttl=10.0)
        
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)  # Should evict oldest
        
        # At least one should be evicted
        values = [cache.get("a"), cache.get("b"), cache.get("c")]
        assert None in values


class TestFrameDiffDetector:
    """Test frame difference detection"""
    
    def test_identical_frames(self):
        detector = FrameDiffDetector()
        
        frame_data = b"test frame data"
        hash1 = detector.calculate_hash(frame_data)
        hash2 = detector.calculate_hash(frame_data)
        
        assert hash1 == hash2
        assert detector.calculate_similarity(hash1, hash2) == 1.0
    
    def test_different_frames(self):
        detector = FrameDiffDetector()
        
        frame1 = b"frame 1"
        frame2 = b"frame 2"
        
        hash1 = detector.calculate_hash(frame1)
        hash2 = detector.calculate_hash(frame2)
        
        assert hash1 != hash2
        assert detector.calculate_similarity(hash1, hash2) < 1.0
    
    def test_significant_change_detection(self):
        detector = FrameDiffDetector()
        
        frame1 = b"frame 1"
        frame2 = b"frame 2"
        
        hash1 = detector.calculate_hash(frame1)
        hash2 = detector.calculate_hash(frame2)
        
        # First frame always has significant change
        assert detector.has_significant_change(hash1) is True
        
        # Same frame should not have significant change
        assert detector.has_significant_change(hash1) is False
        
        # Different frame should have significant change
        assert detector.has_significant_change(hash2) is True


class TestActionPredictor:
    """Test action prediction"""
    
    def test_navigate_prediction(self):
        predictor = ActionPredictor()
        
        predictions = predictor.predict("go to google", {})
        
        assert len(predictions) > 0
        assert predictions[0].action_type == "describe_screen"
        assert predictions[0].confidence > 0.7
    
    def test_click_prediction(self):
        predictor = ActionPredictor()
        
        predictions = predictor.predict("click the button", {})
        
        assert len(predictions) > 0
        assert predictions[0].action_type == "click_element"
        assert predictions[0].confidence > 0.7
    
    def test_type_prediction(self):
        predictor = ActionPredictor()
        
        predictions = predictor.predict("type hello world", {})
        
        assert len(predictions) > 0
        assert predictions[0].action_type == "type_text"
        assert predictions[0].confidence > 0.7
    
    def test_scroll_prediction(self):
        predictor = ActionPredictor()
        
        predictions = predictor.predict("scroll down", {})
        
        assert len(predictions) > 0
        assert predictions[0].action_type == "scroll_page"
        assert predictions[0].params.get("direction") == "down"
    
    def test_action_history(self):
        predictor = ActionPredictor()
        
        predictor.update_history("click_element", True)
        predictor.update_history("type_text", True)
        
        assert len(predictor.recent_actions) == 2
        assert predictor.recent_actions[0]["action"] == "click_element"
        assert predictor.recent_actions[0]["success"] is True


class TestFastResponsePipeline:
    """Test fast response pipeline"""
    
    @pytest.mark.asyncio
    async def test_process_command(self):
        pipeline = FastResponsePipeline()
        
        frame_data = b"test frame"
        command = "describe the screen"
        
        result = await pipeline.process_command(
            command=command,
            frame_data=frame_data,
            gemini_session=None
        )
        
        assert "frame_hash" in result
        assert "frame_changed" in result
        assert "predictions" in result
        assert "processing_time" in result
        assert result["processing_time"] < 0.1  # Should be fast
    
    @pytest.mark.asyncio
    async def test_caching(self):
        pipeline = FastResponsePipeline()
        
        frame_data = b"test frame"
        command = "describe the screen"
        
        # First request - cache miss
        result1 = await pipeline.process_command(
            command=command,
            frame_data=frame_data,
            gemini_session=None
        )
        
        # Cache the description
        pipeline.cache_frame_description(
            frame_hash=result1["frame_hash"],
            description="Test description",
            elements=[]
        )
        
        # Second request - cache hit
        result2 = await pipeline.process_command(
            command=command,
            frame_data=frame_data,
            gemini_session=None
        )
        
        assert result2["cached_description"] == "Test description"
        assert result2["frame_changed"] is False
    
    @pytest.mark.asyncio
    async def test_frame_change_detection(self):
        pipeline = FastResponsePipeline()
        
        frame1 = b"frame 1"
        frame2 = b"frame 2"
        
        # First frame
        result1 = await pipeline.process_command(
            command="test",
            frame_data=frame1,
            gemini_session=None
        )
        assert result1["frame_changed"] is True
        
        # Same frame
        result2 = await pipeline.process_command(
            command="test",
            frame_data=frame1,
            gemini_session=None
        )
        assert result2["frame_changed"] is False
        
        # Different frame
        result3 = await pipeline.process_command(
            command="test",
            frame_data=frame2,
            gemini_session=None
        )
        assert result3["frame_changed"] is True
    
    def test_metrics(self):
        pipeline = FastResponsePipeline()
        
        # Initial metrics
        metrics = pipeline.get_metrics()
        assert metrics["cache_hits"] == 0
        assert metrics["cache_misses"] == 0
        assert metrics["total_requests"] == 0
        
        # Reset metrics
        pipeline.reset_metrics()
        metrics = pipeline.get_metrics()
        assert metrics["total_requests"] == 0
    
    def test_action_result_update(self):
        pipeline = FastResponsePipeline()
        
        pipeline.update_action_result("click_element", True)
        pipeline.update_action_result("type_text", False)
        
        # Should update predictor history
        assert len(pipeline.action_predictor.recent_actions) == 2


@pytest.mark.asyncio
async def test_performance_target():
    """Test that pipeline meets performance targets"""
    pipeline = FastResponsePipeline()
    
    frame_data = b"test frame" * 1000  # Larger frame
    command = "describe the screen"
    
    # Measure processing time
    import time
    start = time.time()
    
    result = await pipeline.process_command(
        command=command,
        frame_data=frame_data,
        gemini_session=None
    )
    
    elapsed = time.time() - start
    
    # Should be very fast (< 10ms for local processing)
    assert elapsed < 0.01
    assert result["processing_time"] < 0.01


@pytest.mark.asyncio
async def test_cache_hit_rate():
    """Test cache hit rate with repeated frames"""
    pipeline = FastResponsePipeline()
    
    frame_data = b"test frame"
    
    # Process same frame multiple times
    for i in range(10):
        result = await pipeline.process_command(
            command=f"command {i}",
            frame_data=frame_data,
            gemini_session=None
        )
        
        if i == 0:
            # Cache first frame
            pipeline.cache_frame_description(
                frame_hash=result["frame_hash"],
                description="Test description",
                elements=[]
            )
    
    # Check metrics
    metrics = pipeline.get_metrics()
    
    # Should have high cache hit rate (9 hits out of 10 requests)
    assert metrics["cache_hit_rate"] > 0.8
    assert metrics["total_requests"] == 10
