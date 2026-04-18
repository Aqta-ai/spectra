"""Ollama streaming session — text-based conversational AI via local Gemma 4."""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.agents.orchestrator import (
    SPECTRA_TOOLS,
    postprocess_spectra_reply,
    remove_narration,
)
from app.agents.system_instruction import SPECTRA_SYSTEM_INSTRUCTION
from app.streaming.ollama_client import OllamaClient
from app.memory import SpectraMemory
from app.performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)


class OllamaStreamingSession:
    """Manage a local text-based session via Ollama (Gemma 4)."""

    def __init__(self, websocket: WebSocket, user_id: str = "default", session_id: str = None):
        self.websocket = websocket
        self.user_id = user_id
        self.session_id = session_id or str(uuid.uuid4())

        # Ollama client
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        ollama_model = os.getenv("OLLAMA_MODEL", "gemma4")
        self.ollama = OllamaClient(base_url=ollama_url, model=ollama_model)

        # Session state
        self._running = False
        self._client_disconnected = False
        self._message_history: list[dict] = []  # conversation history for Ollama
        self._session_start = time.time()
        self._last_activity = time.time()

        # Memory system
        self.memory = SpectraMemory(user_id)

        # Performance monitor
        self.performance_monitor = get_performance_monitor()

        # Tool state
        self._extension_available = False
        self._current_url = ""
        self._latest_frame: str | None = None

        logger.info(f"[Ollama] Session {self.session_id} initialized (user: {user_id}, model: {ollama_model})")

    async def run(self):
        """Main session loop: listen for client messages and respond via Ollama."""
        self._running = True
        try:
            await self._listen_client()
        except WebSocketDisconnect:
            logger.info(f"[Ollama] Client disconnected: {self.session_id}")
        except Exception as e:
            logger.error(f"[Ollama] Session error [{self.session_id}]: {e}", exc_info=True)
            try:
                await self.websocket.close(code=1011, reason=str(e)[:120])
            except Exception:
                pass
        finally:
            self._client_disconnected = True
            await self.cleanup()

    async def _listen_client(self):
        """Listen for messages from the browser WebSocket."""
        while not self._client_disconnected:
            try:
                data = await self.websocket.receive_json()
                await self._handle_client_message(data)
                self._last_activity = time.time()
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"[Ollama] Invalid JSON from client")
            except Exception as e:
                logger.error(f"[Ollama] Error handling client message: {e}")
                await asyncio.sleep(0.1)

    async def _handle_client_message(self, data: dict):
        """Handle incoming message from browser."""
        msg_type = data.get("type", "")

        if msg_type == "text":
            # User sent a text message
            text = data.get("text", "").strip()
            if text:
                await self._process_user_message(text)

        elif msg_type == "screenshot":
            # Store latest screenshot for context
            self._latest_frame = data.get("data", "")

        elif msg_type == "extension_status":
            # Browser extension status
            self._extension_available = data.get("available", False)
            status = "installed" if self._extension_available else "NOT installed"
            logger.info(f"[Ollama] Extension status: {status}")

        elif msg_type == "action_result":
            # Tool execution result from browser
            action_id = data.get("action_id", "")
            result = data.get("result", "")
            logger.debug(f"[Ollama] Action {action_id} result: {result}")

        elif msg_type == "current_url":
            # Update current URL context
            self._current_url = data.get("url", "")

    async def _process_user_message(self, user_text: str):
        """Process user message, send to Ollama, handle response."""
        try:
            # Add user message to history
            self._message_history.append({"role": "user", "content": user_text})

            # Keep history manageable (last 20 turns)
            if len(self._message_history) > 40:
                self._message_history = self._message_history[-40:]

            # Send to Ollama and stream response with retry logic
            logger.info(f"[Ollama] Processing: {user_text[:100]}...")
            response_text = ""

            # Retry up to 2 times on stream error (Ollama may be restarting)
            for attempt in range(1, 3):
                try:
                    chunk_count = 0
                    async for chunk in self.ollama.generate_stream(
                        system=SPECTRA_SYSTEM_INSTRUCTION,
                        messages=self._message_history,
                    ):
                        chunk_count += 1
                        if chunk.get("error"):
                            error_msg = chunk.get("error")
                            logger.error(f"[Ollama] Generation error (attempt {attempt}): {error_msg}")
                            # If first attempt failed, retry once
                            if attempt < 2 and "connection" in str(error_msg).lower():
                                logger.info(f"[Ollama] Retrying after connection error...")
                                await asyncio.sleep(1)
                                break  # Break inner loop to retry
                            else:
                                # Permanent error or second attempt failed
                                await self.websocket.send_json({
                                    "type": "error",
                                    "error": f"Generation failed: {error_msg}",
                                })
                                return

                        text_chunk = chunk.get("text", "")
                        if text_chunk:
                            # Accumulate response
                            response_text += text_chunk
                            logger.debug(f"[Ollama] Chunk {chunk_count}: {repr(text_chunk[:50])}")

                            # Send chunk to client (stream incrementally)
                            try:
                                await self.websocket.send_json({
                                    "type": "transcript",
                                    "text": text_chunk,
                                    "final": False,
                                })
                            except Exception as e:
                                logger.error(f"[Ollama] Failed to send chunk to client: {e}")
                                break

                        if chunk.get("done"):
                            logger.info(f"[Ollama] Generation complete ({chunk_count} chunks, {len(response_text)} chars)")
                            # Final cleanup and store in history
                            response_text = remove_narration(response_text)
                            response_text = postprocess_spectra_reply(response_text)
                            self._message_history.append({"role": "assistant", "content": response_text})

                            # Send final marker
                            try:
                                await self.websocket.send_json({
                                    "type": "transcript",
                                    "text": "",
                                    "final": True,
                                })
                            except Exception as e:
                                logger.error(f"[Ollama] Failed to send final marker: {e}")

                            logger.debug(f"[Ollama] Response: {response_text[:100]}...")
                            return  # Success — exit retry loop
                except Exception as e:
                    # Connection error — try again
                    if attempt < 2 and isinstance(e, (ConnectionError, asyncio.TimeoutError)):
                        logger.warning(f"[Ollama] Connection error on attempt {attempt}, retrying...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        # Permanent error or last attempt failed
                        logger.error(f"[Ollama] Error processing message (attempt {attempt}): {e}", exc_info=True)
            await self.websocket.send_json({
                "type": "error",
                "error": str(e),
            })


    async def cleanup(self):
        """Clean up session resources."""
        self._running = False
        duration = time.time() - self._session_start
        logger.info(f"[Ollama] Session cleaned up: {self.session_id} (duration: {duration:.1f}s, messages: {len(self._message_history)})")
