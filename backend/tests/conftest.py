"""Pytest configuration and shared fixtures."""

import sys
import logging
from pathlib import Path

# Add backend directory to Python path so 'app' module can be imported
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from unittest.mock import patch, MagicMock

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def use_live_api():
    """Check if we should use live API (set USE_LIVE_API=1 for production tests)."""
    import os
    return os.getenv("USE_LIVE_API", "").lower() == "1"


@pytest.fixture(autouse=True)
def mock_gemini_for_all_tests(use_live_api):
    """Mock Gemini client for dev/CI tests. Use real API when USE_LIVE_API=1 (production)."""
    if use_live_api:
        # Production: use real API with actual credentials
        logger.info("✓ Using LIVE Gemini API (production mode)")
        yield None  # No mocking
        return

    # Dev/CI: use mocks
    with patch('google.genai.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance

        # Mock the live connection
        mock_session = MagicMock()

        # Configure mock to return proper non-coroutine values for text attributes
        mock_transcription = MagicMock()
        mock_transcription.text = ""  # Return empty string, not a coroutine

        mock_server_content = MagicMock()
        mock_server_content.input_transcription = mock_transcription

        # Mock async iterator for session.receive()
        async def mock_receive():
            """Return a mock response that won't cause attribute errors."""
            mock_response = MagicMock()
            mock_response.server_content = None  # No server content by default
            return mock_response

        mock_session.receive = mock_receive
        mock_session.send_realtime_input = MagicMock()

        mock_instance.aio.live.connect.return_value.__aenter__.return_value = mock_session
        mock_instance.aio.live.connect.return_value.__aexit__.return_value = None

        yield mock_instance


@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing."""
    class MockWebSocket:
        def __init__(self):
            self.messages = []
            self.is_connected = True

        async def send_json(self, data):
            self.messages.append(data)

        async def close(self, code=None, reason=None):
            self.is_connected = False

    return MockWebSocket()
