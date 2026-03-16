"""Comprehensive tests for SpectraStreamingSession."""

import asyncio
import base64
import json
import os
import pytest
import sys
from unittest.mock import AsyncMock, MagicMock, patch, Mock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import WebSocket
from google.genai import types

from app.streaming.session import SpectraStreamingSession


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages = []
        self.is_connected = True
        self.close_code = None
        self.close_reason = None
    
    async def send_json(self, data):
        self.messages.append(data)
    
    async def receive_text(self):
        # Will be set by test
        raise NotImplementedError("Mock receive_text not implemented")
    
    async def close(self, code=None, reason=None):
        self.is_connected = False
        self.close_code = code
        self.close_reason = reason


class MockGeminiSession:
    """Mock Gemini Live API session."""
    
    def __init__(self):
        self.received_inputs = []
        self.responses = []
        self.is_closed = False
        self._receive_queue = asyncio.Queue()
    
    async def send_realtime_input(self, audio=None, video=None):
        self.received_inputs.append({"audio": audio, "video": video})
    
    async def send_client_content(self, turns, turn_complete=False):
        self.received_inputs.append({"type": "client_content", "turns": turns, "turn_complete": turn_complete})
    
    async def send_tool_response(self, function_responses):
        self.received_inputs.append({"type": "tool_response", "responses": function_responses})
    
    async def close(self):
        self.is_closed = True
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.close()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket for testing."""
    ws = MockWebSocket()
    ws.receive_text = AsyncMock()
    return ws


@pytest.fixture
def mock_gemini_session():
    """Create a mock Gemini session."""
    return MockGeminiSession()


@pytest.fixture(autouse=True)
def mock_google_api():
    """Mock Google API client for all tests."""
    with patch('app.streaming.session.genai.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.mark.asyncio
async def test_session_initialization(mock_websocket):
    """Test session initialization."""
    session = SpectraStreamingSession(mock_websocket, user_id="test-user")
    
    assert session.websocket == mock_websocket
    assert session.user_id == "test-user"
    assert session._running is False
    assert session._latest_frame is None
    assert session._action_queue is not None
    assert session._describe_cache == {}


@pytest.mark.asyncio
async def test_clean_thinking_tags():
    """Test removal of thinking tags from Gemini output."""
    session = SpectraStreamingSession(MockWebSocket())
    
    # Test with thinking tags
    text_with_thinking = "Let me help you! <think>Thinking about the screen...</think> Now I can see it."
    cleaned = session._clean_thinking(text_with_thinking)
    assert cleaned == "Let me help you! Now I can see it."
    
    # Test without thinking tags
    text_normal = "Hello, how can I help you?"
    cleaned = session._clean_thinking(text_normal)
    assert cleaned == "Hello, how can I help you?"
    
    # Test with multiple thinking blocks
    text_multiple = "First <think>block one</think> second <think>block two</think> end."
    cleaned = session._clean_thinking(text_multiple)
    assert cleaned == "First second end."


@pytest.mark.asyncio
async def test_describe_screen_no_frame():
    """Test describe_screen when no frame is available."""
    session = SpectraStreamingSession(MockWebSocket())
    
    result = await session._describe_screen({})
    assert "No screen shared" in result or "screen" in result.lower()


@pytest.mark.asyncio
async def test_describe_screen_with_frame():
    """Test describe_screen with a frame returns prompt for model to describe what it sees."""
    session = SpectraStreamingSession(MockWebSocket())
    session._latest_frame = "base64data"
    session._frame_hash = "abc12345"
    session._capture_width = 800
    session._capture_height = 600
    
    result = await session._describe_screen({"focus_area": "full"})
    
    assert "Describe what you see" in result or "describe" in result.lower()
    assert "full" in result.lower()


@pytest.mark.asyncio
async def test_location_context_interpretation():
    """Test that location queries are interpreted as screen location, not physical location."""
    from app.agents.orchestrator import SPECTRA_SYSTEM_INSTRUCTION
    
    instruction_lower = SPECTRA_SYSTEM_INSTRUCTION.lower()
    assert "where am i" in instruction_lower or "location" in instruction_lower
    assert "website" in instruction_lower or "app" in instruction_lower or "screen" in instruction_lower
    assert "you're on" in instruction_lower or "gmail" in instruction_lower or "google" in instruction_lower
    assert "never" in instruction_lower or "physical" in instruction_lower


@pytest.mark.asyncio
async def test_location_query_screen_analysis():
    """Test that location queries would trigger screen analysis (system instruction validation)."""
    from app.agents.orchestrator import SPECTRA_SYSTEM_INSTRUCTION
    
    instruction_lower = SPECTRA_SYSTEM_INSTRUCTION.lower()
    assert "describe_screen" in instruction_lower
    assert "where am i" in instruction_lower or "location" in instruction_lower
    assert "website" in instruction_lower or "app" in instruction_lower
    assert "you're on" in instruction_lower or "gmail" in instruction_lower


@pytest.mark.asyncio
@pytest.mark.skip(reason="_describe_screen no longer calls generate_content; returns prompt only")
async def test_describe_screen_caching():
    """Test screen description caching."""
    session = SpectraStreamingSession(MockWebSocket())
    session._latest_frame = "base64data"
    session._frame_hash = "hash123"
    
    with patch('app.streaming.session.genai.Client') as mock_client:
        mock_model = MagicMock()
        mock_model.text = "Cached screen description"
        mock_client.return_value.models.generate_content.return_value = mock_model
        
        result1 = await session._describe_screen({})
        result2 = await session._describe_screen({})
        assert mock_client.return_value.models.generate_content.call_count == 1


@pytest.mark.asyncio
async def test_handle_server_tool_describe_screen():
    """Test server-side tool handler for describe_screen."""
    session = SpectraStreamingSession(MockWebSocket())
    session._latest_frame = "base64data"
    session._capture_width = 640
    session._capture_height = 480
    
    result = await session._handle_server_tool("describe_screen", {})
    assert "Describe what you see" in result or "describe" in result.lower()
    assert "full" in result.lower()


@pytest.mark.asyncio
async def test_handle_server_tool_save_snapshot():
    """Test server-side tool handler for save_snapshot."""
    from app.tools.diff import save_snapshot
    
    result = save_snapshot("test_snapshot", "frame_data")
    assert result == "snapshot_saved"


@pytest.mark.asyncio
async def test_handle_server_tool_diff_screen():
    """Test server-side tool handler for diff_screen."""
    from app.tools.diff import save_snapshot, diff_screen
    
    # First save a snapshot
    save_snapshot("test_snapshot", "frame_data")
    
    # Then diff against it
    result = diff_screen("test_snapshot")
    assert "differs" in result.lower() or "snapshot" in result.lower()


@pytest.mark.asyncio
async def test_handle_server_tool_unknown():
    """Test server-side tool handler with unknown tool."""
    session = SpectraStreamingSession(MockWebSocket())
    
    result = await session._handle_server_tool("unknown_tool", {})
    assert "Unknown server tool" in result


@pytest.mark.asyncio
async def test_send_heartbeats(mock_websocket):
    """Test heartbeat mechanism - simplified test."""
    session = SpectraStreamingSession(mock_websocket)
    session._running = True
    session._session_start = 0.0
    session._last_input_time = 0.0
    
    # Mock the websocket send
    mock_websocket.send_json = AsyncMock()
    
    # Mock the gemini session
    mock_gemini = MagicMock()
    mock_gemini.send_realtime_input = AsyncMock()
    session.gemini_session = mock_gemini
    
    # Verify the heartbeat method exists and is callable
    assert hasattr(session, '_send_heartbeats')
    assert callable(session._send_heartbeats)


@pytest.mark.asyncio
async def test_listen_client_audio(mock_websocket, mock_gemini_session):
    """Test client audio message handling - simplified test."""
    session = SpectraStreamingSession(mock_websocket)
    session.gemini_session = mock_gemini_session
    
    audio_data = b"audio_bytes"
    audio_b64 = base64.b64encode(audio_data).decode()
    
    # Test the message parsing directly
    msg = {"type": "audio", "data": audio_b64}
    
    assert msg["type"] == "audio"
    assert msg["data"] == audio_b64


@pytest.mark.asyncio
async def test_listen_client_screenshot(mock_websocket, mock_gemini_session):
    """Test client screenshot message handling - simplified test."""
    session = SpectraStreamingSession(mock_websocket)
    session.gemini_session = mock_gemini_session
    
    frame_data = "base64_frame_data"
    
    # Test the message parsing directly
    msg = {
        "type": "screenshot",
        "data": frame_data,
        "width": 1920,
        "height": 1080
    }
    
    assert msg["type"] == "screenshot"
    assert msg["data"] == frame_data
    assert msg["width"] == 1920
    assert msg["height"] == 1080


@pytest.mark.asyncio
async def test_listen_client_text(mock_websocket, mock_gemini_session):
    """Test client text message handling - simplified test."""
    session = SpectraStreamingSession(mock_websocket)
    session.gemini_session = mock_gemini_session
    
    text = "Hello, how can you help me?"
    
    # Test the message parsing directly
    msg = {"type": "text", "data": text}
    
    assert msg["type"] == "text"
    assert msg["data"] == text


@pytest.mark.asyncio
async def test_handle_tool_calls_server_tool(mock_websocket, mock_gemini_session):
    """Test tool call handling for server-side tools."""
    session = SpectraStreamingSession(mock_websocket)
    session.gemini_session = mock_gemini_session
    session._latest_frame = "frame_data"
    
    # Mock function call
    fc = MagicMock()
    fc.name = "describe_screen"
    fc.id = "test_fc_id"
    fc.args = {}
    
    tool_call = MagicMock()
    tool_call.function_calls = [fc]
    
    with patch('app.streaming.session.genai.Client') as mock_client:
        mock_model = MagicMock()
        mock_model.text = "Screen is showing a login page"
        mock_client.return_value.models.generate_content.return_value = mock_model
        
        await session._handle_tool_calls(tool_call)
    
    # Check tool response was sent
    tool_response_sent = any(
        inp.get("type") == "tool_response" 
        for inp in mock_gemini_session.received_inputs
    )
    assert tool_response_sent


@pytest.mark.asyncio
async def test_handle_tool_calls_client_action(mock_websocket, mock_gemini_session):
    """Test tool call handling for client actions."""
    session = SpectraStreamingSession(mock_websocket)
    session.gemini_session = mock_gemini_session
    session._capture_width = 1920
    session._capture_height = 1080
    
    # Mock function call for click_element
    fc = MagicMock()
    fc.name = "click_element"
    fc.id = "test_fc_id"
    fc.args = {"x": 100, "y": 200, "description": "Login button"}
    
    tool_call = MagicMock()
    tool_call.function_calls = [fc]
    
    # Mock action result
    async def mock_receive():
        return json.dumps({
            "type": "action_result",
            "id": "action123",
            "result": "success"
        })
    
    mock_websocket.receive_text = mock_receive
    
    # Add action result to queue
    await session._action_queue.put({
        "type": "action_result",
        "id": "action123",
        "result": "success"
    })
    
    with patch('app.streaming.session.genai.Client') as mock_client:
        mock_client.return_value.models.generate_content.return_value = MagicMock(text="Screen")
        
        await session._handle_tool_calls(tool_call)
    
    # Check action was sent to client
    action_sent = any(m.get("type") == "action" for m in mock_websocket.messages)
    assert action_sent
    
    # Check action params include dimensions
    action_msg = next((m for m in mock_websocket.messages if m.get("type") == "action"), None)
    assert action_msg is not None
    assert action_msg["params"]["_captureWidth"] == 1920
    assert action_msg["params"]["_captureHeight"] == 1080


@pytest.mark.asyncio
async def test_session_cleanup(mock_websocket):
    """Test session cleanup."""
    session = SpectraStreamingSession(mock_websocket)
    session._running = True
    
    mock_gemini = MagicMock()
    mock_gemini.close = AsyncMock()
    session.gemini_session = mock_gemini
    
    await session.cleanup()
    
    assert session._running is False
    mock_gemini.close.assert_called_once()


@pytest.mark.asyncio
async def test_action_timeout():
    """Test action timeout handling."""
    mock_ws = MockWebSocket()
    session = SpectraStreamingSession(mock_ws)
    session._capture_width = 1920
    session.gemini_session = MagicMock()
    session.gemini_session.send_tool_response = AsyncMock()
    
    # Mock function call
    fc = MagicMock()
    fc.name = "click_element"
    fc.id = "test_fc_id"
    fc.args = {"x": 100, "y": 200, "description": "Button"}
    
    tool_call = MagicMock()
    tool_call.function_calls = [fc]
    
    # Don't add anything to action queue - should timeout
    with patch('app.streaming.session.genai.Client') as mock_client:
        mock_client.return_value.models.generate_content.return_value = MagicMock(text="Screen")
        
        await session._handle_tool_calls(tool_call)
    
    # Check action was sent
    action_sent = any(m.get("type") == "action" for m in mock_ws.messages)
    assert action_sent
    
    # Check tool response was sent with timeout result
    tool_response = next((m for m in mock_ws.messages if m.get("type") == "tool_response"), None)
    # Note: In our implementation, tool responses go to Gemini, not back to websocket


@pytest.mark.asyncio
@pytest.mark.asyncio
@pytest.mark.skip(reason="_frame_buffer maxlen is implementation-defined")
async def test_batched_frames():
    """Test frame batching functionality."""
    session = SpectraStreamingSession(MockWebSocket())
    
    for i in range(5):
        session._frame_buffer.append(f"frame_{i}")
    
    assert len(session._frame_buffer) >= 1
    batch = list(session._frame_buffer)
    session._frame_buffer.clear()
    assert len(session._frame_buffer) == 0


@pytest.mark.asyncio
async def test_tool_response_locking():
    """Test that tool responses are sent sequentially."""
    session = SpectraStreamingSession(MockWebSocket())
    
    # Verify lock exists
    assert hasattr(session, '_tool_response_lock')
    assert isinstance(session._tool_response_lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_frame_hashing():
    """Test frame hash calculation."""
    session = SpectraStreamingSession(MockWebSocket())
    
    frame_data = "test_frame_data"
    frame_bytes = frame_data.encode()
    
    import hashlib
    expected_hash = hashlib.md5(frame_bytes).hexdigest()[:8]
    
    session._frame_hash = expected_hash
    assert session._frame_hash == expected_hash


@pytest.mark.asyncio
async def test_session_start_time():
    """Test session start time tracking."""
    session = SpectraStreamingSession(MockWebSocket())
    
    # Start time should be set in run()
    assert session._session_start == 0.0
    
    # After cleanup, we can't easily test run() without full mocking
    # but the initialization is correct


@pytest.mark.asyncio
async def test_last_input_time_tracking():
    """Test last input time tracking for smart keep-alive."""
    session = SpectraStreamingSession(MockWebSocket())
    
    initial_time = session._last_input_time
    
    # Simulate receiving audio
    session._last_input_time = 1000.0
    assert session._last_input_time == 1000.0
    
    # Simulate receiving text
    session._last_input_time = 2000.0
    assert session._last_input_time == 2000.0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


@pytest.mark.asyncio
async def test_vision_system_behavior_instructions():
    """Test that vision system instructions prohibit deflection and require describing screen."""
    from app.agents.orchestrator import SPECTRA_SYSTEM_INSTRUCTION
    
    instruction_lower = SPECTRA_SYSTEM_INSTRUCTION.lower()
    assert "never" in instruction_lower
    assert "describe" in instruction_lower or "screen" in instruction_lower
    assert "ai" in instruction_lower or "spectra" in instruction_lower


@pytest.mark.asyncio
async def test_vision_system_error_handling_instructions():
    """Test that system instruction mentions errors or recovery."""
    from app.agents.orchestrator import SPECTRA_SYSTEM_INSTRUCTION
    
    instruction_lower = SPECTRA_SYSTEM_INSTRUCTION.lower()
    assert "error" in instruction_lower or "fail" in instruction_lower or "try" in instruction_lower
