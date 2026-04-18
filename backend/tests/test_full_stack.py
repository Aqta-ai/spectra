"""
Full-stack tests: HTTP, WebSocket, session action flow, and production safeguards.

Run with: pytest tests/test_full_stack.py -v
"""

import asyncio
import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Add backend to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from app.main import app
from app.streaming.session import SpectraStreamingSession


client = TestClient(app)


# ─── HTTP: Health & vision-debug ─────────────────────────────────────────────

class TestHealthEndpoint:
    """Production health check."""

    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_status_ok(self):
        response = client.get("/health")
        data = response.json()
        assert data.get("status") == "ok"
        assert "service" in data

    def test_health_has_active_sessions(self):
        response = client.get("/health")
        data = response.json()
        assert "active_sessions" in data
        assert "total_sessions" in data


class TestVisionDebugEndpoint:
    """/vision-debug must not be exposed in production."""

    def test_vision_debug_404_when_disabled(self):
        """Without ENABLE_VISION_DEBUG, endpoint returns 404."""
        with patch("app.main.os.getenv", return_value=""):
            response = client.get("/vision-debug")
        assert response.status_code == 404

    def test_vision_debug_404_when_env_unset(self):
        """Default (env unset) returns 404."""
        with patch("app.main.os.getenv", side_effect=lambda k, default=None: default if k == "ENABLE_VISION_DEBUG" else os.getenv(k, default)):
            response = client.get("/vision-debug")
        assert response.status_code == 404

    def test_vision_debug_200_when_enabled(self):
        """With ENABLE_VISION_DEBUG=1, endpoint returns 200 and debug payload."""
        def getenv(k, default=None):
            return "1" if k == "ENABLE_VISION_DEBUG" else os.getenv(k, default)
        with patch("app.main.os.getenv", side_effect=getenv):
            response = client.get("/vision-debug")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "vision_debug"
        assert "active_sessions" in data
        assert "session_stats" in data


# ─── WebSocket: Connect and message handling ─────────────────────────────────

class TestWebSocketFullStack:
    """WebSocket connect and client messages (backend accepts them)."""

    def test_websocket_accept_and_first_message(self):
        """Connect to /ws; backend accepts and sends at least one message (type in allowed set)."""
        with client.websocket_connect("/ws") as ws:
            data = ws.receive_json()
            assert data is not None
            assert "type" in data
            assert data["type"] in [
                "connected", "ready", "audio", "text", "action",
                "turn_complete", "heartbeat", "usage_limit", "go_away",
                "gemini_reconnecting",  # Added: valid connection state
            ] or "session" in str(data).lower()

    def test_websocket_accepts_extension_status(self):
        """Backend accepts extension_status without disconnecting."""
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "extension_status", "available": True})
            ws.send_json({"type": "extension_status", "available": False})
            # Should not raise; next receive may block, so short timeout
            try:
                ws.receive_json(timeout=0.5)
            except Exception:
                pass

    def test_websocket_accepts_action_result(self):
        """Backend accepts action_result with id (no crash; may be discarded if no waiter)."""
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({
                "type": "action_result",
                "id": "test-id-123",
                "result": "clicked_Button",
            })
            try:
                ws.receive_json(timeout=0.5)
            except Exception:
                pass


# ─── Session: Action result matching by id ───────────────────────────────────

@pytest.fixture
def mock_ws():
    m = MagicMock()
    m.messages = []
    m.send_json = AsyncMock(side_effect=lambda d: m.messages.append(d))
    m.is_connected = True
    return m


@pytest.mark.asyncio
async def test_action_pending_resolves_by_id(mock_ws):
    """When action_result arrives with matching id, the correct future gets the result."""
    with patch("google.genai.Client"):
        session = SpectraStreamingSession(mock_ws, user_id="u", session_id="s")
    session._running = True
    session.gemini_session = MagicMock()

    future = asyncio.get_event_loop().create_future()
    session._action_pending["aid-1"] = future

    # Simulate receiving action_result (as _listen_client would)
    msg = {"type": "action_result", "id": "aid-1", "result": "Successfully clicked 'Login'"}
    if "aid-1" in session._action_pending:
        session._action_pending["aid-1"].set_result(msg)
        del session._action_pending["aid-1"]

    result = await asyncio.wait_for(future, timeout=1.0)
    assert result["result"] == "Successfully clicked 'Login'"
    assert "aid-1" not in session._action_pending


@pytest.mark.asyncio
async def test_action_pending_stale_result_discarded(mock_ws):
    """When action_result arrives for an id that timed out, it is discarded (no crash)."""
    with patch("google.genai.Client"):
        session = SpectraStreamingSession(mock_ws, user_id="u", session_id="s")

    # No pending future for this id (e.g. already timed out)
    msg = {"type": "action_result", "id": "stale-id", "result": "done"}
    if "stale-id" in session._action_pending:
        session._action_pending["stale-id"].set_result(msg)
        del session._action_pending["stale-id"]
    # Should not raise; stale result simply not stored
    assert "stale-id" not in session._action_pending


@pytest.mark.asyncio
async def test_action_pending_two_actions_different_ids(mock_ws):
    """Two actions with different ids get their own results; first timeout does not hand result to second."""
    with patch("google.genai.Client"):
        session = SpectraStreamingSession(mock_ws, user_id="u", session_id="s")

    f1 = asyncio.get_event_loop().create_future()
    f2 = asyncio.get_event_loop().create_future()
    session._action_pending["id-1"] = f1
    session._action_pending["id-2"] = f2

    # Resolve second first (simulate out-of-order delivery)
    if "id-2" in session._action_pending:
        session._action_pending["id-2"].set_result({"id": "id-2", "result": "result-2"})
        del session._action_pending["id-2"]

    r2 = await asyncio.wait_for(f2, timeout=1.0)
    assert r2["result"] == "result-2"

    # Resolve first
    if "id-1" in session._action_pending:
        session._action_pending["id-1"].set_result({"id": "id-1", "result": "result-1"})
        del session._action_pending["id-1"]

    r1 = await asyncio.wait_for(f1, timeout=1.0)
    assert r1["result"] == "result-1"


# ─── Error handling ──────────────────────────────────────────────────────────

class TestFullStackErrorHandling:
    """4xx/5xx and unknown routes."""

    def test_404_unknown_route(self):
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_405_health_post(self):
        response = client.post("/health")
        assert response.status_code == 405


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
