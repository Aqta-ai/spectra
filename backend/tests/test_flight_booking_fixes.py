"""Tests for flight booking fixes — describe_screen staleness, wait_for_content tool,
system instruction updates, and orchestrator tool registration."""

import asyncio
import base64
import os
import sys
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─── Helpers ────────────────────────────────────────────────────────────────

class MockWebSocket:
    def __init__(self):
        self.messages = []
        self.is_connected = True

    async def send_json(self, data):
        self.messages.append(data)

    async def close(self, code=None, reason=None):
        self.is_connected = False


@pytest.fixture(autouse=True)
def mock_google_api():
    with patch('app.streaming.session.genai.Client') as mock_client:
        mock_client.return_value = MagicMock()
        yield mock_client.return_value


@pytest.fixture
def session():
    from app.streaming.session import SpectraStreamingSession
    s = SpectraStreamingSession(MockWebSocket(), user_id="test-user")
    return s


# ─── describe_screen improvements ──────────────────────────────────────────

class TestDescribeScreenImprovements:
    """Tests for the improved _describe_screen method."""

    @pytest.mark.asyncio
    async def test_no_frame_never_shared_first_request(self, session):
        """First call with no frame and no prior screen share asks user to press W."""
        session._latest_frame = None
        session._screen_ever_shared = False

        result = await session._describe_screen({})
        assert "No screen shared" in result
        assert hasattr(session, '_screen_share_requested')

    @pytest.mark.asyncio
    async def test_no_frame_never_shared_second_request(self, session):
        """Second call with no frame returns 'Still waiting' — no repeat prompt."""
        session._latest_frame = None
        session._screen_ever_shared = False
        session._screen_share_requested = True

        result = await session._describe_screen({})
        assert "Still waiting" in result

    @pytest.mark.asyncio
    async def test_no_frame_previously_shared_suggests_read_page_structure(self, session):
        """When screen was shared but frame is missing, fallback should suggest read_page_structure."""
        session._latest_frame = None
        session._screen_ever_shared = True

        result = await session._describe_screen({})
        assert "read_page_structure" in result
        assert "Do NOT ask the user to share" in result

    @pytest.mark.asyncio
    async def test_no_frame_previously_shared_never_asks_share(self, session):
        """Fallback when screen was shared must NEVER contain 'press W' or 'share your screen'."""
        session._latest_frame = None
        session._screen_ever_shared = True

        result = await session._describe_screen({})
        assert "press W" not in result.lower()
        assert "share your screen" not in result.lower()

    @pytest.mark.asyncio
    async def test_fresh_frame_returns_screen_shared(self, session):
        """With a fresh frame, returns standard SCREEN IS SHARED prompt."""
        session._latest_frame = base64.b64encode(b"fake_frame").decode()
        session._capture_width = 1920
        session._capture_height = 1080
        session.last_frame_ts = time.time()

        result = await session._describe_screen({"focus_area": "full"})
        assert "[SCREEN IS SHARED" in result
        assert "1920x1080" in result

    @pytest.mark.asyncio
    async def test_stale_frame_includes_warning(self, session):
        """Frame older than 3s should include a staleness warning."""
        session._latest_frame = base64.b64encode(b"fake_frame").decode()
        session._capture_width = 1920
        session._capture_height = 1080
        session.last_frame_ts = time.time() - 4.0  # 4s old

        result = await session._describe_screen({"focus_area": "full"})
        assert "old" in result.lower()
        assert "read_page_structure" in result

    @pytest.mark.asyncio
    async def test_recent_frame_no_staleness_warning(self, session):
        """Frame under 3s should NOT include a staleness warning."""
        session._latest_frame = base64.b64encode(b"fake_frame").decode()
        session._capture_width = 800
        session._capture_height = 600
        session.last_frame_ts = time.time() - 1.0  # 1s old

        result = await session._describe_screen({"focus_area": "center"})
        assert "[SCREEN IS SHARED" in result
        assert "Frame is" not in result

    @pytest.mark.asyncio
    async def test_frame_arriving_during_wait_succeeds(self, session):
        """If a frame arrives while waiting, should return SCREEN IS SHARED (not fallback)."""
        session._screen_ever_shared = True
        session._capture_width = 1280
        session._capture_height = 720

        async def simulate_frame_arrival():
            await asyncio.sleep(0.3)
            session._latest_frame = base64.b64encode(b"new_frame").decode()
            session.last_frame_ts = time.time()

        asyncio.get_event_loop().create_task(simulate_frame_arrival())
        result = await session._describe_screen({})
        assert "[SCREEN IS SHARED" in result

    @pytest.mark.asyncio
    async def test_screen_share_requested_cleared_on_frame(self, session):
        """_screen_share_requested flag should be cleared when frame is present."""
        session._screen_share_requested = True
        session._latest_frame = base64.b64encode(b"frame").decode()
        session._capture_width = 640
        session._capture_height = 480
        session.last_frame_ts = time.time()

        await session._describe_screen({})
        assert not hasattr(session, '_screen_share_requested')


# ─── wait_for_content tool ─────────────────────────────────────────────────

class TestWaitForContent:
    """Tests for the new wait_for_content server tool."""

    @pytest.mark.asyncio
    async def test_fresh_frame_arrives(self, session):
        """When a new frame arrives during wait, returns SCREEN UPDATED."""
        session._latest_frame = base64.b64encode(b"old_frame").decode()
        session.last_frame_ts = time.time() - 1.0
        session._capture_width = 1920
        session._capture_height = 1080
        session.gemini_session = None

        baseline_ts = session.last_frame_ts

        async def simulate_frame():
            await asyncio.sleep(0.2)
            session.last_frame_ts = time.time()

        asyncio.get_event_loop().create_task(simulate_frame())

        result = await session._wait_for_content({"reason": "autocomplete suggestions", "wait_ms": 1000})
        assert "SCREEN UPDATED" in result
        assert "autocomplete suggestions" in result

    @pytest.mark.asyncio
    async def test_no_new_frame(self, session):
        """When no new frame arrives, returns guidance to use read_page_structure."""
        session._latest_frame = base64.b64encode(b"old_frame").decode()
        session.last_frame_ts = time.time() - 2.0
        session._capture_width = 800
        session._capture_height = 600
        session.gemini_session = None

        result = await session._wait_for_content({"reason": "dropdown", "wait_ms": 500})
        assert "no new frame" in result.lower()
        assert "read_page_structure" in result

    @pytest.mark.asyncio
    async def test_wait_ms_capped_at_5000(self, session):
        """wait_ms should be capped at 5000ms regardless of input."""
        session._latest_frame = base64.b64encode(b"frame").decode()
        session.last_frame_ts = time.time()
        session._capture_width = 800
        session._capture_height = 600
        session.gemini_session = None

        start = time.time()
        # Request 10s but cap should limit to 5s — and since frame is already present
        # it should return near-instantly (frame ts won't change in test)
        result = await session._wait_for_content({"reason": "test", "wait_ms": 10000})
        elapsed = time.time() - start
        assert elapsed < 6.0  # should be capped, and actually finish faster

    @pytest.mark.asyncio
    async def test_resends_frame_to_gemini(self, session):
        """Should re-send the latest frame to Gemini when a session exists."""
        session._latest_frame = base64.b64encode(b"frame_data").decode()
        session.last_frame_ts = time.time()
        session._capture_width = 800
        session._capture_height = 600
        session._running = True

        mock_gemini = MagicMock()
        mock_gemini.send_realtime_input = AsyncMock()
        session.gemini_session = mock_gemini

        await session._wait_for_content({"reason": "test", "wait_ms": 500})
        mock_gemini.send_realtime_input.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_server_tool_routes_wait_for_content(self, session):
        """_handle_server_tool should route wait_for_content correctly."""
        session._latest_frame = base64.b64encode(b"frame").decode()
        session.last_frame_ts = time.time()
        session._capture_width = 800
        session._capture_height = 600
        session.gemini_session = None

        result = await session._handle_server_tool("wait_for_content", {"reason": "test", "wait_ms": 500})
        assert "frame" in result.lower() or "SCREEN" in result

    @pytest.mark.asyncio
    async def test_default_wait_ms(self, session):
        """Should default to 2000ms when wait_ms not provided."""
        session._latest_frame = base64.b64encode(b"frame").decode()
        session.last_frame_ts = time.time()
        session._capture_width = 800
        session._capture_height = 600
        session.gemini_session = None

        start = time.time()
        result = await session._wait_for_content({"reason": "test"})
        elapsed = time.time() - start
        # Should wait up to 2s (default) — but finishes faster since no new frame
        assert elapsed < 3.0


# ─── SERVER_SIDE_TOOLS registration ────────────────────────────────────────

class TestServerSideToolsRegistration:
    """Tests that wait_for_content is properly registered."""

    def test_wait_for_content_in_server_side_tools(self):
        from app.streaming.session import SERVER_SIDE_TOOLS
        assert "wait_for_content" in SERVER_SIDE_TOOLS

    def test_describe_screen_still_registered(self):
        from app.streaming.session import SERVER_SIDE_TOOLS
        assert "describe_screen" in SERVER_SIDE_TOOLS

    def test_all_expected_tools_present(self):
        from app.streaming.session import SERVER_SIDE_TOOLS
        expected = {"describe_screen", "wait_for_content", "save_snapshot",
                    "diff_screen", "teach_me_app", "read_selection", "read_page_structure"}
        assert expected == SERVER_SIDE_TOOLS


# ─── Orchestrator tool declarations ────────────────────────────────────────

class TestOrchestratorToolDeclarations:
    """Tests that the orchestrator exposes wait_for_content to Gemini."""

    def test_wait_for_content_declared(self):
        from app.agents.orchestrator import SPECTRA_TOOLS
        tool_names = [
            fd.name for tool in SPECTRA_TOOLS for fd in tool.function_declarations
        ]
        assert "wait_for_content" in tool_names

    def test_wait_for_content_has_reason_param(self):
        from app.agents.orchestrator import SPECTRA_TOOLS
        for tool in SPECTRA_TOOLS:
            for fd in tool.function_declarations:
                if fd.name == "wait_for_content":
                    prop_names = list(fd.parameters.properties.keys())
                    assert "reason" in prop_names
                    assert "wait_ms" in prop_names
                    return
        pytest.fail("wait_for_content not found")

    def test_wait_for_content_reason_required(self):
        from app.agents.orchestrator import SPECTRA_TOOLS
        for tool in SPECTRA_TOOLS:
            for fd in tool.function_declarations:
                if fd.name == "wait_for_content":
                    assert "reason" in fd.parameters.required
                    return
        pytest.fail("wait_for_content not found")

    def test_describe_screen_still_declared(self):
        from app.agents.orchestrator import SPECTRA_TOOLS
        tool_names = [
            fd.name for tool in SPECTRA_TOOLS for fd in tool.function_declarations
        ]
        assert "describe_screen" in tool_names


# ─── System instruction validation ─────────────────────────────────────────

class TestSystemInstructionUpdates:
    """Validate system instruction includes flight booking and wait_for_content guidance."""

    def test_wait_for_content_in_tools_reference(self):
        from app.agents.system_instruction import TOOLS_REFERENCE
        assert "wait_for_content" in TOOLS_REFERENCE

    def test_autocomplete_uses_wait_for_content(self):
        from app.agents.system_instruction import WORKFLOW
        lower = WORKFLOW.lower()
        assert "wait_for_content" in lower
        assert "autocomplete" in lower

    def test_travel_booking_section_exists(self):
        from app.agents.system_instruction import WORKFLOW
        assert "TRAVEL BOOKING" in WORKFLOW

    def test_travel_booking_warns_against_read_page_structure_on_spa(self):
        from app.agents.system_instruction import WORKFLOW
        assert "NEVER use read_page_structure on Google Flights" in WORKFLOW

    def test_travel_booking_step_by_step_pattern(self):
        from app.agents.system_instruction import WORKFLOW
        lower = WORKFLOW.lower()
        assert "step-by-step pattern" in lower
        assert "combobox" in lower
        assert "date" in lower.lower()

    def test_flight_booking_example_exists(self):
        from app.agents.system_instruction import EXAMPLES
        assert "flight_booking" in EXAMPLES
        assert "wait_for_content" in EXAMPLES["flight_booking"]
        assert "Dublin" in EXAMPLES["flight_booking"]

    def test_error_handling_mentions_stale_frame(self):
        from app.agents.system_instruction import ERROR_HANDLING
        assert "video feed paused" in ERROR_HANDLING
        assert "Frame is" in ERROR_HANDLING

    def test_screen_sharing_never_ask_again_rule(self):
        from app.agents.system_instruction import SCREEN_SHARING_RULES
        assert "NEVER ask the user to share their screen again" in SCREEN_SHARING_RULES

    def test_full_instruction_includes_wait_for_content(self):
        from app.agents.system_instruction import SPECTRA_SYSTEM_INSTRUCTION
        assert "wait_for_content" in SPECTRA_SYSTEM_INSTRUCTION

    def test_full_instruction_includes_travel_booking(self):
        from app.agents.system_instruction import SPECTRA_SYSTEM_INSTRUCTION
        assert "TRAVEL BOOKING" in SPECTRA_SYSTEM_INSTRUCTION
