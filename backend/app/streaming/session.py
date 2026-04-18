"""Spectra streaming session — bridges the client WebSocket to the Gemini Live API."""

import asyncio
import base64
import hashlib
import json
import logging
import os
import re
import time
import uuid
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from google import genai
from google.genai import types

from app.agents.orchestrator import (
    SPECTRA_TOOLS,
    SpectraState,
    log_interaction,
    postprocess_spectra_reply,
    validate_system_instruction_response,
    remove_narration,
)
from app.tools.diff import diff_screen, save_snapshot, teach_me_app
from app.location_context_handler import LocationContextHandler
from app.voice_command_processor import VoiceCommandProcessor, CommandContext
from app.performance_monitor import get_performance_monitor
from app.memory import SpectraMemory
from app.streaming.session_manager import get_session_manager, SessionState

logger = logging.getLogger(__name__)

# Model name differs between Vertex AI and the direct Gemini API.
# Vertex AI uses the "gemini-live-*" naming scheme; direct API uses "models/*".
# NOTE: evaluated lazily in SpectraStreamingSession.__init__ so load_dotenv()
# has already run by the time we read GOOGLE_CLOUD_PROJECT.
_VERTEX_MODEL = "gemini-live-2.5-flash-native-audio"
_DIRECT_MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

def _get_live_model() -> str:
    return _VERTEX_MODEL if os.getenv("GOOGLE_CLOUD_PROJECT") else _DIRECT_MODEL

# Keep a module-level alias for logging — resolved at first use
_USE_VERTEX = None  # set lazily
LIVE_MODEL = None   # set lazily

SERVER_SIDE_TOOLS = {"describe_screen", "wait_for_content", "save_snapshot", "diff_screen", "teach_me_app", "read_selection", "read_page_structure"}
# Performance tuning - Configurable via environment variables
MAX_FRAME_QUEUE = int(os.getenv("MAX_FRAME_QUEUE", "3"))
ACTION_TIMEOUT = float(os.getenv("ACTION_TIMEOUT", "12.0"))  # 12s — navigate waits for page load (up to 8s)
HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", "3.0"))
FRAME_COOLDOWN = float(os.getenv("FRAME_COOLDOWN", "1.0"))  # 1s — Live API max 1 FPS for images
DESCRIBE_CACHE_TTL = float(os.getenv("DESCRIBE_CACHE_TTL", "3.0"))
MAX_CONCURRENT_ACTIONS = int(os.getenv("MAX_CONCURRENT_ACTIONS", "2"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "1"))

# Vision stability tuning
DESCRIBE_COOLDOWN = float(os.getenv("DESCRIBE_COOLDOWN", "0.3"))

# Intelligent caching configuration (Task 5.3)
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", "20"))
CACHE_MIN_TTL = float(os.getenv("CACHE_MIN_TTL", "2.0"))
CACHE_MAX_TTL = float(os.getenv("CACHE_MAX_TTL", "10.0"))
CACHE_ADAPTIVE_THRESHOLD = float(os.getenv("CACHE_ADAPTIVE_THRESHOLD", "0.7"))
FRAME_SIMILARITY_THRESHOLD = float(os.getenv("FRAME_SIMILARITY_THRESHOLD", "0.95"))


def _translate_action_result(action: str, result: str) -> str:
    """Translate raw action result codes into plain English for the Gemini model.

    Raw codes such as "clicked_by_label_button_Sign in" would be read aloud verbatim.
    This function converts them to natural language so the model can respond naturally
    without reciting internal status codes.
    """
    if not isinstance(result, str):
        return str(result)

    r = result.strip()
    rl = r.lower()

    # Failures — pass through as-is so Gemini knows what went wrong
    if any(rl.startswith(p) for p in ("error", "fail", "timeout", "no_element", "no_target", "extension", "blocked", "invalid", "navigate_failed", "click_failed", "type_failed", "key_failed", "scroll_failed")):
        return r

    # Navigate
    if rl.startswith("navigated_to_"):
        url = r[len("navigated_to_"):]
        # Sanitize URL: strip newlines/control chars to prevent prompt injection
        url = url.replace("\n", " ").replace("\r", " ").strip()[:200]
        return f"Navigation succeeded. Now on: {url}"

    # Click — link (triggers page load)
    if rl.startswith("clicked_link_navigate_expected:"):
        dest = r.split(":", 1)[1].strip() if ":" in r else ""
        return f"Link clicked — page loading. Destination: {dest or 'unknown'}"

    # Click — regular element
    if rl.startswith("clicked_"):
        # Preserve what was clicked so Gemini knows the action succeeded
        # Raw format: "clicked_TAG_LABEL" or "clicked_by_label_TAG_LABEL"
        suffix = r[len("clicked_"):]
        # Strip "by_label_" prefix if present
        if suffix.lower().startswith("by_label_"):
            suffix = suffix[len("by_label_"):]
        # Split tag from label: "a_Communication" → tag=a, label=Communication
        parts = suffix.split("_", 1)
        label = parts[1] if len(parts) > 1 else parts[0]
        label = label.replace("_", " ").strip()
        if label:
            return f"Successfully clicked '{label}'."
        return "Clicked."

    # Type
    if rl.startswith("typed_into_"):
        field = r[len("typed_into_"):].replace("_", " ")
        return f"Typed into {field}."

    # Scroll
    if "reached_bottom" in rl:
        return "Scrolled down — reached the bottom of the page."
    if "reached_top" in rl:
        return "Scrolled up — reached the top of the page."
    if rl.startswith("scrolled_"):
        return f"Scrolled. {r.replace('_', ' ').capitalize()}."

    # Key press
    if rl.startswith("pressed_"):
        key = r[len("pressed_"):].replace("_", "+")
        return f"Key pressed: {key}."

    # Highlight
    if rl.startswith("highlighted_"):
        suffix = r[len("highlighted_"):]
        parts = suffix.split("_", 1)
        label = parts[1] if len(parts) > 1 else parts[0]
        label = label.replace("_", " ").strip()
        return f"Highlighted '{label}'." if label else "Element highlighted."

    # Reading / selection
    if rl.startswith("reading_") or rl.startswith("read_"):
        return r  # pass through — this is actual content

    # Fallback: pass through unchanged
    return r


class SpectraStreamingSession:
    """Manage a single user session, bridging the client WebSocket to the Gemini Live API."""

    def __init__(self, websocket: WebSocket, user_id: str = "default", session_id: str = None):
        self.websocket = websocket
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        _gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        _gcp_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        # Resolve model name now that load_dotenv() has run.
        # Store as instance variables so run() doesn't depend on module-level globals.
        self._use_vertex: bool = bool(_gcp_project)
        self._live_model: str = _VERTEX_MODEL if self._use_vertex else _DIRECT_MODEL
        # Also update module-level globals for backward compat (logging etc.)
        global _USE_VERTEX, LIVE_MODEL
        _USE_VERTEX = self._use_vertex
        LIVE_MODEL = self._live_model
        logger.info(f"Using model: {self._live_model} (Vertex={self._use_vertex})")
        if _gcp_project:
            self.client = genai.Client(vertexai=True, project=_gcp_project, location=_gcp_location)
        else:
            self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.gemini_session = None
        self._running = False
        # Match action results by id so a timeout doesn't hand the next action the previous result
        self._action_pending: dict[str, asyncio.Future] = {}
        self._latest_frame: str | None = None
        self._latest_dom: dict = {}
        self._current_url: str = ""
        self._last_frame_time: float = 0
        self._frame_cooldown: float = FRAME_COOLDOWN
        self._frame_hash: str | None = None
        self._capture_width: int = 0
        self._capture_height: int = 0
        self._describe_cache: dict[str, tuple[str, float]] = {}
        self._pending_actions: dict[str, float] = {}
        self._message_count = 0
        self._session_start = 0.0
        self._heartbeat_task: asyncio.Task | None = None
        self._frame_buffer: deque = deque(maxlen=BATCH_SIZE)
        self._last_action_time: float = 0
        self._action_cooldown: float = 0.01  # Reduced from 0.02s to 0.01s
        self._tool_response_lock = asyncio.Lock()
        self._describe_cache_lock = asyncio.Lock()
        self._last_input_time: float = 0

        # Audio gating: buffer audio briefly at the start of each model turn.
        # If a tool_call arrives within the gate window, the buffered audio is
        # discarded (it was premature narration like "done!" spoken before the
        # action actually executed). If no tool_call arrives, the buffer is
        # flushed and subsequent audio flows directly.
        self._audio_buffer: list[dict] = []
        self._audio_gate_open: bool = False
        self._audio_flush_task: asyncio.Task | None = None
        self._last_activity: float = time.time()
        self._last_describe_time: float = 0
        self._describe_cooldown: float = 0.5  # Reduced from 0s to 0.5s
        
        # Fast pipeline integration for 10X performance
        from app.streaming.fast_pipeline import get_fast_pipeline
        self.fast_pipeline = get_fast_pipeline()
        logger.info(f"[FastPipeline] Initialized for session {self.session_id}")
        
        # Get persistent session state from session manager
        self.session_manager = get_session_manager()
        # Key by user_id, not session_id — session_id changes on every page reload,
        # but we need screen-share state to persist across reconnects.
        self.session_state: SessionState = self.session_manager.get_or_create_session(
            self.user_id, self.user_id
        )
        
        # Persistent session state - CRITICAL for avoiding reconnections
        self.screen_stream_active: bool = False  # Track if screen sharing is active
        self.connection_state: str = "open"  # "open" | "degraded" | "closed"
        self.last_frame_ts: float = 0.0  # Timestamp of last frame received
        self.last_describe_screen_ok: bool = False  # Track if last describe_screen succeeded
        # Bug fix: use getattr with default — AttributeError if SessionState is
        # missing last_frame_ts (corrupted state, schema change) would crash __init__.
        self._screen_ever_shared: bool = getattr(self.session_state, 'last_frame_ts', 0) > 0  # Restored from persistent state on reconnect
        
        # Memory system for persistent learning
        self.memory = SpectraMemory(user_id)
        
        # Location context handler for accessibility queries
        self.location_handler = LocationContextHandler()
        
        # Voice command processor for natural language commands
        self.voice_processor = VoiceCommandProcessor()
        
        # Performance monitor for tracking vision system performance
        self.performance_monitor = get_performance_monitor()
        
        # Repeat functionality - store last response for "repeat that" command
        self._last_response_text: str = ""
        self._last_response_audio: bytes | None = None
        self._last_response_time: float = 0.0
        
        # Proactive assistance - detect when user needs help
        self._last_user_input_time: float = time.time()
        self._proactive_help_offered: bool = False

        # Flight booking price memory - track prices across sites for comparison
        self._flight_prices: list[dict] = []  # [{"site": "Google Flights", "airline": "Ryanair", "price": 79, "currency": "EUR", "route": "DUB-LHR", "time": "6am", "timestamp": ...}]
        self._current_search_route: str = ""  # e.g., "Dublin to London"
        self._stuck_threshold: float = 30.0  # Offer help after 30s of inactivity
        
        # Interruption handling - allow user to interrupt Spectra
        self._currently_speaking: bool = False
        self._speech_start_time: float = 0.0
        
        # First-time user onboarding
        self._is_first_time_user: bool = not self._screen_ever_shared
        self._onboarding_completed: bool = False
        self._onboarding_message_sent: bool = False
        
        # Repeat functionality - store last response for "repeat that" command
        self._last_response_text: str = ""
        self._last_response_audio: bytes | None = None
        self._last_response_time: float = 0.0
        
        # State machine for context tracking and optimization
        self.state = SpectraState()
        
        # Intelligent caching state (Task 5.3)
        self._cache_ttl = DESCRIBE_CACHE_TTL  # Adaptive TTL
        self._frame_history: deque = deque(maxlen=10)  # Track recent frame hashes
        self._cache_access_times: dict[str, float] = {}  # Track when cache entries were last accessed
        self._cache_hit_streak = 0  # Track consecutive cache hits for TTL adjustment
        
        # Text buffering for narration filtering
        self._text_buffer = []

        # Track whether audio was sent in the current turn.
        # If audio was sent, suppress text-to-chat (avoids language mismatch where
        # model generates Arabic text but English audio from the same turn).
        self._audio_sent_this_turn: bool = False

        # Set True when the browser WebSocket disconnects so the Gemini reconnect
        # loop knows to stop rather than reconnect again.
        self._client_disconnected: bool = False
        
        # Extension availability — set by extension_status message from frontend
        self._extension_available: bool = False
        
        # Frame similarity detection for response time optimization (Task 8.4)
        self._previous_frame_hash: str | None = None
        self._frame_similarity_scores: deque = deque(maxlen=20)  # Track similarity history

    def _calculate_frame_similarity(self, current_hash: str, previous_hash: str) -> float:
        """
        Calculate a similarity score between two frame hashes.

        Uses hash comparison as a lightweight proxy for visual similarity.
        Returns a value between 0.0 (completely different) and 1.0 (identical).

        Args:
            current_hash: Hash of the current frame
            previous_hash: Hash of the previous frame

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not current_hash or not previous_hash:
            return 0.0
        
        if current_hash == previous_hash:
            return 1.0
        
        # Calculate Hamming distance between hashes
        # For more sophisticated comparison, could use perceptual hashing
        try:
            # Convert hex hashes to binary and compare
            current_bin = bin(int(current_hash, 16))[2:].zfill(256)
            previous_bin = bin(int(previous_hash, 16))[2:].zfill(256)
            
            # Count matching bits
            matches = sum(c == p for c, p in zip(current_bin, previous_bin))
            similarity = matches / len(current_bin)
            
            return similarity
        except (ValueError, TypeError):
            # If hash comparison fails, assume frames are different
            return 0.0
    
    def _should_use_cached_description(self, current_hash: str) -> bool:
        """
        Determine if cached description should be used based on frame similarity.
        
        Args:
            current_hash: Hash of current frame
            
        Returns:
            True if cached description should be used, False if fresh analysis needed
        """
        if not self._previous_frame_hash or not current_hash:
            return False
        
        # Calculate similarity with previous frame
        similarity = self._calculate_frame_similarity(current_hash, self._previous_frame_hash)
        self._frame_similarity_scores.append(similarity)
        
        # Use cached description if frames are very similar
        if similarity >= FRAME_SIMILARITY_THRESHOLD:
            logger.info(f"Frame similarity {similarity:.2%} >= threshold {FRAME_SIMILARITY_THRESHOLD:.2%}, using cached description")
            return True
        
        logger.debug(f"Frame similarity {similarity:.2%} < threshold {FRAME_SIMILARITY_THRESHOLD:.2%}, performing fresh analysis")
        return False
    
    def _update_frame_tracking(self, frame_hash: str):
        """Update frame tracking for similarity detection."""
        self._previous_frame_hash = frame_hash
        self._frame_history.append(frame_hash)

    async def run(self):
        self._session_start = time.time()
        
        # Inject memory context into system instruction
        memory_context = self.memory.get_context_for_system_instruction()
        from app.agents.orchestrator import SPECTRA_SYSTEM_INSTRUCTION
        core_instruction = SPECTRA_SYSTEM_INSTRUCTION
        enhanced_instruction = core_instruction + memory_context
        
        # Full Spectra configuration with proper system instruction
        # Note: max_output_tokens and temperature are not valid LiveConnectConfig params.
        # thinking_config is only supported on the direct Gemini API, not Vertex AI Live.
        config_kwargs = dict(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=enhanced_instruction)]
            ),
            tools=SPECTRA_TOOLS,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=os.getenv("SPECTRA_VOICE", "Aoede")
                    )
                )
            ),
            # Transcribe what the user says so the frontend can show it
            input_audio_transcription=types.AudioTranscriptionConfig(),
            # Enable output audio transcription for debugging
            output_audio_transcription=types.AudioTranscriptionConfig(),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefix_padding_ms=300,
                )
            ),
        )
        # thinking_config is only available on the direct Gemini API (not Vertex AI Live)
        if not self._use_vertex:
            config_kwargs["thinking_config"] = types.ThinkingConfig(include_thoughts=False)
        config = types.LiveConnectConfig(**config_kwargs)

        # client_task and heartbeat_task span the full WebSocket lifetime —
        # they survive Gemini reconnects so the browser connection stays alive.
        client_task = asyncio.create_task(self._listen_client())
        heartbeat_task = asyncio.create_task(self._send_heartbeats())
        keepalive_task = asyncio.create_task(self._gemini_keepalive())

        try:
            # ── Gemini reconnect loop ────────────────────────────────────────
            # When Gemini sends go_away (15-min limit) or any session error,
            # we transparently reconnect to Gemini without closing the browser
            # WebSocket. The user keeps their session; only the Gemini
            # connection is cycled.
            _reconnect_delay = 1.0   # seconds, doubles on each failure
            _go_away_wait = 0.0      # seconds to wait from go_away time_left
            _is_first_connect = True
            while not self._client_disconnected:
                if _go_away_wait > 0:
                    logger.info(f"Honouring go_away — waiting {_go_away_wait:.0f}s before reconnecting")
                    await asyncio.sleep(_go_away_wait)
                    _go_away_wait = 0.0
                try:
                    async with self.client.aio.live.connect(
                        model=self._live_model, config=config
                    ) as session:
                        self.gemini_session = session
                        self._running = True
                        _session_start_time = time.time()
                        # Reset per-turn state that may be stale from the dead session.
                        self._text_buffer = []
                        self._audio_sent_this_turn = False
                        logger.info(f"Gemini Live session (re)connected using model: {self._live_model}")
                        first_connect = _is_first_connect
                        if not _is_first_connect:
                            # On reconnect: suppress the greeting loop by sending the
                            # "stay silent" instruction BEFORE the silence burst.
                            # Order matters — the silence burst triggers Gemini's VAD.
                            # If the instruction arrives after the burst, Gemini has
                            # already started generating the "Press W" greeting.
                            # Sending text first gives Gemini the context it needs
                            # before VAD fires. We also skip the silence burst entirely
                            # since the text input already keeps the session alive.
                            try:
                                await session.send_realtime_input(
                                    text="[Session reconnected. The user is already present. Stay silent — do NOT greet or ask for screen share. Wait for the user to speak first.]"
                                )
                                self._last_input_time = time.time()
                            except Exception:
                                pass
                        else:
                            # First connect: send minimal silence to prime VAD
                            # Very small to prevent "yes ready" spam but keep connection alive
                            try:
                                await session.send_realtime_input(
                                    audio=types.Blob(data=b'\x00' * 200, mime_type="audio/pcm;rate=16000")
                                )
                                self._last_input_time = time.time()
                            except Exception as prime_err:
                                logger.debug(f"Session prime skipped: {prime_err}")
                        _is_first_connect = False

                        # Re-inject context so Gemini knows where it is after reconnect.
                        # Without this, Gemini starts completely blank: no page, no screen.
                        try:
                            ctx_parts = []
                            
                            # First connect: single greeting only (avoid duplicate intro)
                            if first_connect:
                                if not self._screen_ever_shared:
                                    ctx_parts.append(
                                        "[The user has just connected. Say exactly ONCE: "
                                        "'Hello, I'm Spectra — your hands-free browser assistant. Press W to share your screen so I can see it and help you.' "
                                        "Do NOT repeat hello or add a second greeting. One short intro only.]"
                                    )
                                else:
                                    ctx_parts.append(
                                        "[The user has just connected. Say exactly ONCE: "
                                        "'Hello, I'm Spectra. I'm ready — what would you like to do?' "
                                        "Do NOT repeat or add another greeting.]"
                                    )
                            else:
                                # Reconnect: context only, no greeting
                                if not self._screen_ever_shared:
                                    ctx_parts.append(
                                        "[USER NEEDS ONBOARDING: User hasn't shared screen yet. "
                                        "If they ask anything, warmly explain how to press W to share screen.]"
                                    )
                                else:
                                    ctx_parts.append("[Screen sharing is active. User can see and interact normally.]")
                            
                            # Inject extension status so Gemini knows upfront whether actions work
                            if self._extension_available:
                                ctx_parts.append("[Browser extension: INSTALLED. All browser actions work.]")
                            else:
                                ctx_parts.append(
                                    "[IMPORTANT: Browser extension NOT installed. "
                                    "Do NOT attempt click_element, type_text, scroll_page, press_key, or navigate — they will fail. "
                                    "If asked to interact with the browser, tell the user to install the Spectra extension first.]"
                                )

                            if self._current_url:
                                ctx_parts.append(f"[Current page: {self._current_url}]")
                                
                            if ctx_parts:
                                await session.send_realtime_input(text=" ".join(ctx_parts))
                                
                            # Send latest frame if available
                            if self._latest_frame:
                                frame_bytes = base64.b64decode(self._latest_frame)
                                await session.send_realtime_input(
                                    video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
                                )
                                self._last_frame_time = time.time()  # reset cooldown after reconnect injection
                        except Exception as ctx_err:
                            logger.debug(f"Context re-injection skipped: {ctx_err}")

                        try:
                            # Use __anext__() directly instead of `async for` so the
                            # loop persists across turn_complete boundaries.
                            # `async for session.receive()` exits after turn_complete
                            # because the SDK generator raises StopAsyncIteration —
                            # that kills the session after every single response.
                            _receiver = session.receive()
                            while not self._client_disconnected:
                                try:
                                    response = await _receiver.__anext__()
                                except StopAsyncIteration:
                                    # turn_complete caused the generator to end —
                                    # re-create it so we keep receiving on the same session
                                    _receiver = session.receive()
                                    continue

                                if response.server_content:
                                    sc = response.server_content

                                    # User speech transcription — filter noise before sending
                                    if sc.input_transcription and sc.input_transcription.text:
                                        raw_t = sc.input_transcription.text.strip()
                                        is_noise = (
                                            not raw_t
                                            or raw_t.startswith("<noise>")
                                            or raw_t.startswith("[noise]")
                                            or len(raw_t) <= 1
                                        )
                                        if not is_noise:
                                            await self.websocket.send_json({
                                                "type": "transcript",
                                                "data": raw_t,
                                            })

                                    if sc.model_turn:
                                        for part in sc.model_turn.parts:
                                            if part.inline_data:
                                                self._audio_sent_this_turn = True
                                                chunk = {
                                                    "type": "audio",
                                                    "data": base64.b64encode(part.inline_data.data).decode(),
                                                    "mime_type": part.inline_data.mime_type,
                                                }
                                                if self._audio_gate_open:
                                                    await self.websocket.send_json(chunk)
                                                else:
                                                    self._audio_buffer.append(chunk)
                                                    if self._audio_flush_task is None or self._audio_flush_task.done():
                                                        self._audio_flush_task = asyncio.create_task(self._flush_audio_gate())
                                            if part.text:
                                                if len(part.text) > 20:
                                                    logger.debug(f"Text part (len={len(part.text)}): {part.text[:80]}")
                                                self._text_buffer.append(part.text)
                                                # Send text parts as transcripts in real-time so UI shows response immediately
                                                await self.websocket.send_json({
                                                    "type": "transcript",
                                                    "data": part.text,
                                                })

                                    if sc.turn_complete:
                                        # Flush any audio still in the gate buffer
                                        if self._audio_flush_task and not self._audio_flush_task.done():
                                            self._audio_flush_task.cancel()
                                        for msg in self._audio_buffer:
                                            await self.websocket.send_json(msg)
                                        self._audio_buffer.clear()
                                        self._audio_gate_open = False

                                        if self._text_buffer:
                                            full_text = "".join(self._text_buffer)
                                            self._text_buffer = []
                                            if not self._audio_sent_this_turn:
                                                cleaned = postprocess_spectra_reply(full_text)
                                                is_valid, violations = validate_system_instruction_response(cleaned)
                                                if not is_valid:
                                                    logger.warning(f"Spectra violation: {violations}")
                                                if cleaned:
                                                    await self.websocket.send_json({
                                                        "type": "text",
                                                        "data": cleaned,
                                                    })
                                        self._audio_sent_this_turn = False
                                        await self.websocket.send_json({"type": "turn_complete"})

                                if response.tool_call:
                                    # Discard pre-tool-call audio (premature "done!" narration).
                                    if self._audio_flush_task and not self._audio_flush_task.done():
                                        self._audio_flush_task.cancel()
                                    discarded = len(self._audio_buffer)
                                    self._audio_buffer.clear()
                                    self._audio_gate_open = True  # post-tool audio flows directly
                                    if discarded > 0:
                                        logger.info(f"🔇 Discarded {discarded} premature audio chunks before tool call")
                                    await self._handle_tool_calls(response.tool_call)

                                # go_away: server asking us to reconnect after time_left
                                go_away = getattr(response, "go_away", None)
                                if go_away:
                                    time_left = getattr(go_away, "time_left", None)
                                    wait_secs = max(float(str(time_left).rstrip("s") or 5), 2) if time_left else 5
                                    logger.warning(f"go_away received (time_left={time_left}) — will wait {wait_secs:.0f}s")
                                    _go_away_wait = wait_secs
                                    break

                            _reconnect_delay = 1.0  # clean exit = reset backoff

                        except Exception as e:
                            if self._client_disconnected:
                                break
                            logger.error(f"Gemini receive error: {type(e).__name__}: {e}", exc_info=True)
                            _reconnect_delay = min(_reconnect_delay * 2, 30)
                            # Close provider on error only
                            self._running = False
                            self.gemini_session = None

                except Exception as e:
                    if self._client_disconnected:
                        break
                    logger.error(f"Gemini connection error: {e}", exc_info=True)
                    self._running = False
                    self.gemini_session = None
                    
                    # Check if this is a model availability error
                    error_str = str(e).lower()
                    if "not found" in error_str or "not supported for bidigeneratecontent" in error_str:
                        # Send helpful error message to user
                        try:
                            await self.websocket.send_json({
                                "type": "text",
                                "data": f"⚠️ Gemini Live API Error: The model '{self._live_model}' is not available for voice chat. This is a known limitation of the Gemini Live API. Please try again later or check Google's documentation for available models."
                            })
                        except Exception:
                            pass
                        
                        # Don't retry as aggressively for model availability errors
                        _reconnect_delay = min(_reconnect_delay * 1.5, 60)
                    else:
                        _reconnect_delay = min(_reconnect_delay * 2, 30)

                # ── Decide whether to reconnect ──────────────────────────────
                if self._client_disconnected:
                    break

                delay = _go_away_wait if _go_away_wait > 0 else _reconnect_delay
                _go_away_wait = 0.0
                logger.info(f"Gemini session ended — reconnecting in {delay:.0f}s...")
                try:
                    await self.websocket.send_json({"type": "gemini_reconnecting"})
                except Exception:
                    self._client_disconnected = True
                    break
                await asyncio.sleep(delay)

        finally:
            self._running = False
            self.gemini_session = None
            client_task.cancel()
            heartbeat_task.cancel()
            keepalive_task.cancel()
            try:
                await client_task
            except Exception:
                pass
            try:
                await heartbeat_task
            except Exception:
                pass
            try:
                await keepalive_task
            except Exception:
                pass

    async def cleanup(self):
        """Enhanced cleanup with preference and memory persistence."""
        self._running = False
        self._client_disconnected = True

        # Close the Gemini session first so the receive loop terminates
        if self.gemini_session:
            try:
                await self.gemini_session.close()
            except Exception:
                pass
            self.gemini_session = None

        # Close the browser WebSocket so _listen_client() exits and the
        # run() reconnect loop stops.  Without this, the old session's
        # run() keeps reconnecting to Gemini after being replaced.
        try:
            await self.websocket.close(code=1000, reason="replaced by new session")
        except Exception:
            pass
        
        # Mark session as closed in session manager (but don't remove it)
        # This allows reconnection without losing state
        self.session_state.connection_state = "closed"
        
        # Clean up caches to prevent memory leaks
        self._describe_cache.clear()
        self._cache_access_times.clear()
        self._pending_actions.clear()
        
        # Save memory
        try:
            self.memory.save()
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")
        
        logger.debug("Session cleanup completed for user %s", self.user_id)

    async def _flush_audio_gate(self):
        """Flush the audio buffer after a brief hold-off.

        Called as an asyncio task. If a tool_call arrives before this fires,
        the task is cancelled and the buffer is discarded instead.
        """
        try:
            await asyncio.sleep(0.20)
            buf = list(self._audio_buffer)
            self._audio_buffer.clear()
            self._audio_gate_open = True
            for msg in buf:
                if not self._client_disconnected:
                    await self.websocket.send_json(msg)
        except asyncio.CancelledError:
            pass

    async def _gemini_keepalive(self):
        """Send tiny silence bursts periodically to keep the Gemini Live session alive.

        The Vertex AI Live API closes the stream if no input arrives for several
        seconds.  We only send silence when there's been no real input recently,
        to avoid interfering with VAD during active conversation.
        """
        _SILENCE = b'\x00' * 100  # 6.25ms @ 16kHz — below VAD threshold
        while not self._client_disconnected:
            try:
                await asyncio.sleep(2.0)
                if self.gemini_session and self._running:
                    time_since_input = time.time() - self._last_input_time
                    if time_since_input >= 1.5:
                        await self.gemini_session.send_realtime_input(
                            audio=types.Blob(data=_SILENCE, mime_type="audio/pcm;rate=16000")
                        )
            except asyncio.CancelledError:
                break
            except Exception:
                pass  # Session may be reconnecting — silently skip

    async def _send_heartbeats(self):
        """Heartbeat loop — runs for the full WebSocket lifetime across Gemini reconnects."""
        consecutive_failures = 0

        while not self._client_disconnected:
            try:
                time_since_activity = time.time() - self._last_activity
                interval = HEARTBEAT_INTERVAL if time_since_activity < 30 else HEARTBEAT_INTERVAL * 2
                await asyncio.sleep(interval)

                if self._client_disconnected:
                    break

                try:
                    await self.websocket.send_json({
                        "type": "heartbeat",
                        "uptime": round(time.time() - self._session_start),
                        "performance": {
                            "message_count": self._message_count,
                            "cache_size": len(self._describe_cache),
                            "cache_ttl": round(self._cache_ttl, 1),
                            "cache_hit_rate": round(self.performance_monitor.get_cache_hit_rate(), 1),
                        },
                    })
                    consecutive_failures = 0
                except WebSocketDisconnect:
                    logger.info("Client disconnected during heartbeat")
                    self._client_disconnected = True
                    break
                except Exception as ws_err:
                    consecutive_failures += 1
                    logger.warning(f"Heartbeat failed ({consecutive_failures}): {ws_err}")
                    if consecutive_failures >= 3:
                        logger.error("Too many heartbeat failures, stopping")
                        self._client_disconnected = True
                        break

                # Gemini keep-alive is handled by _gemini_keepalive() task (runs every 0.5s)
                    
                    # First-time user onboarding - DISABLED to prevent continuous talking
                    # Users will get onboarding help when they actually ask for it
                    # if (self._is_first_time_user and 
                    #     not self._screen_ever_shared and 
                    #     not self._onboarding_message_sent and
                    #     time_since_input > 5.0):
                    #     try:
                    #         logger.info("Triggering first-time user onboarding")
                    #         await self.gemini_session.send_realtime_input(
                    #             text="[The user has been connected for 5 seconds but hasn't shared their screen yet. Proactively greet them with the friendly onboarding message now.]"
                    #         )
                    #         self._onboarding_message_sent = True
                    #     except Exception as onboard_err:
                    #         logger.debug(f"Onboarding trigger skipped: {onboard_err}")


            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                consecutive_failures += 1
                if consecutive_failures >= 5:
                    self._client_disconnected = True
                    break

    async def _listen_client(self):
        """Read messages from the browser WebSocket and forward to Gemini.

        Runs for the full WebSocket lifetime. During a Gemini reconnect window
        (self.gemini_session is None), time-insensitive messages are dropped
        gracefully rather than erroring.
        """
        try:
            while not self._client_disconnected:
                raw = await self.websocket.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "audio":
                    if self.gemini_session and self._running:
                        try:
                            audio_data = base64.b64decode(msg["data"])
                            if len(audio_data) >= 2 and len(audio_data) % 2 == 0:
                                await self.gemini_session.send_realtime_input(
                                    audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                                )
                                self._last_input_time = time.time()
                                self._last_activity = time.time()
                            else:
                                logger.debug("Skipping invalid audio chunk: len=%d (expected even, >=2)", len(audio_data))
                        except Exception as e:
                            # Provider disconnected (e.g., Gemini connection closed). Log once and move on.
                            logger.debug("Audio send failed (provider may have disconnected): %s", type(e).__name__)

                elif msg_type == "screenshot":
                    frame_data = msg["data"]
                    frame_bytes = base64.b64decode(frame_data)
                    now = time.time()
                    # Detect screen share change: long gap = user stopped then restarted (or switched source)
                    frame_gap = now - self.last_frame_ts if self.last_frame_ts else 0
                    if frame_gap > 5.0 and self._screen_ever_shared:
                        async with self._describe_cache_lock:
                            self._describe_cache.clear()
                        self._cache_access_times.clear()
                        if self.gemini_session and self._running:
                            try:
                                await self.gemini_session.send_realtime_input(
                                    text="[Screen source changed. Describe what you see now.]"
                                )
                            except Exception:
                                pass
                    self._latest_frame = frame_data
                    self._capture_width = msg.get("width", 0)
                    self._capture_height = msg.get("height", 0)
                    self._frame_hash = hashlib.md5(frame_bytes).hexdigest()[:8]

                    # Track screen sharing state
                    was_first_time = self._is_first_time_user and not self._screen_ever_shared

                    self.screen_stream_active = True
                    self.last_frame_ts = now
                    self.connection_state = "open"
                    self._screen_ever_shared = True
                    self.session_state.mark_frame_received()  # persist across reconnects

                    if hasattr(self, '_screen_share_requested'):
                        delattr(self, '_screen_share_requested')

                    if not hasattr(self, '_first_frame_logged'):
                        logger.debug(f"First frame: {self._capture_width}x{self._capture_height}")
                        self._first_frame_logged = True
                    
                    # First-time user just shared screen - DISABLED to prevent continuous talking
                    # Users will get help when they actually ask for it
                    # if was_first_time and self.gemini_session and not self._onboarding_completed:
                    #     try:
                    #         await self.gemini_session.send_realtime_input(
                    #             text="[USER JUST SHARED SCREEN FOR FIRST TIME! Provide the warm welcome message explaining what you can do. Be enthusiastic and helpful!]"
                    #         )
                    #         self._onboarding_completed = True
                    #         self._is_first_time_user = False
                    #     except Exception as e:
                    #         logger.debug(f"Onboarding context injection failed: {e}")

                    if self.gemini_session and self._running:
                        # Rate-limit to 1 FPS — Live API max for image input
                        now = time.time()
                        if now - self._last_frame_time < self._frame_cooldown:
                            continue  # drop this frame, too soon
                        self._last_frame_time = now
                        try:
                            await self.gemini_session.send_realtime_input(
                                video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
                            )
                            logger.debug(f"📹 Sent frame to Gemini: {len(frame_bytes)} bytes, {self._capture_width}x{self._capture_height}")
                            self._last_input_time = time.time()
                            self._last_activity = time.time()
                        except Exception as e:
                            logger.error(f"Failed to send video frame to Gemini: {e}")
                            # Mark that video sending failed
                            self.screen_stream_active = False

                elif msg_type == "text":
                    text = msg.get("data", "")
                    if text:
                        # Inject context hints from state machine
                        enhanced_text = self.state.inject_context_hint(text)
                        
                        # Don't send "processing" messages - they're internal thoughts
                        # Users should only see actual responses, not processing status
                        
                        # Check for memory commands first
                        memory_response = await self._handle_memory_command(text)
                        if memory_response:
                            await self.websocket.send_json({
                                "type": "text",
                                "data": memory_response,
                            })
                            logger.info(f"💭 Memory command handled: '{text}'")
                            continue
                        
                        # Send everything directly to Gemini — it handles natural language
                        # commands natively. The VoiceCommandProcessor layer was causing
                        # double-handling (frontend ack + Gemini response) and confusing
                        # "I didn't understand" messages for valid commands.
                        await self._process_normal_text_message(text)
                        
                        self._last_input_time = time.time()
                        self._last_activity = time.time()

                elif msg_type == "action_result":
                    action_id = msg.get("id", "unknown")
                    result = msg.get("result", "unknown")
                    if action_id in self._action_pending:
                        try:
                            self._action_pending[action_id].set_result(msg)
                        except asyncio.InvalidStateError:
                            pass
                        del self._action_pending[action_id]
                    else:
                        logger.debug("Discarding stale action_result for id=%s (no waiter)", action_id)
                    self._last_activity = time.time()

                elif msg_type == "extension_status":
                    available = msg.get("available", False)
                    self._extension_available = available
                    logger.info(f"Extension status: {'available' if available else 'NOT available'}")
                    if self.gemini_session and self._running:
                        try:
                            if available:
                                ctx = "[Browser extension is installed and active. All browser actions (click, type, scroll, navigate, press_key) will work normally.]"
                            else:
                                ctx = (
                                    "[IMPORTANT: The Spectra browser extension is NOT installed. "
                                    "Browser actions like click_element, type_text, scroll_page, press_key, and navigate will FAIL. "
                                    "If the user asks you to click, type, scroll, or navigate: "
                                    "1. Tell them the extension is not installed. "
                                    "2. Explain they need to install it from the Chrome Web Store or load it as an unpacked extension. "
                                    "3. You CAN still describe the screen, answer questions, and have a conversation. "
                                    "Do NOT attempt browser actions — they will fail with extension_unavailable.]"
                                )
                            await self.gemini_session.send_realtime_input(text=ctx)
                        except Exception as e:
                            logger.debug(f"Extension status injection skipped: {e}")

        except WebSocketDisconnect as e:
            if e.code == 1001:
                logger.info("Client navigated away (1001)")
            else:
                logger.info("Client disconnected (code=%s)", e.code)
            self._client_disconnected = True
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Client listener error: %s", e, exc_info=True)
            self._client_disconnected = True

    def _clean_thinking(self, text: str) -> str:
        """
        Remove thinking tags and internal reasoning from Gemini output.
        Uses the aggressive remove_narration() from orchestrator.
        """
        # Use the aggressive narration filter from orchestrator
        cleaned = remove_narration(text)
        
        # Additional cleanup for any remaining artifacts
        cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
        
        # Normalize whitespace after tag removal
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()

    async def _send_to_gemini(self, text: str) -> bool:
        """Send text to Gemini Live session, dropping silently during reconnect windows.

        Returns True if sent, False if dropped (session not ready).
        Injects current URL so Gemini always knows what page it's on without
        needing to call describe_screen or read_page_structure for location queries.
        """
        if not (self.gemini_session and self._running):
            logger.debug("_send_to_gemini: session not ready — message dropped")
            return False
        if self._current_url:
            text = f"[Page: {self._current_url}]\n{text}"
        text = text.rstrip() + "\n[Respond in the same language as this message.]"
        await self.gemini_session.send_realtime_input(text=text)
        return True

    async def _handle_tool_calls(self, tool_call):
        """Handle tool calls with proper error handling."""
        function_responses = []
        tool_calls_log = []  # For interaction logging

        for fc in tool_call.function_calls:
            args = dict(fc.args) if fc.args else {}
            start_time = time.time()
            
            # Log tool call for training dataset
            tool_calls_log.append({
                "name": fc.name,
                "args": args,
                "id": fc.id,
            })
            
            # Record action in state machine
            self.state.record_action(fc.name, args)
            
            if fc.name in SERVER_SIDE_TOOLS:
                result = await self._handle_server_tool(fc.name, args)
                function_responses.append(
                    types.FunctionResponse(
                        id=fc.id,
                        name=fc.name,
                        response={"result": result},
                    )
                )
                # Record server tool usage
                success = not any(x in result.lower() for x in ("error", "fail", "timeout"))
                duration = time.time() - start_time
            else:
                params = dict(args)
                if self._capture_width > 0:
                    params["_captureWidth"] = self._capture_width
                    params["_captureHeight"] = self._capture_height

                action_id = str(uuid.uuid4())[:8]
                logger.info("→ Sending action to extension: %s(%s) id=%s",
                            fc.name, {k: v for k, v in params.items() if not k.startswith("_")}, action_id)
                future: asyncio.Future = asyncio.get_running_loop().create_future()
                self._action_pending[action_id] = future
                await self.websocket.send_json({
                    "type": "action",
                    "action": fc.name,
                    "params": params,
                    "id": action_id,
                })

                try:
                    action_msg = await asyncio.wait_for(future, timeout=ACTION_TIMEOUT)
                    result = action_msg.get("result", "done")
                    logger.info("← Action result for %s: %s", fc.name, result[:120])
                except asyncio.TimeoutError:
                    result = "timeout: action took too long"
                    logger.warning("⏱ Action timeout for %s (id=%s)", fc.name, action_id)
                    if action_id in self._action_pending:
                        del self._action_pending[action_id]

                # Track current URL after successful navigation
                old_url = self._current_url
                if fc.name == "navigate":
                    nav_url = args.get("url", "")
                    if nav_url:
                        self._current_url = nav_url

                # Also update _current_url when a link click triggers page navigation.
                # content.js returns "clicked_link_navigate_expected:<href>" for <a> tags.
                # Check RAW result format (before _translate_action_result).
                if fc.name == "click_element" and result.lower().startswith("clicked_link_navigate_expected:"):
                    link_dest = result.split(":", 1)[1].strip() if ":" in result else ""
                    if link_dest and link_dest.startswith("http"):
                        self._current_url = link_dest

                # When page changes, clear caches and tell Gemini so it doesn't use old context.
                if self._current_url != old_url:
                    async with self._describe_cache_lock:
                        self._describe_cache.clear()
                    self._cache_access_times.clear()
                    if self.gemini_session and self._running:
                        try:
                            await self.gemini_session.send_realtime_input(
                                text=f"[Page changed to: {self._current_url}. Describe what you see now — ignore previous page content.]"
                            )
                        except Exception:
                            pass

                # Translate raw action result codes into plain English for Gemini.
                # Raw codes like "clicked_by_label_button_Sign in" cause Gemini to read
                # them aloud verbatim. Give it natural language so it can respond naturally.
                result = _translate_action_result(fc.name, result)

                # Auto-inject page structure after successful navigate or link click.
                # Saves Gemini one full round-trip tool call — it gets the new page content
                # immediately in the tool response, without needing to call read_page_structure.
                if fc.name == "navigate" and result.startswith("Navigation succeeded"):
                    try:
                        structure = await self._read_page_structure({})
                        result = f"{result}\n\n[Page content loaded automatically:]\n{structure}"
                    except Exception as _e:
                        logger.debug("Auto page structure after navigate failed: %s", _e)
                elif fc.name == "click_element" and result.startswith("Link clicked"):
                    # Link clicks don't wait for page load — give the new page 0.8s to settle
                    await asyncio.sleep(0.8)
                    try:
                        structure = await self._read_page_structure({})
                        result = f"{result}\n\n[Page content loaded automatically:]\n{structure}"
                    except Exception as _e:
                        logger.debug("Auto page structure after link click failed: %s", _e)

                function_responses.append(
                    types.FunctionResponse(
                        id=fc.id,
                        name=fc.name,
                        response={"result": result},
                    )
                )
                
                # Record client tool usage with enhanced tracking
                success = not any(x in result.lower() for x in ("error", "fail", "timeout", "no_element"))
                duration = time.time() - start_time

        if function_responses:
            async with self._tool_response_lock:
                try:
                    await self.gemini_session.send_tool_response(
                        function_responses=function_responses
                    )
                    tool_summary = ", ".join(
                        f"{fr.name}→{str(fr.response.get('result',''))[:80]}"
                        for fr in function_responses
                    )
                    logger.info(f"Tool responses: [{tool_summary}]")
                    
                    # Log interaction for fine-tuning dataset
                    # Note: We'll log the full interaction when we get the model response
                    self.state.interaction_log.append({
                        "tool_calls": tool_calls_log,
                        "timestamp": time.time(),
                    })
                    if len(self.state.interaction_log) > 500:
                        self.state.interaction_log = self.state.interaction_log[-500:]
                    
                except Exception as e:
                    logger.error(f"send_tool_response failed, closing session: {e}", exc_info=True)
                    self._running = False
                    raise

    async def _handle_memory_command(self, text: str) -> Optional[str]:
        """
        Handle memory-related voice commands.
        
        Returns response text if command was handled, None otherwise.
        """
        text_lower = text.lower()
        
        # "What do you remember about me?"
        if any(phrase in text_lower for phrase in ["what do you remember", "what have you learned", "tell me what you know"]):
            return self.memory.get_summary()
        
        # "Remember that I prefer..."
        if text_lower.startswith("remember that i prefer"):
            # Extract preference
            preference = text[len("remember that i prefer"):].strip()
            self.memory.remember("custom_instructions", 
                               self.memory.recall("custom_instructions", "") + f"\n- User prefers: {preference}")
            return f"Got it, I'll remember that you prefer {preference}"
        
        # "Forget everything" / "Clear my memory"
        if any(phrase in text_lower for phrase in ["forget everything", "clear my memory", "reset memory"]):
            self.memory.clear()
            return "I've cleared my memory. Starting fresh!"
        
        # "Remember this shortcut: [phrase] means [action]"
        if "remember this shortcut" in text_lower or "remember that" in text_lower and "means" in text_lower:
            try:
                # Parse "remember that 'check email' means navigate to gmail"
                parts = text_lower.split("means")
                if len(parts) == 2:
                    phrase = parts[0].replace("remember that", "").replace("remember this shortcut", "").strip().strip("'\"")
                    action = parts[1].strip()
                    self.memory.learn_shortcut(phrase, action)
                    return f"Got it! I'll remember that '{phrase}' means {action}"
            except Exception as e:
                logger.error(f"Failed to parse shortcut: {e}")
        
        return None

    def _save_flight_price(self, site: str, airline: str, price: float, currency: str = "EUR",
                          route: str = "", flight_time: str = "", details: str = ""):
        """Save a flight price for comparison across sites."""
        import time as time_module
        price_entry = {
            "site": site,
            "airline": airline,
            "price": price,
            "currency": currency,
            "route": route or self._current_search_route,
            "time": flight_time,
            "details": details,
            "timestamp": time_module.time()
        }
        self._flight_prices.append(price_entry)
        logger.info(f"Saved flight price: {airline} {currency}{price} on {site}")

    def _get_cheapest_flight(self) -> Optional[dict]:
        """Get the cheapest flight from tracked prices."""
        if not self._flight_prices:
            return None
        return min(self._flight_prices, key=lambda x: x["price"])

    def _compare_flight_prices(self) -> str:
        """Generate a comparison summary of all tracked flight prices."""
        if not self._flight_prices:
            return "No flight prices tracked yet."

        # Sort by price
        sorted_prices = sorted(self._flight_prices, key=lambda x: x["price"])

        # Build comparison text
        lines = []
        for i, flight in enumerate(sorted_prices, 1):
            site = flight["site"]
            airline = flight["airline"]
            price = flight["price"]
            currency = flight["currency"]
            time_str = flight.get("time", "")
            time_part = f" at {time_str}" if time_str else ""
            lines.append(f"{i}. {airline}: {currency}{price}{time_part} (via {site})")

        cheapest = sorted_prices[0]
        recommendation = f"\nRecommendation: {cheapest['airline']} at {cheapest['currency']}{cheapest['price']} on {cheapest['site']}"

        return "\n".join(lines) + recommendation

    def _clear_flight_prices(self):
        """Clear tracked flight prices for a new search."""
        self._flight_prices.clear()
        logger.info("Cleared flight price memory")

    async def _handle_server_tool(self, tool_name: str, args: dict) -> str:
        """Execute server-side tools with caching and parallel vision."""
        try:
            if tool_name == "describe_screen":
                # Re-send the latest frame to Gemini right now so it has the
                # freshest possible visual context when it processes this tool response.
                if self._latest_frame and self.gemini_session and self._running:
                    try:
                        frame_bytes = base64.b64decode(self._latest_frame)
                        await self.gemini_session.send_realtime_input(
                            video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
                        )
                        # Brief pause so Gemini processes the new frame before receiving
                        # the describe prompt — without this, it may describe a stale frame.
                        await asyncio.sleep(0.15)
                    except Exception as _fe:
                        logger.debug(f"describe_screen frame re-send skipped: {_fe}")
                result = await self._describe_screen(args)
                # Update state machine with screen context
                self.state.update_from_screen_description(result)
                return result
            elif tool_name == "wait_for_content":
                return await self._wait_for_content(args)
            elif tool_name == "save_snapshot":
                # Capture a text description of the current screen to store alongside the frame
                # so diff_screen can later tell Gemini what the screen looked like at save time.
                desc = await self._describe_screen({"focus_area": "full"}) if self._latest_frame else ""
                return save_snapshot(args.get("name"), self._latest_frame, description=desc)
            elif tool_name == "diff_screen":
                return diff_screen(args.get("name"), self._capture_width, self._capture_height)
            elif tool_name == "teach_me_app":
                return teach_me_app(args.get("focus", "all"))
            elif tool_name == "read_selection":
                return await self._read_selection(args)
            elif tool_name == "read_page_structure":
                return await self._read_page_structure(args)
            else:
                return f"Unknown server tool: {tool_name}"
        except Exception as e:
            logger.error(f"Tool error [{tool_name}]: {e}")
            return f"error: {e}"

    async def _describe_screen(self, args: dict) -> str:
        """Return a prompt that tells the model to describe what it sees.

        The Gemini Live API already receives video frames via send_realtime_input.
        The model HAS the visual context. This tool response just instructs it
        to describe the current screen content.
        """
        if not self._latest_frame:
            # Wait longer (4s) when screen was previously shared — page transitions,
            # heavy SPA renders (Google Flights, Kayak), and navigation can cause
            # multi-second frame gaps. 2s was too short and caused the agent to
            # give up and either hallucinate or ask to re-share screen.
            wait_ticks = 40 if self._screen_ever_shared else 20  # 4s vs 2s
            for _ in range(wait_ticks):
                await asyncio.sleep(0.1)
                if self._latest_frame:
                    break

            if not self._latest_frame:
                if self._screen_ever_shared:
                    logger.warning("⚠️ No current frame but screen was previously shared — falling back to read_page_structure guidance")
                    focus = args.get("focus_area", args.get("focus", "")) or "full"
                    return (
                        f"[SCREEN IS SHARED — video feed paused during page load or heavy render] "
                        f"The screen IS still shared. Do NOT ask the user to share their screen again. "
                        f"Use read_page_structure to get the page DOM (buttons, inputs, links) so you can continue. "
                        f"Focus: {focus}. PROCEED with the task — use read_page_structure now."
                    )
                # Rate-limit screen share requests to avoid spamming user
                if not hasattr(self, '_screen_share_requested_at'):
                    self._screen_share_requested_at = time.time()
                    return "No screen shared yet. Ask the user to press W to share their screen."

                time_since_request = time.time() - self._screen_share_requested_at
                if time_since_request > 10:
                    self._screen_share_requested_at = time.time()
                    return "Still waiting for screen share. Gently remind user: press W to share screen."

                # Silent wait — don't spam the user. Work with what you have or wait.
                return "[No screen available yet — user hasn't shared. Don't repeat the request. Continue conversation or wait silently.]"

        if hasattr(self, '_screen_share_requested_at'):
            delattr(self, '_screen_share_requested_at')

        focus = args.get("focus_area", args.get("focus", "")) or "full"
        self._last_describe_time = time.time()
        self.screen_stream_active = True

        frame_age = time.time() - self.last_frame_ts
        if frame_age > 5.0:
            logger.warning(f"⚠️ Frame is {frame_age:.1f}s old - may cause outdated descriptions")

        # Include frame age hint when stale so Gemini knows to be cautious
        stale_hint = ""
        if frame_age > 3.0:
            stale_hint = (
                f" ⚠️ Frame is {frame_age:.0f}s old — page may have changed since this frame. "
                f"If acting on a dynamic page (flights, search, forms), call read_page_structure "
                f"for accurate element positions before clicking."
            )

        prompt = (
            f"[SCREEN IS SHARED — {self._capture_width}x{self._capture_height}, focus: {focus}] "
            f"Look at what's on screen carefully before acting. "
            f"• If the user asked for a description → describe what you see. "
            f"• If the user wants an action → call the appropriate tool. No narration before tool calls. "
            f"• On forms/SPAs (flights, booking, search): read the visible fields first, then act step by step."
            f"{stale_hint}"
        )

        logger.info(f"🔍 describe_screen ({focus}, {self._capture_width}x{self._capture_height}, frame_age={frame_age:.1f}s)")
        return prompt

    async def _wait_for_content(self, args: dict) -> str:
        """Wait for a FRESH frame (newer than current), then describe.

        Use after typing into autocomplete/combobox fields — gives the page
        time to render dropdown suggestions before the agent tries to read them.
        """
        reason = args.get("reason", "content update")
        wait_ms = min(int(args.get("wait_ms", 2000)), 5000)  # cap at 5s
        baseline_ts = self.last_frame_ts

        # Wait for a frame newer than the current one
        waited = 0
        while waited < wait_ms:
            await asyncio.sleep(0.1)
            waited += 100
            if self.last_frame_ts > baseline_ts:
                break

        got_fresh = self.last_frame_ts > baseline_ts
        frame_age = time.time() - self.last_frame_ts

        # Re-send the fresh frame to Gemini so visual context is up to date
        if self._latest_frame and self.gemini_session and self._running:
            try:
                frame_bytes = base64.b64decode(self._latest_frame)
                await self.gemini_session.send_realtime_input(
                    video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
                )
                await asyncio.sleep(0.15)
            except Exception:
                pass

        focus = args.get("focus_area", "full")
        freshness = "FRESH" if got_fresh else f"unchanged ({frame_age:.1f}s old)"
        logger.info(f"⏳ wait_for_content ({reason}, waited={waited}ms, frame={freshness})")

        if got_fresh:
            return (
                f"[SCREEN UPDATED — {self._capture_width}x{self._capture_height}, focus: {focus}] "
                f"A fresh frame arrived after {waited}ms (reason: {reason}). "
                f"Look at what's on screen NOW — describe visible elements, dropdowns, suggestions, or form state. "
                f"If you see autocomplete suggestions/dropdown options, click the correct one."
            )
        else:
            return (
                f"[SCREEN — no new frame after {waited}ms, current frame is {frame_age:.1f}s old] "
                f"The page may not have visually changed yet (reason: {reason}). "
                f"Use read_page_structure to get the current DOM state (dropdown options, form fields) "
                f"or describe what you can see from the existing video context."
            )

    async def send_action_result(self, action_id: str, result: str):
        """Send action result with deduplication."""
        await self.websocket.send_json({
            "type": "action_result",
            "id": action_id,
            "result": result,
        })

    async def _preprocess_voice_command(self, text: str) -> dict:
        """
        Preprocess voice command before sending to Gemini (Task 4.3).
        
        This method:
        1. Updates context with current screen information
        2. Parses the command with full context
        3. Resolves pronouns and context-dependent references
        4. Formats command for Gemini with enhanced context
        
        Args:
            text: The user's voice command text
            
        Returns:
            dict with status, action, target, and other metadata
        """
        if self._latest_frame:
            try:
                screen_description = await self._describe_screen({"focus_area": "full"})
                self.voice_processor.update_context(screen_description=screen_description)
            except Exception as e:
                logger.warning(f"Failed to get screen context: {e}")
        
        # Step 2: Update context with conversation history for pronoun resolution
        if hasattr(self, '_conversation_history'):
            self.voice_processor.update_context(conversation_history=self._conversation_history)
        
        # Step 3: Parse the voice command with full context
        parsed_command = self.voice_processor.parse_command(text)
        
        # Step 4: Handle different command parsing results
        if parsed_command.action.value == "unknown":
            return {
                "status": "unknown",
                "original_text": text,
                "suggestions": parsed_command.suggestions or []
            }
        
        # Step 5: Check if command is ambiguous (low confidence)
        if parsed_command.confidence < 0.5:
            return {
                "status": "ambiguous",
                "action": parsed_command.action.value,
                "target": parsed_command.target,
                "confidence": parsed_command.confidence,
                "original_text": text,
                "suggestions": parsed_command.suggestions or []
            }
        
        # Step 6: Format command for execution
        execution_format = self.voice_processor.format_command_for_execution(parsed_command)
        
        # Step 7: Send command acknowledgment to user
        ack_message = self._generate_command_acknowledgment(parsed_command, text)
        await self.websocket.send_json({
            "type": "text",
            "data": ack_message,
        })
        
        # Step 8: Send enhanced text to Gemini with command context
        command_context = self._build_command_context(parsed_command, execution_format)
        enhanced_text = f"{text}\n\n{command_context}"

        if not await self._send_to_gemini(enhanced_text):
            logger.warning("_send_to_gemini: enhanced voice command dropped (Gemini reconnecting)")

        # Step 9: Update context with the executed command
        self.voice_processor.update_context(recent_command=parsed_command)
        
        # Step 10: Track mentioned elements for pronoun resolution
        if parsed_command.target:
            self.voice_processor.update_context(mentioned_element=parsed_command.target)
        
        return {
            "status": "success",
            "action": parsed_command.action.value,
            "target": parsed_command.target,
            "confidence": parsed_command.confidence,
            "context_dependent": parsed_command.context_dependent,
            "compound": parsed_command.compound
        }
    
    def _generate_command_acknowledgment(self, parsed_command, original_text: str) -> str:
        """Generate user-friendly acknowledgment for voice commands."""
        if parsed_command.compound:
            return f"I'll execute the compound command: {original_text}"
        
        ack = f"I'll {parsed_command.action.value}"
        
        if parsed_command.target:
            ack += f" {parsed_command.target}"
        
        if parsed_command.context_dependent:
            ack += " (using context from previous conversation)"
        
        return ack
    
    def _build_command_context(self, parsed_command, execution_format: dict) -> str:
        """Build enhanced context string for Gemini."""
        context_parts = [f"[Voice Command: {execution_format}]"]
        
        # Add context-dependent information
        if parsed_command.context_dependent:
            context_parts.append("[Context: This command references previously mentioned elements]")
        
        # Add compound command information
        if parsed_command.compound and parsed_command.sub_commands:
            sub_actions = [f"{cmd.action.value} {cmd.target or ''}" for cmd in parsed_command.sub_commands]
            context_parts.append(f"[Sub-commands: {', '.join(sub_actions)}]")
        
        # Add confidence information for low-confidence commands
        if parsed_command.confidence < 0.7:
            context_parts.append(f"[Confidence: {parsed_command.confidence:.2f} - may need clarification]")
        
        return "\n".join(context_parts)
    
    async def _handle_ambiguous_command(self, text: str, preprocess_result: dict):
        """
        Handle ambiguous voice commands by providing suggestions (Task 4.3).
        
        Args:
            text: Original command text
            preprocess_result: Result from preprocessing with ambiguity info
        """
        action = preprocess_result.get("action", "unknown")
        target = preprocess_result.get("target", "")
        confidence = preprocess_result.get("confidence", 0.0)
        suggestions = preprocess_result.get("suggestions", [])
        
        # Build ambiguity message
        ambiguity_message = f"I'm not entirely sure about that command (confidence: {confidence:.0%}). "
        
        if target:
            ambiguity_message += f"Did you want me to {action} '{target}'? "
        else:
            ambiguity_message += f"Did you want me to {action}? "
        
        # Add suggestions
        if suggestions:
            ambiguity_message += "Here are some suggestions: " + "; ".join(suggestions[:3])
        
        # Send ambiguity message to user
        await self.websocket.send_json({
            "type": "text",
            "data": ambiguity_message,
        })
        
        # Also send to Gemini for natural language clarification
        clarification_context = f"[Ambiguous Command: action={action}, target={target}, confidence={confidence:.2f}]"
        enhanced_text = f"{text}\n\n{clarification_context}\n\nPlease clarify or confirm the user's intent."
        
        if not await self._send_to_gemini(enhanced_text):
            logger.warning("_send_to_gemini: enhanced voice command dropped (Gemini reconnecting)")

        logger.info(f"⚠️ Ambiguous command handled: {action} -> {target} (confidence: {confidence:.2f})")
    
    async def _handle_unknown_command(self, text: str, preprocess_result: dict):
        """
        Handle unknown voice commands by providing suggestions (Task 4.3).
        
        Args:
            text: Original command text
            preprocess_result: Result from preprocessing with unknown status
        """
        suggestions = preprocess_result.get("suggestions", [])
        
        # Build unknown command message
        unknown_message = "I didn't understand that command. "
        
        if suggestions:
            unknown_message += "Here are some suggestions:\n" + "\n".join(f"• {s}" for s in suggestions[:4])
        else:
            unknown_message += "Try commands like 'click the button', 'type hello', or 'scroll down'."
        
        # Send unknown command message to user
        await self.websocket.send_json({
            "type": "text",
            "data": unknown_message,
        })
        
        # Still send to Gemini for natural language processing
        # Gemini might understand the intent even if our parser doesn't
        await self._process_normal_text_message(text)
        
        logger.info(f"❓ Unknown command handled: '{text}' - provided {len(suggestions)} suggestions")
    
    def _update_conversation_context(self, text: str):
        """
        Update conversation context for pronoun resolution (Task 4.3).
        
        Maintains a rolling window of recent messages to help resolve
        context-dependent commands like "click it" or "type in that field".
        
        Args:
            text: The user's message text
        """
        # Initialize conversation history if not exists
        if not hasattr(self, '_conversation_history'):
            self._conversation_history = []
        
        # Add message to history
        self._conversation_history.append(text)
        
        # Keep only last 10 messages for context
        self._conversation_history = self._conversation_history[-10:]
        
        # Update voice processor context
        self.voice_processor.update_context(conversation_history=self._conversation_history)
        
        logger.debug(f"📝 Updated conversation context (history size: {len(self._conversation_history)})")

    # Keywords that indicate the user is asking about visible screen content
    _VISUAL_QUERY_KEYWORDS = frozenset([
        "see", "screen", "read", "news", "article", "page", "open",
        "show", "visible", "display", "there", "current", "what's",
        "whats", "looking", "describe", "tell me", "what do", "what is",
        "what are", "headline", "title", "website", "tab", "window",
    ])

    def _is_visual_query(self, text: str) -> bool:
        """Return True if the message is likely asking about on-screen content."""
        lower = text.lower()
        return any(kw in lower for kw in self._VISUAL_QUERY_KEYWORDS)

    async def _process_normal_text_message(self, text: str):
        """Process normal text messages with workflow detection (extracted from main handler)."""

        # ── Re-send latest frame for visual queries ──────────────────────────
        # If the user is asking about something on screen AND we have a frame,
        # re-send the frame so Gemini has fresh visual context before responding.
        # Do NOT inject describe_screen output as text — that's a prompt, not content.
        if self._is_visual_query(text) and self._latest_frame and self.gemini_session and self._running:
            try:
                frame_bytes = base64.b64decode(self._latest_frame)
                await self.gemini_session.send_realtime_input(
                    video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
                )
                self._last_frame_time = time.time()
                logger.debug(f"👁️ Re-sent frame for visual query: '{text[:60]}'")
            except Exception as e:
                logger.debug(f"Frame re-send for visual query skipped: {e}")

        # Send text to Gemini
        if not await self._send_to_gemini(text):
            logger.warning("_send_to_gemini: voice command dropped (Gemini reconnecting)")
    # ━━━ ORCHESTRATOR HELPER METHODS ━━━
    
    def _get_enhanced_system_instruction(self, user_text: str = "") -> str:
        """
        Get system instruction with optional destructive action reminder.
        
        Args:
            user_text: The user's input text to check for destructive actions
            
        Returns:
            Enhanced system instruction with context-specific reminders
        """
        from app.agents.orchestrator import get_confirmation_reminder, SPECTRA_SYSTEM_INSTRUCTION
        
        core_instruction = SPECTRA_SYSTEM_INSTRUCTION
        
        # Add confirmation reminder if this is a destructive action
        reminder = get_confirmation_reminder(user_text)
        if reminder:
            return f"{core_instruction}\n\n{reminder}"
        
        return core_instruction
    
    def _should_enforce_describe_first(self) -> bool:
        """
        Check if we should enforce describe_screen before actions.
        
        Returns:
            True if describe_screen should be called first
        """
        # If we haven't described the screen recently, enforce it
        time_since_describe = time.time() - self._last_describe_time
        return time_since_describe > 2.0  # 2 seconds since last describe
    
    async def _read_selection(self, args: dict) -> str:
        """
        Read selected or highlighted text on screen.
        
        Args:
            args: Dict with 'mode' key ('selected', 'paragraph', or 'page')
            
        Returns:
            Text content to read aloud
        """
        mode = args.get("mode", "selected")
        
        # Request selection from client
        action_id = str(uuid.uuid4())[:8]
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._action_pending[action_id] = future
        await self.websocket.send_json({
            "type": "action",
            "action": "read_selection",
            "params": {"mode": mode},
            "id": action_id,
        })
        try:
            action_msg = await asyncio.wait_for(future, timeout=ACTION_TIMEOUT)
            result = action_msg.get("result", "No text selected")
            return f"Reading {mode}: {result}"
        except asyncio.TimeoutError:
            if action_id in self._action_pending:
                del self._action_pending[action_id]
            return f"Timeout reading {mode} text"

    async def _read_page_structure(self, args: dict) -> str:
        """Fetch the DOM structure of the current (or given) page via the overlay API.

        Calls _analyse_uncached directly to avoid an HTTP round-trip.
        Returns a compact, structured summary that Gemini can use to pick
        precise CSS selectors and element labels before acting.
        """
        from app.overlay import _analyse_uncached

        url = args.get("url") or self._current_url
        if not url:
            return (
                "No URL available. Navigate to a page first, or pass the URL as an argument."
            )

        try:
            data = await _analyse_uncached(url)
        except Exception as e:
            logger.warning(f"read_page_structure failed for {url}: {e}")
            return f"Could not analyse page structure: {e}"

        title = data.get("title", "")

        title_lower = title.lower()

        # Detect login redirects — server-side fetch has no auth cookies, so authenticated
        # apps (Gmail, GitHub, etc.) redirect to their login page. Gemini must not act on
        # login-page elements when the screen already shows the logged-in app.
        _LOGIN_SIGNALS = ("sign in", "log in", "login", "sign-in", "signin", "authenticate", "sign up")
        if any(s in title_lower for s in _LOGIN_SIGNALS):
            logger.info(f"read_page_structure: login redirect detected for {url} (title={title!r})")
            return (
                f"[read_page_structure: page requires authentication — server cannot access logged-in content] "
                f"The page title returned was '{title}', which is a login page. "
                f"This means the server fetch was redirected to a sign-in screen. "
                f"The screen share shows the actual logged-in page. "
                f"Use describe_screen instead to see what's currently on screen."
            )

        # Detect bot-detection / challenge pages — Cloudflare, Akamai, etc.
        _BOT_SIGNALS = ("just a moment", "access denied", "attention required", "checking your browser",
                        "please wait", "ddos-guard", "ray id", "security check")
        if any(s in title_lower for s in _BOT_SIGNALS):
            logger.info(f"read_page_structure: bot-detection page for {url} (title={title!r})")
            return (
                f"[read_page_structure: bot-detection challenge page returned] "
                f"The server received a security challenge page (Cloudflare/Akamai) instead of real content. "
                f"The screen share shows the actual page. Use describe_screen instead."
            )

        elements = data.get("elements", [])

        # Detect SPA shell — JS-rendered pages return near-empty HTML to server-side fetchers.
        # If we got very few elements and no meaningful title, the page is client-side rendered.
        if len(elements) < 3:
            logger.info(f"read_page_structure: likely SPA shell for {url} ({len(elements)} elements)")
            return (
                f"[read_page_structure: page appears to be a JavaScript SPA — server-side fetch returned only "
                f"{len(elements)} element(s), which means content is rendered client-side and not visible to the server. "
                f"The screen share shows the fully rendered page. Use describe_screen instead."
            )

        lines: list[str] = []
        if title:
            lines.append(f"Page: {title}")
        lines.append(f"URL: {url}")
        lines.append(f"{len(elements)} interactive/structural elements found:")

        # Group by importance so the model sees what matters most first
        for importance in ("high", "medium", "low"):
            group = [e for e in elements if e.get("importance") == importance]
            if not group:
                continue
            lines.append(f"\n[{importance.upper()}]")
            for el in group:
                etype = el.get("type", "?")
                role = el.get("role", "")
                text = el.get("text", "").strip()
                sel = el.get("selector", "")
                entry = f'  {etype}'
                if role:
                    entry += f' ({role})'
                if text:
                    entry += f': "{text}"'
                if sel:
                    entry += f" → {sel}"
                lines.append(entry)

        return "\n".join(lines)
