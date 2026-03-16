"""Configuration management for Spectra orchestrator."""

import os
from typing import Final

# ━━━ FILE PATHS ━━━
INTERACTION_LOG_PATH: Final[str] = os.getenv(
    "SPECTRA_INTERACTION_LOG_PATH", 
    "logs/spectra_traces.jsonl"
)

# ━━━ TIMING CONFIGURATION ━━━
SCREEN_CONTEXT_MAX_AGE_SECONDS: Final[int] = int(
    os.getenv("SPECTRA_SCREEN_CONTEXT_MAX_AGE", "5")
)

# ━━━ REGEX PATTERN CONFIGURATION ━━━
ENABLE_AGGRESSIVE_NARRATION_FILTER: Final[bool] = (
    os.getenv("SPECTRA_AGGRESSIVE_NARRATION_FILTER", "true").lower() == "true"
)

# ━━━ LOGGING CONFIGURATION ━━━
LOG_INTERACTIONS: Final[bool] = (
    os.getenv("SPECTRA_LOG_INTERACTIONS", "true").lower() == "true"
)

MAX_LOG_FILE_SIZE_MB: Final[int] = int(
    os.getenv("SPECTRA_MAX_LOG_FILE_SIZE_MB", "100")
)

# ━━━ VALIDATION CONFIGURATION ━━━
STRICT_VALIDATION: Final[bool] = (
    os.getenv("SPECTRA_STRICT_VALIDATION", "false").lower() == "true"
)

# ━━━ DESTRUCTIVE ACTION KEYWORDS ━━━
DESTRUCTIVE_KEYWORDS: Final[list[str]] = [
    # Data loss — irreversible
    "delete", "remove", "destroy", "erase", "purge",
    # Financial — irreversible
    "purchase", "buy", "pay", "checkout", "order",
    # Account / legal — high stakes
    "terminate", "legal", "financial", "bank", "credit",
    "hr", "human resources", "personnel",
    # NOTE: "send", "email", "submit", "post", "cancel", "close" intentionally
    # removed — they are too broad and cause double-confirm UX during normal flows
    # (e.g. user says "send it" as confirmation → orchestrator fires reminder again).
    # Gemini handles email send confirmation contextually via the confirm_action tool.
]

# ━━━ VISION ERROR CLASSIFICATION ━━━
VISION_ERROR_TYPES: Final[dict[str, list[str]]] = {
    'authentication': [r'401', r'invalid.*api.*key', r'unauthorized', r'api.?key'],
    'rate_limit': [r'429', r'rate limit', r'quota', r'exceeded'],
    'timeout': [r'timeout', r'timed out', r'deadline', r'connection timed out'],
    'network': [r'connection', r'network', r'dns', r'reachable', r'offline'],
    'frame_invalid': [r'invalid.*frame', r'empty.*frame', r'no.*screen', r'capture'],
    'api_error': [r'gemini.*api', r'api.*error', r'server.*error'],
}

# ━━━ FORBIDDEN SENTENCE STARTS ━━━
# Only clearly internal-monologue patterns. Avoid short prefixes like "i'm now"
# that would also match normal speech ("I'm now on the homepage").
FORBIDDEN_SENTENCE_STARTS: Final[list[str]] = [
    "currently, i am analyzing", "right now, i am analyzing",
    "to accomplish this, i will", "this initial step involves",
    "my next step is to analyze", "i've decided to analyze",
    "first, i will analyze", "before i can help, i need",
    "i've begun analyzing", "i've initiated the",
    "i've detailed the elements", "i've pinpointed the",
    "i'm currently analyzing", "i'm currently examining",
    "i'm focusing on the elements", "i'm concentrating on the",
    "my focus is on analyzing", "my analysis of the screen",
    "my plan is to analyze", "my goal is to determine",
    "i need to understand the layout", "i need to figure out the",
    "looking at the screen description", "based on what i see in the description",
    "detailing the elements", "analyzing the screen description",
    "examining the elements", "i'm zeroing in on",
    "i've now analyzed the", "the user input appears",
    "the previous attempt to", "a fresh screen description",
    "its coordinates are", "once i understand the",
]
