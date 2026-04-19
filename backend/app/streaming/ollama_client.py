"""Ollama HTTP client for streaming text generation with tool support."""

import asyncio
import json
import logging
from typing import AsyncIterator, Optional
import httpx

logger = logging.getLogger(__name__)


class OllamaClient:
    """Wrapper for Ollama /api/generate endpoint with streaming support."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model: str = "gemma4",
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def generate_stream(
        self,
        system: str,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> AsyncIterator[str]:
        """Stream text generation from Ollama.

        Args:
            system: System prompt/instructions
            messages: Conversation history [{"role": "user"|"assistant", "content": str}]
            tools: Tool definitions (not yet supported, for future expansion)
            temperature: Sampling temperature (0.0-2.0)
            top_p: Nucleus sampling parameter (0.0-1.0)

        Yields:
            Streamed response text chunks
        """
        # Build prompt from messages
        prompt = self._build_prompt(system, messages)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "temperature": temperature,
            "top_p": top_p,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(
                            f"Ollama API error {response.status_code}: {error_text}"
                        )
                        raise RuntimeError(
                            f"Ollama API error: {response.status_code}"
                        )

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse Ollama response: {line}")
                            continue
        except httpx.ConnectError:
            logger.error(f"Failed to connect to Ollama at {self.base_url}")
            raise RuntimeError("Failed to connect to Ollama server")
        except asyncio.TimeoutError:
            logger.error("Ollama request timeout")
            raise RuntimeError("Ollama request timeout")

    def _build_prompt(self, system: str, messages: list[dict]) -> str:
        """Build a single prompt string from system instruction and message history.

        Format:
        {system}

        {user message 1}
        {assistant response 1}
        {user message 2}
        """
        lines = [system.strip(), ""]

        for msg in messages:
            role = msg.get("role", "").lower()
            content = msg.get("content", "").strip()

            if role == "user":
                lines.append(content)
            elif role == "assistant":
                lines.append(content)

        return "\n".join(lines)

    async def check_connection(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama connection check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """List available models on Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
        return []
