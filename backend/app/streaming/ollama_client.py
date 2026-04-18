"""Ollama HTTP client for local LLM inference via Gemma 4."""

import asyncio
import httpx
import json
import logging
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)


class OllamaClient:
    """HTTP client for Ollama /api/generate streaming endpoint."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "gemma4"):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = httpx.Timeout(600.0)  # 10 min timeout for long generations

    async def check_health(self) -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False

    async def generate_stream(
        self,
        system: str,
        messages: list[dict],
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> AsyncIterator[dict]:
        """
        Stream text generation from Ollama.

        Args:
            system: System prompt/instructions
            messages: List of messages in format [{"role": "user"|"assistant", "content": "..."}]
            temperature: Sampling temperature (0.0-1.0)
            top_p: Nucleus sampling parameter

        Yields:
            Dict with keys:
            - "text": Generated text chunk (str)
            - "done": True if generation complete (bool)
        """
        # Build conversation context
        prompt = self._build_prompt(system, messages)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "temperature": temperature,
            "top_p": top_p,
            "stop": ["User:", "Assistant:", "<|im_end|>"],  # Common stop tokens
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
                        logger.error(f"Ollama error {response.status_code}: {error_text}")
                        yield {"text": "", "done": True, "error": f"HTTP {response.status_code}"}
                        return

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield {
                                    "text": data.get("response", ""),
                                    "done": data.get("done", False),
                                }
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse Ollama response: {line}")
                            continue

        except asyncio.CancelledError:
            logger.info("Ollama generation cancelled")
            yield {"text": "", "done": True, "cancelled": True}
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            yield {"text": "", "done": True, "error": str(e)}

    def _build_prompt(self, system: str, messages: list[dict]) -> str:
        """
        Build a prompt string from system instruction and message history.
        Gemma format: <start_of_turn>user\n{text}<end_of_turn>\n<start_of_turn>model
        """
        parts = []

        # Add system instruction
        if system:
            parts.append(f"<start_of_turn>system\n{system}<end_of_turn>\n")

        # Add message history
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"<start_of_turn>{role}\n{content}<end_of_turn>\n")

        # Start model's turn
        parts.append("<start_of_turn>model\n")

        return "".join(parts)

    async def chat_completion(
        self,
        system: str,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> str:
        """
        Get a single non-streaming response from Ollama.

        Returns:
            Complete generated text
        """
        full_response = ""
        async for chunk in self.generate_stream(
            system=system,
            messages=messages,
            temperature=temperature,
        ):
            full_response += chunk.get("text", "")
            if chunk.get("error"):
                logger.error(f"Error during generation: {chunk['error']}")
                break

        return full_response.strip()

    def convert_gemini_tools_to_schema(self, gemini_tools: list) -> str:
        """
        Convert Gemini FunctionDeclaration format to JSON schema string
        for Ollama to understand as available tools.

        Gemini format: {
            "name": "click_element",
            "description": "Click an element on the screen",
            "parameters": {"properties": {...}, "required": [...]}
        }

        Returns a formatted schema string that can be included in system prompt.
        """
        if not gemini_tools:
            return ""

        schema_lines = ["Available tools:"]
        for tool in gemini_tools:
            name = tool.get("name", "unknown")
            description = tool.get("description", "")
            params = tool.get("parameters", {}).get("properties", {})

            schema_lines.append(f"\n1. {name} - {description}")

            if params:
                schema_lines.append("   Parameters:")
                for param_name, param_schema in params.items():
                    param_desc = param_schema.get("description", "")
                    param_type = param_schema.get("type", "string")
                    schema_lines.append(f"   - {param_name} ({param_type}): {param_desc}")

        return "\n".join(schema_lines)

    async def detect_tool_call(self, text: str) -> Optional[dict]:
        """
        Detect if text contains a tool call in Ollama's format.

        For MVP, we look for tool calls in the format:
        TOOL: tool_name(arg1=value1, arg2=value2)

        Returns:
            {
                "tool": "tool_name",
                "args": {"arg1": "value1", "arg2": "value2"}
            }
            or None if no tool call detected.
        """
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("TOOL:"):
                # Parse: TOOL: click_element(x=100, y=200)
                tool_part = line[len("TOOL:"):].strip()
                try:
                    # Extract tool name and args
                    paren_idx = tool_part.find("(")
                    if paren_idx > 0:
                        tool_name = tool_part[:paren_idx]
                        args_str = tool_part[paren_idx + 1 : -1]  # Remove parens

                        # Parse args: x=100, y=200
                        args = {}
                        for arg_pair in args_str.split(","):
                            if "=" in arg_pair:
                                key, val = arg_pair.split("=", 1)
                                args[key.strip()] = val.strip().strip('"\'')

                        return {"tool": tool_name, "args": args}
                except Exception as e:
                    logger.warning(f"Failed to parse tool call '{line}': {e}")

        return None
