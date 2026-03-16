"""
Test suite for connection recovery and resilience
Tests reconnection logic, state restoration, and error recovery.

NOTE: SpectraStreamingSession no longer exposes reconnect/restore_state/request_queue
or checkpoint APIs; it is a WebSocket-to-Gemini bridge with internal reconnection.
These tests are skipped until rewritten to match the current session API.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

# Current SpectraStreamingSession(websocket, user_id, session_id) has no reconnect(),
# restore_state(), request_queue, handle_api_error, checkpoints, etc.
pytestmark = pytest.mark.skip(reason="Session API changed; tests target legacy reconnect/checkpoint API")


class TestConnectionRecovery:
    """Test connection recovery mechanisms"""
    
    @pytest.mark.asyncio
    async def test_reconnect_after_disconnect(self):
        """Should reconnect after connection loss"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Simulate connection
        session.connected = True
        
        # Simulate disconnect
        session.connected = False
        
        # Attempt reconnect
        with patch.object(session, '_connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            result = await session.reconnect()
            
            assert result is True
            assert mock_connect.called
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_retry(self):
        """Should use exponential backoff for retries"""
        session = SpectraStreamingSession(user_id="test_user")
        retry_delays = []
        
        async def mock_sleep(delay):
            retry_delays.append(delay)
        
        with patch('asyncio.sleep', side_effect=mock_sleep):
            with patch.object(session, '_connect', new_callable=AsyncMock) as mock_connect:
                # Fail first 3 attempts, succeed on 4th
                mock_connect.side_effect = [False, False, False, True]
                
                result = await session.reconnect_with_backoff(max_attempts=5)
                
                assert result is True
                assert len(retry_delays) == 3  # 3 retries before success
                # Check exponential backoff: 1s, 2s, 4s
                assert retry_delays[0] == 1
                assert retry_delays[1] == 2
                assert retry_delays[2] == 4
    
    @pytest.mark.asyncio
    async def test_max_retry_attempts(self):
        """Should stop after max retry attempts"""
        session = SpectraStreamingSession(user_id="test_user")
        
        with patch.object(session, '_connect', new_callable=AsyncMock) as mock_connect:
            # Always fail
            mock_connect.return_value = False
            
            result = await session.reconnect_with_backoff(max_attempts=3)
            
            assert result is False
            assert mock_connect.call_count == 3
    
    @pytest.mark.asyncio
    async def test_state_restoration_after_reconnect(self):
        """Should restore session state after reconnection"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Set up initial state
        session.conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        session.user_preferences = {"voice": "aoede", "speed": 1.0}
        
        # Simulate disconnect and reconnect
        session.connected = False
        
        with patch.object(session, '_connect', new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = True
            await session.reconnect()
            await session.restore_state()
            
            # State should be preserved
            assert len(session.conversation_history) == 2
            assert session.user_preferences["voice"] == "aoede"


class TestAPIErrorHandling:
    """Test API error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_queues_request(self):
        """Should queue request when rate limited"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Simulate rate limit error
        error = Mock()
        error.type = "rate_limit"
        error.retry_after = 5
        
        await session.handle_api_error(error)
        
        # Request should be queued
        assert len(session.request_queue) > 0
    
    @pytest.mark.asyncio
    async def test_quota_exceeded_switches_to_fallback(self):
        """Should switch to fallback model when quota exceeded"""
        session = SpectraStreamingSession(user_id="test_user")
        session.current_model = "gemini-2.0-flash-exp"
        
        # Simulate quota exceeded error
        error = Mock()
        error.type = "quota_exceeded"
        
        with patch.object(session, 'switch_to_fallback_model', new_callable=AsyncMock) as mock_switch:
            await session.handle_api_error(error)
            
            assert mock_switch.called
    
    @pytest.mark.asyncio
    async def test_network_error_triggers_reconnect(self):
        """Should trigger reconnect on network error"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Simulate network error
        error = Mock()
        error.type = "network_error"
        
        with patch.object(session, 'reconnect_with_backoff', new_callable=AsyncMock) as mock_reconnect:
            mock_reconnect.return_value = True
            await session.handle_api_error(error)
            
            assert mock_reconnect.called
    
    @pytest.mark.asyncio
    async def test_invalid_request_notifies_user(self):
        """Should notify user of invalid request"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Simulate invalid request error
        error = Mock()
        error.type = "invalid_request"
        error.message = "Invalid audio format"
        
        notifications = []
        
        async def mock_notify(message):
            notifications.append(message)
        
        with patch.object(session, 'notify_user', side_effect=mock_notify):
            await session.handle_api_error(error)
            
            assert len(notifications) > 0
            assert "invalid" in notifications[0].lower()


class TestGracefulDegradation:
    """Test graceful degradation when services are unavailable"""
    
    @pytest.mark.asyncio
    async def test_fallback_to_text_when_audio_fails(self):
        """Should fallback to text when audio processing fails"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Simulate audio processing failure
        with patch.object(session, 'process_audio', side_effect=Exception("Audio error")):
            with patch.object(session, 'process_text', new_callable=AsyncMock) as mock_text:
                mock_text.return_value = {"type": "text", "data": "Fallback response"}
                
                result = await session.handle_input(
                    audio_data=b"audio_bytes",
                    fallback_text="Hello"
                )
                
                assert result["type"] == "text"
                assert mock_text.called
    
    @pytest.mark.asyncio
    async def test_cached_response_when_api_unavailable(self):
        """Should use cached response when API is unavailable"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Set up cache
        session.response_cache["describe_screen"] = {
            "type": "text",
            "data": "Cached screen description"
        }
        
        # Simulate API unavailable
        with patch.object(session, 'call_gemini_api', side_effect=Exception("API unavailable")):
            result = await session.describe_screen(use_cache=True)
            
            assert result["data"] == "Cached screen description"
    
    @pytest.mark.asyncio
    async def test_basic_actions_work_offline(self):
        """Should support basic actions when offline"""
        session = SpectraStreamingSession(user_id="test_user")
        session.connected = False
        
        # Basic actions should still work
        actions = [
            {"type": "click", "x": 100, "y": 200},
            {"type": "scroll", "direction": "down"},
            {"type": "type", "text": "hello"}
        ]
        
        for action in actions:
            result = await session.execute_action_offline(action)
            assert result["status"] in ["queued", "executed"]


class TestConnectionMonitoring:
    """Test connection health monitoring"""
    
    @pytest.mark.asyncio
    async def test_heartbeat_detection(self):
        """Should detect missed heartbeats"""
        session = SpectraStreamingSession(user_id="test_user")
        session.last_heartbeat = asyncio.get_event_loop().time() - 60  # 60s ago
        
        is_healthy = session.check_connection_health()
        
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_automatic_reconnect_on_unhealthy(self):
        """Should automatically reconnect when connection is unhealthy"""
        session = SpectraStreamingSession(user_id="test_user")
        session.last_heartbeat = asyncio.get_event_loop().time() - 60
        
        with patch.object(session, 'reconnect_with_backoff', new_callable=AsyncMock) as mock_reconnect:
            mock_reconnect.return_value = True
            await session.monitor_connection_health()
            
            assert mock_reconnect.called
    
    @pytest.mark.asyncio
    async def test_connection_quality_metrics(self):
        """Should track connection quality metrics"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Simulate some latency measurements
        session.record_latency(50)
        session.record_latency(100)
        session.record_latency(75)
        
        metrics = session.get_connection_metrics()
        
        assert "average_latency" in metrics
        assert "packet_loss" in metrics
        assert metrics["average_latency"] == 75  # (50 + 100 + 75) / 3


class TestSessionRecovery:
    """Test session recovery after crashes"""
    
    @pytest.mark.asyncio
    async def test_recover_from_crash(self):
        """Should recover session state after crash"""
        # Create session and save state
        session1 = SpectraStreamingSession(user_id="test_user")
        session1.conversation_history = [{"role": "user", "content": "test"}]
        await session1.save_checkpoint()
        
        # Simulate crash and recovery
        session2 = SpectraStreamingSession(user_id="test_user")
        await session2.recover_from_checkpoint()
        
        assert len(session2.conversation_history) == 1
        assert session2.conversation_history[0]["content"] == "test"
    
    @pytest.mark.asyncio
    async def test_cleanup_old_checkpoints(self):
        """Should cleanup old checkpoints"""
        session = SpectraStreamingSession(user_id="test_user")
        
        # Create multiple checkpoints
        for i in range(10):
            await session.save_checkpoint()
            await asyncio.sleep(0.1)
        
        # Cleanup old ones (keep only last 3)
        await session.cleanup_checkpoints(keep_last=3)
        
        checkpoints = await session.list_checkpoints()
        assert len(checkpoints) <= 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
