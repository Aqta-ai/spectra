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
FORBIDDEN_SENTENCE_STARTS: Final[list[str]] = [
    "currently, i", "right now, i", "to accomplish this, i",
    "this initial step", "my next step", "i've decided to",
    "i will now", "first, i will", "before i can help",
    "i've begun", "i've initiated", "i've detailed", "i've pinpointed",
    "i've completed", "i'm now", "i'm currently", "i'm focusing",
    "my focus is", "my analysis", "my plan is", "my goal is",
    "let me now", "let me begin", "let me start",
    "i need to understand", "i need to figure out", "i need to determine",
    "looking at the screen", "based on what i see",
    "this will allow", "this step is", "this is essential",
    # Additional patterns from recent violations
    "i've identified", "i've noted", "i've registered", "i've examined",
    "i'm zeroing", "i'm concentrating", "i'm noting",
    "detailing the", "analyzing the", "examining the",
    # New patterns from the screenshot
    "i'm puzzled", "i'm viewing", "i'm still trying", "i plan to",
    "i've now analyzed", "the user input", "appears incomplete",
    "lacks context", "remains ambiguous",
    # Inner-thought verbs seen leaking through
    "i'm verifying", "i'm revisiting", "i'm re-examining", "i'm re-analyzing",
    "i'm exploring", "i'm retrying", "i'm prepared to", "i'm re-",
    "i'll target", "i'll retry", "i'll re-", "my next action",
    "the previous attempt", "a fresh screen", "its coordinates are",
    "i've re-analyzed", "i've re-examined", "i've re-identified",
    "once i understand", "once i have",
]
