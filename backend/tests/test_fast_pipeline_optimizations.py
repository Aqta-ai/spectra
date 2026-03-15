"""
Test suite for fast pipeline optimizations
Tests the enhanced performance features and smart caching
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock

from app.streaming.fast_pipeline import FastResponsePipeline, ActionPredictor, PredictedAction
from app.intelligence.context_engine import ContextualIntelligence, Intent
from app.performance_monitor import PerformanceMonitor, DegradationDetector


class TestFastResponsePipeline:
    """Test enhanced fast response pipeline"""
    
    @pytest.fixture
    def pipeline(self):
        return FastResponsePipeline()
    
    @pytest.fixture
    def mock_gemini_session(self):
        return Mock()
    
    @pytest.mark.asyncio
    async def test_enhanced_caching(self, pipeline, mock_gemini_session):
        """Test enhanced caching with intent analysis"""
        # First call - should miss cache
        frame_data = b"test_frame_data"
        command = "click the button"
        
        result1 = await pipeline.process_command(command, frame_data, mock_gemini_session)
        
        assert result1['cache_hit'] is False
        assert 'intent' in result1
        assert result1['intent']['type'] == 'click'
        
        # Second call with same data - should hit cache for high confidence
        result2 = await pipeline.process_command(command, frame_data, mock_gemini_session)
        
        # Should have intent cached
        assert result2['intent']['type'] == 'click'
    
    @pytest.mark.asyncio
    async def test_parallel_processing(self, pipeline, mock_gemini_session):
        """Test parallel processing optimization"""
        frame_data = b"test_frame_data"
        command = "describe the screen"
        
        start_time = time.time()
        result = await pipeline.process_command(command, frame_data, mock_gemini_session)
        duration = time.time() - start_time
        
        # Should complete quickly due to parallel processing
        assert duration < 0.1  # Very fast for test
        assert 'predictions' in result
        assert 'intent' in result
        assert result['processing_time'] > 0
    
    @pytest.mark.asyncio
    async def test_ultra_fast_responses(self, pipeline, mock_gemini_session):
        """Test ultra-fast response tracking"""
        frame_data = b"test_frame_data"
        command = "read this"
        
        # Process multiple commands to build cache
        for _ in range(3):
            await pipeline.process_command(command, frame_data, mock_gemini_session)
        
        metrics = pipeline.get_metrics()
        
        # Should track ultra-fast responses
        assert 'sub_200ms_responses' in metrics
        assert metrics['total_requests'] >= 3


class TestActionPredictor:
    """Test enhanced action predictor"""
    
    @pytest.fixture
    def predictor(self):
        return ActionPredictor()
    
    def test_enhanced_pattern_matching(self, predictor):
        """Test enhanced pattern matching"""
        predictions = predictor.predict("click the submit button", {})
        
        assert len(predictions) > 0
        assert predictions[0].action_type == 'click_element'
        assert predictions[0].confidence > 0.8
        assert predictions[0].params.get('smart_detection') is True
    
    def test_context_aware_prediction(self, predictor):
        """Test context-aware predictions"""
        screen_context = {
            'form_elements': [{'type': 'input', 'id': 'email'}],
            'nav_elements': [{'type': 'link', 'text': 'Home'}]
        }
        
        predictions = predictor.predict("fill out the form", screen_context)
        
        assert len(predictions) > 0
        # Should predict form interaction
        form_prediction = next((p for p in predictions if p.action_type == 'type_text'), None)
        assert form_prediction is not None
        assert form_prediction.params.get('form_aware') is True
    
    def test_learning_from_success(self, predictor):
        """Test learning from successful actions"""
        # Simulate successful actions
        predictor.update_history('click_element', True)
        predictor.update_history('click_element', True)
        predictor.update_history('click_element', False)
        
        stats = predictor.get_learning_stats()
        
        assert stats['total_actions'] == 3
        assert stats['recent_success_rate'] > 0.5
        assert 'click_element' in predictor.success_patterns
    
    def test_shortcut_learning(self, predictor):
        """Test command shortcut learning"""
        predictor.learn_shortcut(
            command="go home",
            action_type="navigate",
            params={'target': 'home'},
            confidence=0.8
        )
        
        predictions = predictor.predict("go home", {})
        
        # Should find the learned shortcut
        shortcut_prediction = next(
            (p for p in predictions if p.action_type == 'navigate'), 
            None
        )
        assert shortcut_prediction is not None


class TestContextualIntelligence:
    """Test contextual intelligence engine"""
    
    @pytest.fixture
    def engine(self):
        return ContextualIntelligence("test_user")
    
    @pytest.mark.asyncio
    async def test_intent_analysis(self, engine):
        """Test multi-level intent analysis"""
        history = [
            {'action': 'describe_screen', 'success': True},
            {'action': 'click_element', 'success': True}
        ]
        
        intent = await engine.analyze_intent("read the result", history)
        
        assert isinstance(intent, Intent)
        assert intent.surface == 'read'
        assert intent.deep == 'verify_action_result'  # Should infer deeper intent
        assert intent.confidence > 0.7
        assert len(intent.suggested_actions) > 0
    
    def test_learning_from_interaction(self, engine):
        """Test learning from user interactions"""
        interaction = {
            'command': 'click the button',
            'action': 'click_element',
            'success': True,
            'intent': 'click'
        }
        
        engine.learn_from_interaction(interaction)
        
        # Should update user patterns
        assert 'click' in engine.user_profile.success_patterns
        assert len(engine.session_history) == 1
        assert 'click' in engine.user_profile.vocabulary
    
    def test_workflow_pattern_detection(self, engine):
        """Test workflow pattern detection"""
        # Simulate a common workflow pattern
        interactions = [
            {'action': 'describe_screen', 'success': True},
            {'action': 'click_element', 'success': True},
            {'action': 'type_text', 'success': True}
        ]
        
        for interaction in interactions:
            engine.learn_from_interaction(interaction)
        
        # Repeat the pattern to establish it
        for _ in range(2):
            for interaction in interactions:
                engine.learn_from_interaction(interaction)
        
        # Should detect the workflow pattern
        assert len(engine.user_profile.common_workflows) > 0
        workflow = engine.user_profile.common_workflows[0]
        assert 'describe_screen->click_element->type_text' in workflow['pattern']


class TestPerformanceMonitor:
    """Test enhanced performance monitoring"""
    
    @pytest.fixture
    def monitor(self):
        return PerformanceMonitor()
    
    @pytest.mark.asyncio
    async def test_ultra_fast_detection(self, monitor):
        """Test ultra-fast response detection"""
        async def fast_function():
            await asyncio.sleep(0.1)  # 100ms - ultra fast
            return "result"
        
        result = await monitor.monitor_vision_call(fast_function)
        
        assert result == "result"
        stats = monitor.get_enhanced_statistics()
        assert stats['ultra_fast_responses'] > 0
    
    @pytest.mark.asyncio
    async def test_performance_trend_tracking(self, monitor):
        """Test performance trend tracking"""
        async def variable_function(delay):
            await asyncio.sleep(delay)
            return "result"
        
        # Simulate improving performance
        delays = [0.5, 0.4, 0.3, 0.2, 0.1]
        for delay in delays:
            await monitor.monitor_vision_call(variable_function, delay)
        
        stats = monitor.get_enhanced_statistics()
        assert stats['performance_trend'] in ['improving', 'stable']
    
    def test_optimization_suggestions(self, monitor):
        """Test optimization suggestion generation"""
        # Simulate low cache hit rate
        for _ in range(10):
            monitor.record_cache_miss()
        for _ in range(2):
            monitor.record_cache_hit()
        
        stats = monitor.get_enhanced_statistics()
        suggestions = stats['optimization_suggestions']
        
        assert len(suggestions) > 0
        assert any('cache hit rate' in s.lower() for s in suggestions)


class TestDegradationDetector:
    """Test performance degradation detection"""
    
    @pytest.fixture
    def detector(self):
        return DegradationDetector(window_size=10, threshold=1.5)
    
    def test_baseline_establishment(self, detector):
        """Test baseline performance establishment"""
        # Add consistent samples
        for _ in range(10):
            detector.add_sample(0.5)
        
        status = detector.get_status()
        assert status['baseline_established'] is True
        assert status['baseline_mean'] == 0.5
    
    def test_degradation_detection(self, detector):
        """Test degradation detection"""
        # Establish baseline with good performance
        for _ in range(10):
            detector.add_sample(0.5)
        
        # Add degraded samples
        for _ in range(5):
            detector.add_sample(2.0)  # Much slower
        
        assert detector.is_degrading() is True
    
    def test_no_false_positives(self, detector):
        """Test no false positive degradation alerts"""
        # Add consistent good samples
        for _ in range(15):
            detector.add_sample(0.5)
        
        assert detector.is_degrading() is False


@pytest.mark.integration
class TestIntegratedOptimizations:
    """Integration tests for all optimizations working together"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_optimization(self):
        """Test complete optimization pipeline"""
        pipeline = FastResponsePipeline()
        monitor = PerformanceMonitor()
        engine = ContextualIntelligence("test_user")
        
        # Simulate a complete interaction
        frame_data = b"test_frame"
        command = "click the login button"
        
        # Process with pipeline
        start_time = time.time()
        result = await pipeline.process_command(command, frame_data, Mock())
        duration = time.time() - start_time
        
        # Analyze intent
        intent = await engine.analyze_intent(command, [])
        
        # Learn from interaction
        engine.learn_from_interaction({
            'command': command,
            'action': 'click_element',
            'success': True,
            'intent': intent.surface
        })
        
        # Update predictor
        pipeline.update_action_result('click_element', True)
        
        # Verify optimizations
        assert result['processing_time'] < 1.0  # Should be fast
        assert intent.confidence > 0.7
        assert len(pipeline.action_predictor.recent_actions) > 0
        
        # Get comprehensive stats
        pipeline_metrics = pipeline.get_metrics()
        engine_data = engine.get_personalization_data()
        
        assert pipeline_metrics['total_requests'] > 0
        assert engine_data['session_stats']['total_interactions'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])