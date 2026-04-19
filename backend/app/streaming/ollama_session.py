"""Spectra streaming session for Ollama (offline Gemma 4 mode)."""

import asyncio
import base64
import json
import logging
import os
import re
import time
import uuid
from collections import deque
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from app.agents.orchestrator import (
    postprocess_spectra_reply,
    remove_narration,
)
from app.memory import SpectraMemory
from app.streaming.ollama_client import OllamaClient
from app.streaming.session_manager import get_session_manager, SessionState
from app.performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)

# System instruction for Ollama (text-only, conversational)
OLLAMA_SYSTEM_INSTRUCTION = """You are Spectra, an intelligent accessibility agent that helps users control and interact with their browser through conversation. You understand natural language commands and execute browser actions like clicking, typing, navigating, and reading screen content.

KEY PRINCIPLES:
1. Be conversational and helpful — respond naturally to user requests
2. When the user asks you to do something, break it down into clear steps
3. Always confirm what you're about to do before taking destructive actions
4. If something fails, explain the issue clearly and suggest alternatives
5. Provide context about what you're doing and what you see on screen

IMPORTANT RULES:
- Never make up information about what's on screen — always use describe_screen first
- Be concise and direct in responses
- Focus on helping the user accomplish their goal
- If you need more information about the current screen state, ask describe_screen
- Provide step-by-step guidance for complex tasks

PERSONALITY:
- Helpful and patient
- Clear and concise communication
- Problem-solver mindset
- Respectful of user intent"""

# Configuration
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
ACTION_TIMEOUT = float(os.getenv("ACTION_TIMEOUT", "12.0"))
HEARTBEAT_INTERVAL = float(os.getenv("HEARTBEAT_INTERVAL", "3.0"))
FRAME_COOLDOWN = float(os.getenv("FRAME_COOLDOWN", "1.0"))

# Actions that Ollama can request
SUPPORTED_ACTIONS = {
    "describe_screen",
    "click_element",
    "type_text",
    "scroll_page",
    "press_key",
    "navigate",
    "wait_for_content",
    "save_snapshot",
    "diff_screen",
    "teach_me_app",
    "read_selection",
    "read_page_structure",
    "confirm_action",
    "highlight_element",
}


class OllamaStreamingSession:
    """WebSocket session handler for Ollama-based offline conversations."""

    def __init__(self, websocket: WebSocket, user_id: str, session_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.session_id = session_id

        # Session state
        self.is_running = True
        self.memory = SpectraMemory(user_id=user_id)
        self.ollama_client = OllamaClient(
            base_url=OLLAMA_BASE_URL,
            model=OLLAMA_MODEL,
        )

        # Conversation history
        self.messages: list[dict] = []
        self.max_history = 20  # Keep last 20 messages

        # Frame/screenshot tracking
        self.last_screenshot: Optional[bytes] = None
        self.last_screenshot_time = 0
        self.screenshot_queue: deque = deque(maxlen=3)

        # Timing
        self.session_start = time.time()
        self.last_heartbeat = time.time()
        self.last_describe_time = 0

        # Action handling
        self.pending_action: Optional[dict] = None
        self.action_in_progress = False

        # Session manager
        self.session_manager = get_session_manager()
        self.session_state = self.session_manager.get_or_create_session(session_id, user_id)

        logger.info(
            f"OllamaStreamingSession initialized: {session_id} (user: {user_id})"
        )

    async def run(self):
        """Main session loop — receive messages and process them."""
        logger.info(f"Starting Ollama session: {self.session_id}")
        try:
            while self.is_running:
                try:
                    # Receive message from client with timeout
                    logger.debug("Waiting for message...")
                    message_data = await asyncio.wait_for(
                        self.websocket.receive_json(),
                        timeout=HEARTBEAT_INTERVAL + 2,
                    )

                    # Process incoming message
                    await self._process_message(message_data)

                except asyncio.TimeoutError:
                    logger.debug("Timeout, sending heartbeat")
                    # Send heartbeat to keep connection alive
                    await self._send_heartbeat()
                    continue
                except WebSocketDisconnect:
                    logger.info(f"Client disconnected: {self.session_id}")
                    break

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: {self.session_id}")
        except Exception as e:
            logger.error(
                f"Session error [{self.session_id}]: {e}", exc_info=True
            )
        finally:
            logger.info(f"Cleaning up session: {self.session_id}")
            await self.cleanup()

    async def _process_message(self, message_data: dict):
        """Process incoming message from client."""
        try:
            msg_type = message_data.get("type", "").lower()
            logger.debug(f"Processing message type: {msg_type}")

            if msg_type == "text":
                # User sent text message
                text = message_data.get("text", "").strip()
                if text:
                    logger.info(f"User message: {text[:100]}")
                    await self._handle_text_message(text)

            elif msg_type == "screenshot":
                # Client sent a screenshot
                screenshot_data = message_data.get("data", "")
                if screenshot_data:
                    await self._handle_screenshot(screenshot_data)

            elif msg_type == "action_result":
                # Browser action completed, send result back to model
                action_name = message_data.get("action", "")
                result = message_data.get("result", "")
                await self._handle_action_result(action_name, result)

            else:
                logger.warning(
                    f"Unknown message type: {msg_type}"
                )

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self._send_error(str(e))

    async def _handle_text_message(self, text: str):
        """Handle user text input."""
        # Add to conversation history
        self.messages.append({"role": "user", "content": text})

        # Truncate history if too long
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history :]

        # Send to Ollama and get response
        await self._send_to_ollama()

    async def _handle_screenshot(self, screenshot_b64: str):
        """Handle incoming screenshot from client."""
        try:
            # Store screenshot for context
            self.last_screenshot = base64.b64decode(screenshot_b64)
            self.last_screenshot_time = time.time()
            self.screenshot_queue.append(self.last_screenshot)

            # Update session state
            if self.session_state:
                self.session_state.mark_frame_received()

        except Exception as e:
            logger.warning(f"Failed to process screenshot: {e}")

    async def _handle_action_result(self, action_name: str, result: str):
        """Handle result from browser action execution."""
        # Translate action result to natural language
        translated = self._translate_action_result(action_name, result)

        # Add to conversation
        self.messages.append(
            {"role": "assistant", "content": f"[Executed {action_name}]"}
        )
        self.messages.append(
            {"role": "user", "content": f"Action result: {translated}"}
        )

        # Continue conversation with updated context
        await self._send_to_ollama()

    async def _send_to_ollama(self):
        """Send conversation to Ollama and stream response."""
        if self.action_in_progress:
            return  # Don't send while waiting for action result

        try:
            self.action_in_progress = True
            response_text = ""
            logger.info("Sending to Ollama...")

            # Stream response from Ollama
            async for chunk in self.ollama_client.generate_stream(
                system=OLLAMA_SYSTEM_INSTRUCTION,
                messages=self.messages,
            ):
                response_text += chunk
                # Don't send partial chunks yet — accumulate for parsing

            logger.info(f"Received response from Ollama ({len(response_text)} chars)")

            # Post-process response
            response_text = remove_narration(response_text)
            response_text = postprocess_spectra_reply(response_text)

            # Add assistant response to history
            self.messages.append({"role": "assistant", "content": response_text})

            # Parse for action requests
            actions = self._parse_actions_from_response(response_text)

            if actions:
                logger.info(f"Parsed {len(actions)} action(s)")
                # Send first action to browser
                for action in actions[:1]:  # Execute one action at a time
                    await self._send_action(action)
                    break
            else:
                # No actions — send text response to user
                logger.info(f"Sending text response: {response_text[:100]}...")
                await self._send_text(response_text)

            self.action_in_progress = False

        except Exception as e:
            logger.error(f"Error in Ollama communication: {e}", exc_info=True)
            self.action_in_progress = False
            await self._send_error(f"Error: {str(e)}")

    def _parse_actions_from_response(self, response: str) -> list[dict]:
        """Parse action requests from Ollama response.

        For now, Ollama responses are pure text only.
        Structured action parsing could be added later with tool definitions.
        """
        # Text-only mode: no structured action parsing yet
        return []

    async def _send_action(self, action: dict):
        """Send action to browser for execution."""
        self.pending_action = action

        await self.websocket.send_json(
            {
                "type": "action",
                "action": action.get("name"),
                "params": action.get("params", {}),
            }
        )

    async def _send_text(self, text: str):
        """Send text response to client."""
        try:
            await self.websocket.send_json({"type": "text", "text": text})
        except Exception as e:
            logger.error(f"Failed to send text: {e}")
            raise

    async def _send_error(self, error_message: str):
        """Send error message to client."""
        await self.websocket.send_json(
            {"type": "error", "message": error_message}
        )

    async def _send_heartbeat(self):
        """Send heartbeat to keep connection alive."""
        current_time = time.time()
        if current_time - self.last_heartbeat > HEARTBEAT_INTERVAL:
            try:
                await self.websocket.send_json({"type": "heartbeat"})
                self.last_heartbeat = current_time
            except Exception as e:
                logger.warning(f"Failed to send heartbeat: {e}")

    def _translate_action_result(self, action: str, result: str) -> str:
        """Translate raw action result codes into natural language."""
        if not isinstance(result, str):
            return str(result)

        r = result.strip()
        rl = r.lower()

        # Failures — pass through as-is
        if any(
            rl.startswith(p)
            for p in (
                "error",
                "fail",
                "timeout",
                "no_element",
                "extension",
                "invalid",
            )
        ):
            return r

        # Navigate
        if rl.startswith("navigated_to_"):
            url = r[len("navigated_to_") :]
            url = url.replace("\n", " ").replace("\r", " ").strip()[:200]
            return f"Navigated to: {url}"

        # Click
        if rl.startswith("clicked_"):
            suffix = r[len("clicked_") :]
            if suffix.lower().startswith("by_label_"):
                suffix = suffix[len("by_label_") :]
            parts = suffix.split("_", 1)
            label = parts[1] if len(parts) > 1 else parts[0]
            label = label.replace("_", " ").strip()
            if label:
                return f"Clicked '{label}'."
            return "Clicked."

        # Type
        if rl.startswith("typed_into_"):
            field = r[len("typed_into_") :].replace("_", " ")
            return f"Typed into {field}."

        # Scroll
        if "reached_bottom" in rl:
            return "Scrolled to bottom."
        if "reached_top" in rl:
            return "Scrolled to top."
        if rl.startswith("scrolled_"):
            return "Scrolled."

        # Key press
        if rl.startswith("pressed_"):
            key = r[len("pressed_") :].replace("_", "+")
            return f"Pressed: {key}."

        return r

    async def cleanup(self):
        """Clean up session resources."""
        self.is_running = False
        self.session_manager.remove_session(self.session_id)
        logger.debug(f"Session cleaned up: {self.session_id}")
