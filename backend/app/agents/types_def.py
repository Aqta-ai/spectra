"""Type definitions for Spectra orchestrator."""

from typing import TypedDict, Literal, Optional, Any


class VisionErrorResult(TypedDict):
    """Result of vision error classification."""
    type: str
    user_message: str
    should_retry: bool


class ValidationResult(TypedDict):
    """Result of system instruction validation."""
    is_valid: bool
    violations: list[str]


class ToolCall(TypedDict):
    """Represents a tool call in interaction log."""
    name: str
    args: dict[str, Any]


class InteractionTrace(TypedDict):
    """Complete interaction trace for logging."""
    timestamp: float
    user: str
    tool_calls: list[ToolCall]
    response: str
    violations: list[str]
    quality: str


class DatasetStats(TypedDict):
    """Statistics about the training dataset."""
    total_interactions: int
    good_quality: int
    needs_review: int
    unique_tools: int
