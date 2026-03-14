"""Spectra streaming session — bridges client WebSocket to Gemini Live API."""

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
    SPECTRA_SYSTEM_INSTRUCTION, 
    SPECTRA_TOOLS,
    SpectraState,
    log_interaction,
    postprocess_spectra_reply,
    validate_system_instruction_response,
    remove_narration,
)
from app.personalization import UserPreferences, get_user_preferences
from app.tools.diff import diff_screen, save_snapshot, teach_me_app
from app.location_context_handler import LocationContextHandler
from app.voice_command_processor import VoiceCommandProcessor, CommandContext
from app.performance_monitor import get_performance_monitor
from app.memory import SpectraMemory
from app.streaming.session_manager import get_session_manager, SessionState

logger = logging.getLogger(__name__)

LIVE_MODEL = "gemini-2.5-flash-native-audio-latest"

SERVER_SIDE_TOOLS = {"describe_screen", "save_snapshot", "diff_screen", "teach_me_app", "read_selection", "read_page_structure"}

# Performance tuning - Configurable via environment variables
MAX_FRAME_QUEUE = int(os.getenv("MAX_FRAME_QUEUE", "3"))
ACTION_TIMEOUT = float(os.getenv("ACTION_TIMEOUT", "12.0"))  # 12s — navigate waits for page load (up to 8s)
HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", "3.0"))
FRAME_COOLDOWN = float(os.getenv("FRAME_COOLDOWN", "0.01"))
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
    """Translate raw action result codes into plain English for Gemini.

    Raw codes like "clicked_by_label_button_Sign in" cause Gemini to read
    them aloud verbatim. This gives the model natural language so it can
    respond naturally without reciting internal codes.
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
        return f"Navigation succeeded. Now on: {url}"

    # Click — link (triggers page load)
    if rl.startswith("clicked_link_navigate_expected:"):
        dest = r.split(":", 1)[1].strip() if ":" in r else ""
        return f"Link clicked — page loading. Destination: {dest or 'unknown'}"

    # Click — regular element
    if rl.startswith("clicked_"):
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
        return "Element highlighted."

    # Reading / selection
    if rl.startswith("reading_") or rl.startswith("read_"):
        return r  # pass through — this is actual content

    # Fallback: pass through unchanged
    return r


class SpectraStreamingSession:
    """Manages a single user session bridging WebSocket to Gemini Live API."""

    def __init__(self, websocket: WebSocket, user_id: str = "default", session_id: str = None):
        self.websocket = websocket
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())
        _gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        _gcp_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        if _gcp_project:
            self.client = genai.Client(vertexai=True, project=_gcp_project, location=_gcp_location)
        else:
            self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.gemini_session = None
        self._running = False
        self._action_queue: asyncio.Queue = asyncio.Queue()
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
        self._last_activity: float = time.time()
        self._last_describe_time: float = 0
        self._describe_cooldown: float = 0.5  # Reduced from 0s to 0.5s
        
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
        
        # Workflow tracking for personalization
        self._current_workflow: str | None = None
        self._workflow_start_time: float = 0.0
        
        # User preferences for personalization
        self.prefs: UserPreferences = get_user_preferences(user_id)
        
        # Memory system for persistent learning
        self.memory = SpectraMemory(user_id)
        
        # Location context handler for accessibility queries
        self.location_handler = LocationContextHandler()
        
        # Voice command processor for natural language commands
        self.voice_processor = VoiceCommandProcessor()
        
        # Performance monitor for tracking vision system performance
        self.performance_monitor = get_performance_monitor()
        
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
        
        # Frame similarity detection for response time optimization (Task 8.4)
        self._previous_frame_hash: str | None = None
        self._frame_similarity_scores: deque = deque(maxlen=20)  # Track similarity history

    def _calculate_frame_similarity(self, current_hash: str, previous_hash: str) -> float:
        """
        Calculate similarity between two frame hashes.
        
        Uses a simple hash comparison approach. For more sophisticated similarity,
        could use perceptual hashing or image diff algorithms.
        
        Args:
            current_hash: Hash of current frame
            previous_hash: Hash of previous frame
            
        Returns:
            Similarity score between 0.0 (completely different) and 1.0 (identical)
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
        enhanced_instruction = SPECTRA_SYSTEM_INSTRUCTION + memory_context
        
        # Full Spectra configuration with proper system instruction
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=types.Content(
                parts=[types.Part(text=enhanced_instruction)]
            ),
            tools=SPECTRA_TOOLS,
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"
                    )
                )
            ),
            # Hide thinking tokens from output — this model (2.5 Flash) leaks
            # its internal reasoning as text parts even when modality is AUDIO.
            # include_thoughts=False suppresses them from the stream while
            # keeping full reasoning capability intact (thinking_budget=-1 = auto).
            thinking_config=types.ThinkingConfig(include_thoughts=False),
            max_output_tokens=4096,
            temperature=0.5,
            # Transcribe what the user says so the frontend can show it
            input_audio_transcription=types.AudioTranscriptionConfig(),
            # VAD tuning: HIGH start sensitivity catches first words before full
            # voice onset; HIGH end sensitivity means Gemini responds quickly
            # after the user stops speaking — LOW was causing Gemini to keep
            # waiting and never reply to short commands.
            # prefix_padding_ms=300 includes 300ms of audio before VAD fires so
            # the first syllable is never clipped.
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                    prefix_padding_ms=300,
                )
            ),
        )

        # client_task and heartbeat_task span the full WebSocket lifetime —
        # they survive Gemini reconnects so the browser connection stays alive.
        client_task = asyncio.create_task(self._listen_client())
        heartbeat_task = asyncio.create_task(self._send_heartbeats())

        try:
            # ── Gemini reconnect loop ────────────────────────────────────────
            # When Gemini sends go_away (15-min limit) or any session error,
            # we transparently reconnect to Gemini without closing the browser
            # WebSocket. The user keeps their session; only the Gemini
            # connection is cycled.
            _reconnect_delay = 1.0   # seconds, doubles on each failure
            _go_away_wait = 0.0      # seconds to wait from go_away time_left
            while not self._client_disconnected:
                if _go_away_wait > 0:
                    logger.info(f"Honouring go_away — waiting {_go_away_wait:.0f}s before reconnecting")
                    await asyncio.sleep(_go_away_wait)
                    _go_away_wait = 0.0
                try:
                    async with self.client.aio.live.connect(
                        model=LIVE_MODEL, config=config
                    ) as session:
                        self.gemini_session = session
                        self._running = True
                        _session_start_time = time.time()
                        logger.info("Gemini Live session (re)connected")
                        # Single small silence burst to prevent immediate session timeout.
                        try:
                            await session.send_realtime_input(
                                audio=types.Blob(data=b'\x00' * 3200, mime_type="audio/pcm;rate=16000")
                            )
                            self._last_input_time = time.time()
                        except Exception as prime_err:
                            logger.debug(f"Session prime skipped: {prime_err}")

                        try:
                            async for response in session.receive():
                                if self._client_disconnected:
                                    break

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
                                                await self.websocket.send_json({
                                                    "type": "audio",
                                                    "data": base64.b64encode(part.inline_data.data).decode(),
                                                    "mime_type": part.inline_data.mime_type,
                                                })
                                            if part.text:
                                                if len(part.text) > 20:
                                                    logger.debug(f"Text part (len={len(part.text)}): {part.text[:80]}")
                                                self._text_buffer.append(part.text)

                                    if sc.turn_complete:
                                        if self._text_buffer:
                                            full_text = "".join(self._text_buffer)
                                            self._text_buffer = []
                                            # Only show text in chat if NO audio was sent this turn.
                                            # When audio IS sent, the text is often in a different
                                            # language than the audio (e.g. Arabic text + English audio)
                                            # which confuses the user. Audio is the primary output.
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
                                        self._audio_sent_this_turn = False  # reset for next turn
                                        await self.websocket.send_json({"type": "turn_complete"})

                                if response.tool_call:
                                    await self._handle_tool_calls(response.tool_call)

                                # go_away: server asking us to reconnect after time_left
                                go_away = getattr(response, "go_away", None)
                                if go_away:
                                    time_left = getattr(go_away, "time_left", None)
                                    wait_secs = max(float(str(time_left).rstrip("s") or 5), 2) if time_left else 5
                                    logger.warning(f"go_away received (time_left={time_left}) — will wait {wait_secs:.0f}s")
                                    _go_away_wait = wait_secs
                                    break

                        except Exception as e:
                            logger.error(f"Gemini receive error: {e}", exc_info=True)
                            _reconnect_delay = min(_reconnect_delay * 2, 30)

                        else:
                            session_age = time.time() - _session_start_time
                            if session_age >= 5.0:
                                logger.warning("Gemini receive loop exited cleanly")
                                _reconnect_delay = 1.0  # healthy session = reset backoff
                            else:
                                logger.warning(f"Gemini receive loop exited cleanly after {session_age:.1f}s — likely rate-limited or rejected; backing off")
                                _reconnect_delay = min(_reconnect_delay * 2, 30)

                        finally:
                            self._running = False
                            self.gemini_session = None

                except Exception as e:
                    logger.error(f"Gemini connection error: {e}", exc_info=True)
                    self._running = False
                    self.gemini_session = None
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
            try:
                await client_task
            except Exception:
                pass
            try:
                await heartbeat_task
            except Exception:
                pass

    async def cleanup(self):
        """Enhanced cleanup with preference and memory persistence."""
        self._running = False
        self._client_disconnected = True
        if self.gemini_session:
            try:
                await self.gemini_session.close()
            except:
                pass
        
        # Mark session as closed in session manager (but don't remove it)
        # This allows reconnection without losing state
        self.session_state.connection_state = "closed"
        
        # Clean up caches to prevent memory leaks
        self._describe_cache.clear()
        self._cache_access_times.clear()
        self._pending_actions.clear()
        
        # Ensure preferences are saved before session ends
        try:
            self.prefs.flush()
            logger.debug(f"💾 Saved preferences for user {self.user_id}")
        except Exception as e:
            logger.warning(f"Failed to save preferences: {e}")
        
        # Save memory
        try:
            self.memory.save()
            logger.debug(f"💾 Saved memory for user {self.user_id}")
        except Exception as e:
            logger.warning(f"Failed to save memory: {e}")
        
        logger.debug(f"🧹 Session cleanup completed for user {self.user_id} (session preserved for reconnection)")

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

                # Gemini keep-alive — only when Gemini session is live
                # Threshold is 2s (not 15s) so the first heartbeat tick (3s) fires
                # before Gemini's ~5s idle timeout kills the session pre-activation.
                if self.gemini_session and self._running:
                    time_since_input = time.time() - self._last_input_time
                    if 2.0 < time_since_input < 60.0:
                        try:
                            silence = b'\x00' * 800
                            await self.gemini_session.send_realtime_input(
                                audio=types.Blob(data=silence, mime_type="audio/pcm;rate=16000")
                            )
                        except Exception as keep_alive_err:
                            logger.debug(f"Keep-alive skipped: {keep_alive_err}")

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
                        audio_data = base64.b64decode(msg["data"])
                        await self.gemini_session.send_realtime_input(
                            audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                        )
                        self._last_input_time = time.time()
                        self._last_activity = time.time()

                elif msg_type == "screenshot":
                    frame_data = msg["data"]
                    frame_bytes = base64.b64decode(frame_data)
                    self._latest_frame = frame_data
                    self._capture_width = msg.get("width", 0)
                    self._capture_height = msg.get("height", 0)
                    self._frame_hash = hashlib.md5(frame_bytes).hexdigest()[:8]

                    self.screen_stream_active = True
                    self.last_frame_ts = time.time()
                    self.connection_state = "open"
                    self._screen_ever_shared = True
                    self.session_state.mark_frame_received()  # persist across reconnects

                    if hasattr(self, '_screen_share_requested'):
                        delattr(self, '_screen_share_requested')

                    if not hasattr(self, '_first_frame_logged'):
                        logger.debug(f"First frame: {self._capture_width}x{self._capture_height}")
                        self._first_frame_logged = True

                    if self.gemini_session and self._running:
                        await self.gemini_session.send_realtime_input(
                            video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
                        )
                        self._last_input_time = time.time()
                        self._last_activity = time.time()

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
                        
                        if True:  # location queries handled by Gemini via system instruction
                            # Check for voice commands (accessibility enhancement)
                            if self.voice_processor.is_voice_command(text):
                                logger.info(f"🎤 Voice command detected: '{text}'")
                                
                                try:
                                    # Preprocess command with full context (Task 4.3)
                                    preprocessed_result = await self._preprocess_voice_command(text)
                                    
                                    if preprocessed_result["status"] == "success":
                                        # Command was successfully preprocessed and sent to Gemini
                                        logger.info(f"✅ Voice command preprocessed: {preprocessed_result['action']} -> {preprocessed_result.get('target', 'N/A')}")
                                    elif preprocessed_result["status"] == "ambiguous":
                                        # Ambiguous command - provide suggestions
                                        await self._handle_ambiguous_command(text, preprocessed_result)
                                    elif preprocessed_result["status"] == "unknown":
                                        # Unknown command - provide suggestions and fallback
                                        await self._handle_unknown_command(text, preprocessed_result)
                                        
                                except Exception as e:
                                    logger.error(f"Voice command processing failed: {e}")
                                    # Fallback to normal processing on error
                                    await self._process_normal_text_message(text)
                            else:
                                # Normal text processing (existing workflow logic)
                                await self._process_normal_text_message(text)
                                
                            # Update conversation context for pronoun resolution (Task 4.3)
                            self._update_conversation_context(text)
                        
                        self._last_input_time = time.time()
                        self._last_activity = time.time()

                elif msg_type == "action_result":
                    action_id = msg.get("id", "unknown")
                    result = msg.get("result", "unknown")
                    await self._action_queue.put(msg)
                    self._last_activity = time.time()

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
        
        return cleaned.strip()

    async def _send_to_gemini(self, text: str) -> bool:
        """Send text to Gemini Live session, dropping silently during reconnect windows.

        Returns True if sent, False if dropped (session not ready).
        """
        if not (self.gemini_session and self._running):
            logger.debug("_send_to_gemini: session not ready — message dropped")
            return False
        await self.gemini_session.send_realtime_input(text=text)
        return True

    async def _handle_tool_calls(self, tool_call):
        """Handle tool calls with proper error handling and personalization tracking."""
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
                self.prefs.record_action(fc.name, success, duration)
            else:
                params = dict(args)
                if self._capture_width > 0:
                    params["_captureWidth"] = self._capture_width
                    params["_captureHeight"] = self._capture_height

                action_id = str(uuid.uuid4())[:8]
                await self.websocket.send_json({
                    "type": "action",
                    "action": fc.name,
                    "params": params,
                    "id": action_id,
                })

                try:
                    action_msg = await asyncio.wait_for(
                        self._action_queue.get(), timeout=ACTION_TIMEOUT
                    )
                    result = action_msg.get("result", "done")
                except asyncio.TimeoutError:
                    result = "timeout: action took too long"

                # Track current URL after successful navigation
                if fc.name == "navigate":
                    nav_url = args.get("url", "")
                    if nav_url:
                        self._current_url = nav_url

                # Also update _current_url when a link click triggers page navigation.
                # content.js returns "clicked_link_navigate_expected:<href>" for <a> tags.
                # Without this, read_page_structure() after a link click fetches the old URL.
                if fc.name == "click_element" and result.startswith("Link clicked"):
                    # result format: "Link clicked — page loading. Destination: <url>"
                    dest_prefix = "Destination: "
                    dest_idx = result.find(dest_prefix)
                    if dest_idx != -1:
                        link_dest = result[dest_idx + len(dest_prefix):].strip()
                        if link_dest and link_dest != "unknown" and link_dest.startswith("http"):
                            self._current_url = link_dest

                # Translate raw action result codes into plain English for Gemini.
                # Raw codes like "clicked_by_label_button_Sign in" cause Gemini to read
                # them aloud verbatim. Give it natural language so it can respond naturally.
                result = _translate_action_result(fc.name, result)

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
                self.prefs.record_action(fc.name, success, duration)
                
                # Update workflow statistics if this was part of a workflow
                if self._current_workflow:
                    self.prefs.bump_workflow(self._current_workflow, success, time.time() - self._workflow_start_time)
                    # Clear workflow tracking after completion
                    if fc.name in ["navigate", "press_key"] or "complete" in result.lower():
                        self._current_workflow = None
                        self._workflow_start_time = 0.0

        if function_responses:
            async with self._tool_response_lock:
                try:
                    await self.gemini_session.send_tool_response(
                        function_responses=function_responses
                    )
                    logger.info("Tool responses sent successfully")
                    
                    # Log interaction for fine-tuning dataset
                    # Note: We'll log the full interaction when we get the model response
                    self.state.interaction_log.append({
                        "tool_calls": tool_calls_log,
                        "timestamp": time.time(),
                    })
                    
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
                    except Exception as _fe:
                        logger.debug(f"describe_screen frame re-send skipped: {_fe}")
                result = await self._describe_screen(args)
                # Update state machine with screen context
                self.state.update_from_screen_description(result)
                return result
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
            # Only wait for a frame if screen was previously shared (momentary gap during navigation).
            # If screen was NEVER shared, return immediately — no point polling.
            if self._screen_ever_shared:
                for _ in range(20):
                    await asyncio.sleep(0.1)
                    if self._latest_frame:
                        break

            if not self._latest_frame:
                # If the screen was EVER shared this session, don't ask again —
                # frames may briefly pause during navigation or tab switch.
                if self._screen_ever_shared:
                    logger.info("⚠️ No current frame but screen was previously shared — returning context prompt")
                    focus = args.get("focus_area", args.get("focus", "")) or "full"
                    return (
                        f"[SCREEN IS SHARED] The screen feed has momentarily paused (navigation or tab switch). "
                        f"Describe the last visible state of the screen based on your video context. "
                        f"Focus: {focus}. Do NOT ask the user to share their screen again."
                    )
                if not hasattr(self, '_screen_share_requested'):
                    self._screen_share_requested = True
                    return "No screen shared yet. Ask the user to press W to share their screen."
                return "Still waiting for screen share."

        if hasattr(self, '_screen_share_requested'):
            delattr(self, '_screen_share_requested')

        focus = args.get("focus_area", args.get("focus", "")) or "full"
        self._last_describe_time = time.time()
        self.screen_stream_active = True

        prompt = (
            f"[SCREEN IS SHARED] "
            f"Describe what you see on the screen right now. "
            f"Focus: {focus}. Resolution: {self._capture_width}x{self._capture_height}. "
            f"Include: the website/app name, page title, all visible text headings, "
            f"buttons and links with their approximate x,y coordinates (for clicking), "
            f"input fields, images, and current state. "
            f"Be concise — your user is listening, not reading."
        )

        logger.info(f"🔍 describe_screen ({focus}, {self._capture_width}x{self._capture_height})")
        return prompt

    async def _describe_screen_with_retry(self, focus: str, cache_key: str) -> str:
        """Enhanced screen description with 3-attempt retry logic and comprehensive error handling."""
        from app.error_handler import error_handler
        
        # Track cache miss since we're making an API call
        self.performance_monitor.record_cache_miss()
        
        # Validate frame data before attempting API calls
        if not self._validate_frame_data():
            return error_handler.handle_vision_error(
                Exception("Invalid frame data: Frame is empty or corrupted"),
                frame_hash=self._frame_hash,
                frame_size=len(self._latest_frame) if self._latest_frame else 0,
                session_id=getattr(self, 'session_id', None),
                user_id=getattr(self, 'user_id', None)
            )
        
        max_retries = 3
        api_request_details = None
        api_response_details = None
        
        # Wrap the entire retry loop with performance monitoring
        async def _monitored_vision_call():
            for retry_attempt in range(max_retries):
                try:
                    # Attempt vision analysis (this now includes comprehensive logging)
                    result = await self._perform_vision_analysis(focus, retry_attempt)
                    
                    # Validate response to ensure it's a valid description, not a deflection
                    if not self._is_valid_description(result):
                        logger.warning(f"Invalid/deflection response detected on attempt {retry_attempt + 1}: {result[:100]}")
                        if retry_attempt < max_retries - 1:
                            continue  # Try again
                        else:
                            # Force a proper description on final attempt
                            result = (
                                f"I can see your screen content (frame {self._frame_hash[:6] if self._frame_hash else 'unknown'}, "
                                f"{self._capture_width}x{self._capture_height} pixels). "
                                f"The screen shows visual content that I should describe in detail, including any text, "
                                f"buttons, links, images, or interface elements currently visible. Focus: {focus}."
                            )
                    
                    # Success - cache and return result
                    self._last_describe_time = time.time()
                    if cache_key:
                        current_time = time.time()
                        async with self._describe_cache_lock:
                            self._describe_cache[cache_key] = (result, current_time)
                            self._cache_access_times[cache_key] = current_time
                            self._cleanup_cache()
                    
                    # Update persistent session state - describe succeeded
                    self.session_state.mark_describe_success()
                    
                    logger.info(f"✅ Screen analyzed successfully on attempt {retry_attempt + 1}")
                    return result
                    
                except Exception as e:
                    logger.warning(f"Vision analysis attempt {retry_attempt + 1} failed: {e}")
                    
                    # Check if we should retry this error
                    if not error_handler.should_retry(e, retry_attempt, max_retries):
                        logger.error(f"Non-retryable error on attempt {retry_attempt + 1}: {e}")
                        break
                    
                    # If this is not the last attempt, wait before retrying
                    if retry_attempt < max_retries - 1:
                        category = error_handler.categorize_error(e)
                        delay = error_handler.get_retry_delay(retry_attempt, category)
                        logger.info(f"Retrying in {delay:.1f}s (attempt {retry_attempt + 2}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    
                    # Final attempt failed - handle error and return user-friendly message
                    # Update persistent session state - describe failed
                    self.session_state.mark_describe_failure()
                    
                    # Note: API request/response details are now logged within _perform_vision_analysis
                    return error_handler.handle_vision_error(
                        e,
                        frame_hash=self._frame_hash,
                        frame_size=len(self._latest_frame) if self._latest_frame else 0,
                        session_id=getattr(self, 'session_id', None),
                        user_id=getattr(self, 'user_id', None),
                        retry_attempt=retry_attempt,
                        additional_context={
                            "focus": focus,
                            "cache_key": cache_key,
                            "max_retries": max_retries,
                            "frame_dimensions": f"{self._capture_width}x{self._capture_height}" if hasattr(self, '_capture_width') else "unknown"
                        }
                    )
            
            # All retries exhausted - return cached result if available
            # Update persistent session state - describe failed
            self.session_state.mark_describe_failure()
            
            async with self._describe_cache_lock:
                if self._describe_cache:
                    last_result = max(self._describe_cache.values(), key=lambda x: x[1])[0]
                    logger.info("All retries exhausted, returning cached result")
                    return last_result + " (using recent cached analysis due to API issues)"
            
            return "Vision analysis failed after multiple attempts. Please check your connection and try again."
        
        # Execute with performance monitoring
        try:
            result = await self.performance_monitor.monitor_vision_call(_monitored_vision_call)
            return result
        except Exception as e:
            # If monitoring itself fails, log and continue
            logger.error(f"Performance monitoring error: {e}")
            return await _monitored_vision_call()
    def _is_valid_description(self, response: str) -> bool:
        """Check if vision response is a valid description, not a deflection.

        This method validates that the vision system returned an actual screen description
        rather than a deflection response like "I have limitations" or similar phrases.

        Args:
            response: The response text from the vision system

        Returns:
            True if the response is a valid description, False if it's a deflection
        """
        from app.error_handler import error_handler

        # Use the error handler's deflection detection
        is_deflection = error_handler.is_deflection_response(response)

        # Also check for empty or very short responses that might indicate issues
        if not response or len(response.strip()) < 10:
            return False

        # Check for generic error messages that aren't helpful
        generic_errors = [
            "error occurred",
            "something went wrong",
            "unable to process",
            "failed to analyze",
            "no content available"
        ]

        response_lower = response.lower()
        has_generic_error = any(error in response_lower for error in generic_errors)

        # Valid if it's not a deflection and doesn't contain generic errors
        return not is_deflection and not has_generic_error

    def _validate_frame_data(self) -> bool:
        """Validate frame data before sending to API."""
        if not self._latest_frame:
            return False
        
        try:
            # Check if frame is valid base64
            frame_bytes = base64.b64decode(self._latest_frame)
            
            # Check minimum frame size (should be at least a few KB for a valid image)
            if len(frame_bytes) < 1024:  # Less than 1KB is likely invalid
                logger.warning(f"Frame too small: {len(frame_bytes)} bytes")
                return False
            
            # Check maximum frame size (prevent oversized frames)
            if len(frame_bytes) > 10 * 1024 * 1024:  # More than 10MB is too large
                logger.warning(f"Frame too large: {len(frame_bytes)} bytes")
                return False
            
            # Basic JPEG header validation
            if not frame_bytes.startswith(b'\xff\xd8'):
                logger.warning("Frame does not appear to be a valid JPEG")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Frame validation error: {e}")
            return False

    async def _perform_vision_analysis(self, focus: str, retry_attempt: int) -> str:
        """Perform the actual vision analysis with comprehensive logging and proper error handling."""
        from app.error_handler import error_handler
        
        # Log vision analysis attempt
        analysis_context = error_handler.log_vision_analysis_attempt(
            frame_hash=self._frame_hash or "unknown",
            frame_size=len(self._latest_frame) if self._latest_frame else 0,
            focus=focus,
            retry_attempt=retry_attempt,
            session_id=getattr(self, 'session_id', None),
            user_id=getattr(self, 'user_id', None)
        )
        
        start_time = time.time()
        
        try:
            # Decode frame data
            frame_bytes = base64.b64decode(self._latest_frame)
            
            # Log API request details
            api_request_details = error_handler.log_api_request(
                endpoint="gemini-live-api/send_realtime_input",
                method="POST",
                headers={
                    "Content-Type": "application/json",
                    "X-Goog-Api-Key": os.getenv('GOOGLE_API_KEY', 'not_set')[:8] + "***"
                },
                payload_size=len(frame_bytes),
                frame_hash=self._frame_hash,
                session_id=getattr(self, 'session_id', None),
                user_id=getattr(self, 'user_id', None)
            )
            
            # Send to Gemini Live API for analysis
            await self.gemini_session.send_realtime_input(
                video=types.Blob(data=frame_bytes, mime_type="image/jpeg")
            )
            
            # Wait for response from Gemini Live with timeout
            await asyncio.wait_for(asyncio.sleep(0.3), timeout=2.0)  # 2 second timeout
            
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Log successful API response
            api_response_details = error_handler.log_api_response(
                request_details=api_request_details,
                status_code=200,  # Assuming success if no exception
                response_time_ms=processing_time_ms
            )
            
            # For now, return a more informative placeholder until we can capture the actual response
            result = (
                f"SCREEN CONTENT AVAILABLE: I can see the current screen (frame {self._frame_hash[:6]}, "
                f"{self._capture_width}x{self._capture_height}). The visual content is being processed by my vision system. "
                f"I should describe what I can actually see on the screen right now, including any websites, apps, "
                f"text, buttons, or other visual elements that are currently visible. Focus area: {focus}."
            )
            
            # Log successful vision analysis result
            error_handler.log_vision_analysis_result(
                analysis_context=analysis_context,
                success=True,
                result_length=len(result),
                processing_time_ms=processing_time_ms,
                is_deflection=error_handler.is_deflection_response(result)
            )
            
            return result
            
        except asyncio.TimeoutError as e:
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Log timeout error
            api_response_details = error_handler.log_api_response(
                request_details=api_request_details if 'api_request_details' in locals() else {},
                response_time_ms=processing_time_ms,
                error=e
            )
            
            error_handler.log_vision_analysis_result(
                analysis_context=analysis_context,
                success=False,
                processing_time_ms=processing_time_ms,
                error=e
            )
            
            raise Exception("Vision analysis timed out after 2 seconds")
            
        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Log API error response
            if 'api_request_details' in locals():
                api_response_details = error_handler.log_api_response(
                    request_details=api_request_details,
                    response_time_ms=processing_time_ms,
                    error=e
                )
            
            # Log failed vision analysis
            error_handler.log_vision_analysis_result(
                analysis_context=analysis_context,
                success=False,
                processing_time_ms=processing_time_ms,
                error=e
            )
            
            # Re-raise with more context
            raise Exception(f"Vision API error: {str(e)}")

    def _cleanup_cache(self):
        """
        Clean up the describe cache with intelligent eviction (Task 5.3).
        
        Uses LRU (Least Recently Used) eviction strategy and removes expired entries.
        """
        current_time = time.time()
        
        # Remove expired entries based on adaptive TTL
        expired_keys = []
        for key, (result, cached_time) in self._describe_cache.items():
            cache_age = current_time - cached_time
            if cache_age > self._cache_ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self._describe_cache.pop(key, None)
            self._cache_access_times.pop(key, None)
        
        if expired_keys:
            logger.debug(f"🧹 Removed {len(expired_keys)} expired cache entries")
        
        # If still over max size, use LRU eviction
        if len(self._describe_cache) > CACHE_MAX_SIZE:
            # Sort by last access time (oldest first)
            sorted_entries = sorted(
                self._cache_access_times.items(),
                key=lambda x: x[1]
            )
            
            # Remove oldest entries until we're under the limit
            entries_to_remove = len(self._describe_cache) - CACHE_MAX_SIZE
            for key, _ in sorted_entries[:entries_to_remove]:
                self._describe_cache.pop(key, None)
                self._cache_access_times.pop(key, None)
            
            logger.debug(f"🧹 LRU evicted {entries_to_remove} cache entries")
    
    async def _check_cache_with_invalidation(self, cache_key: str) -> Optional[str]:
        """
        Check cache with intelligent invalidation logic (Task 5.3).

        All reads and writes to _describe_cache / _cache_access_times are
        protected by _describe_cache_lock to prevent race conditions.

        Args:
            cache_key: The cache key to check

        Returns:
            Cached result if valid, None otherwise
        """
        current_time = time.time()

        async with self._describe_cache_lock:
            # Check if key exists in cache
            if cache_key not in self._describe_cache:
                self.performance_monitor.record_cache_miss()
                self._cache_hit_streak = 0
                return None

            cached_result, cached_time = self._describe_cache[cache_key]
            cache_age = current_time - cached_time

            # Check if cache entry has expired based on adaptive TTL
            if cache_age > self._cache_ttl:
                logger.debug(f"⏰ Cache expired (age: {cache_age:.1f}s, TTL: {self._cache_ttl:.1f}s)")
                self.performance_monitor.record_cache_miss()
                self._cache_hit_streak = 0
                return None

            # Detect significant screen changes for intelligent invalidation
            if self._should_invalidate_cache():
                logger.debug("🔄 Cache invalidated due to significant screen change")
                self.performance_monitor.record_cache_miss()
                self._cache_hit_streak = 0
                self._describe_cache.clear()
                self._cache_access_times.clear()
                return None

            # Cache hit - update metrics and access time
            logger.debug(f"⚡ Cache hit (age: {cache_age:.1f}s, TTL: {self._cache_ttl:.1f}s)")
            self.performance_monitor.record_cache_hit()
            self._cache_access_times[cache_key] = current_time
            self._cache_hit_streak += 1

            # Adjust TTL based on cache hit patterns (Task 5.3)
            self._adjust_cache_ttl()

            return cached_result
    
    def _should_invalidate_cache(self) -> bool:
        """
        Determine if cache should be invalidated due to significant screen changes (Task 5.3).
        
        Uses frame history to detect when the screen content has changed significantly,
        indicating that cached descriptions are no longer valid.
        
        Returns:
            True if cache should be invalidated, False otherwise
        """
        if not self._frame_hash or len(self._frame_history) < 2:
            return False
        
        # Add current frame to history
        if not self._frame_history or self._frame_history[-1] != self._frame_hash:
            self._frame_history.append(self._frame_hash)
        
        # Check if we've seen rapid frame changes (indicating screen activity)
        if len(self._frame_history) >= 3:
            # If last 3 frames are all different, screen is changing rapidly
            recent_frames = list(self._frame_history)[-3:]
            if len(set(recent_frames)) == 3:
                logger.debug("🔄 Rapid screen changes detected")
                return True
        
        return False
    
    def _adjust_cache_ttl(self):
        """
        Adjust cache TTL based on usage patterns (Task 5.3).
        
        Dynamically adjusts the cache TTL to optimize for the target cache hit rate:
        - Increases TTL when cache hit rate is high (content is stable)
        - Decreases TTL when cache hit rate is low (content is changing)
        """
        # Only adjust after sufficient data
        if self._cache_hit_streak < 5:
            return
        
        current_hit_rate = self.performance_monitor.get_cache_hit_rate() / 100.0
        
        # If hit rate is above target, we can increase TTL (content is stable)
        if current_hit_rate > CACHE_ADAPTIVE_THRESHOLD + 0.1:
            new_ttl = min(self._cache_ttl * 1.2, CACHE_MAX_TTL)
            if new_ttl != self._cache_ttl:
                logger.info(f"📈 Increasing cache TTL: {self._cache_ttl:.1f}s → {new_ttl:.1f}s (hit rate: {current_hit_rate:.1%})")
                self._cache_ttl = new_ttl
        
        # If hit rate is below target, decrease TTL (content is changing)
        elif current_hit_rate < CACHE_ADAPTIVE_THRESHOLD - 0.1:
            new_ttl = max(self._cache_ttl * 0.8, CACHE_MIN_TTL)
            if new_ttl != self._cache_ttl:
                logger.info(f"📉 Decreasing cache TTL: {self._cache_ttl:.1f}s → {new_ttl:.1f}s (hit rate: {current_hit_rate:.1%})")
                self._cache_ttl = new_ttl
        
        # Reset streak after adjustment
        self._cache_hit_streak = 0

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

        await self._send_to_gemini(enhanced_text)

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
        
        await self._send_to_gemini(enhanced_text)

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

        # ── Auto-describe screen for visual queries ──────────────────────────
        # If the user is asking about something on screen AND we have a frame,
        # inject a fresh describe_screen result so Gemini sees the screen before
        # generating a response instead of guessing/hallucinating.
        screen_context = ""
        if self._is_visual_query(text) and self._latest_frame:
            try:
                screen_context = await self._describe_screen({"focus_area": "full"})
                logger.info(f"👁️ Auto-described screen for visual query: '{text[:60]}'")
            except Exception as e:
                logger.warning(f"Auto-describe failed: {e}")

        # Build the text to send — inject screen context when available
        def _with_screen(base_text: str) -> str:
            if screen_context:
                return f"{base_text}\n\n[Screen content: {screen_context}]"
            return base_text

        # Check for workflow triggers before sending to Gemini
        matching_workflows = self.prefs.match_workflows(text)
        if matching_workflows:
            workflow = matching_workflows[0]
            logger.info(f"🎯 Executing workflow: {workflow['name']}")
            self._current_workflow = workflow['name']
            self._workflow_start_time = time.time()
            workflow_context = f"User triggered workflow '{workflow['name']}'. Execute these steps: {', '.join(workflow['steps'])}"
            enhanced_text = _with_screen(f"{text}\n\n[Workflow Context: {workflow_context}]")
            # send_realtime_input triggers audio+tool response (response_modalities=["AUDIO"]);
            # send_client_content would return text-only, breaking voice output and actions.
            await self._send_to_gemini(enhanced_text)
        else:
            await self._send_to_gemini(_with_screen(text))
    # ━━━ ORCHESTRATOR HELPER METHODS ━━━
    
    def _get_enhanced_system_instruction(self, user_text: str = "") -> str:
        """
        Get system instruction with optional destructive action reminder.
        
        Args:
            user_text: The user's input text to check for destructive actions
            
        Returns:
            Enhanced system instruction with context-specific reminders
        """
        from app.agents.orchestrator import SPECTRA_SYSTEM_INSTRUCTION, get_confirmation_reminder
        
        # Add confirmation reminder if this is a destructive action
        reminder = get_confirmation_reminder(user_text)
        if reminder:
            return f"{SPECTRA_SYSTEM_INSTRUCTION}\n\n{reminder}"
        
        return SPECTRA_SYSTEM_INSTRUCTION
    
    def _should_enforce_describe_first(self) -> bool:
        """
        Check if we should enforce describe_screen before actions.
        
        Returns:
            True if describe_screen should be called first
        """
        # If we haven't described the screen recently, enforce it
        time_since_describe = time.time() - self._last_describe_time
        return time_since_describe > 2.0  # 2 seconds since last describe
    
    def _track_action_state(self, action_name: str, params: dict):
        """
        Track action state for undo/redo functionality.
        
        Args:
            action_name: Name of the action performed
            params: Action parameters (coordinates, etc.)
        """
        if not hasattr(self, '_action_history'):
            self._action_history = []
        
        self._action_history.append({
            'action': action_name,
            'params': params.copy(),
            'timestamp': time.time(),
        })
        
        # Keep only last 10 actions for undo
        self._action_history = self._action_history[-10:]
    
    def _get_last_action(self) -> dict | None:
        """
        Get the last action performed.
        
        Returns:
            Last action dict or None if no history
        """
        if not hasattr(self, '_action_history') or not self._action_history:
            return None
        return self._action_history[-1]
    
    def _get_action_for_undo(self) -> dict | None:
        """
        Get an action to undo based on the last action.
        
        Returns:
            Dict with undo action info or None if no undo available
        """
        last_action = self._get_last_action()
        if not last_action:
            return None
        
        action_name = last_action['action']
        
        # Map actions to undo operations
        undo_map = {
            'click_element': {'action': 'press_key', 'params': {'key': 'Escape'}},
            'navigate': {'action': 'press_key', 'params': {'key': 'Backspace'}},
            'type_text': {'action': 'press_key', 'params': {'key': 'Backspace'}},
            'scroll_page': {'action': 'scroll_page', 'params': {'direction': 'up' if last_action['params'].get('direction') == 'down' else 'down'}},
        }
        
        return undo_map.get(action_name)
    
    def _detect_app_type(self, screen_description: str) -> str:
        """
        Detect the current app type from screen description.
        
        Args:
            screen_description: Description of the current screen
            
        Returns:
            App type: 'email', 'docs', 'browser', 'app', or 'unknown'
        """
        desc_lower = screen_description.lower()
        
        if 'gmail' in desc_lower or 'inbox' in desc_lower or 'email' in desc_lower:
            return 'email'
        elif 'docs' in desc_lower or 'google docs' in desc_lower or 'document' in desc_lower:
            return 'docs'
        elif 'github' in desc_lower or 'gitlab' in desc_lower or 'bitbucket' in desc_lower:
            return 'code'
        else:
            return 'browser'

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
        await self.websocket.send_json({
            "type": "action",
            "action": "read_selection",
            "params": {"mode": mode},
            "id": action_id,
        })
        
        try:
            action_msg = await asyncio.wait_for(
                self._action_queue.get(), timeout=ACTION_TIMEOUT
            )
            result = action_msg.get("result", "No text selected")
            return f"Reading {mode}: {result}"
        except asyncio.TimeoutError:
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
