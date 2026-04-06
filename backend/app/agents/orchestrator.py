"""Spectra orchestrator — optimised system instruction and tool declarations for Gemini Live API."""

import re
import os
import time
import json
import logging
from typing import Optional, Any
from google.genai import types

# Modular imports (refactored)
from app.agents.config import (
    INTERACTION_LOG_PATH,
    SCREEN_CONTEXT_MAX_AGE_SECONDS,
    DESTRUCTIVE_KEYWORDS,
    VISION_ERROR_TYPES,
    FORBIDDEN_SENTENCE_STARTS,
    LOG_INTERACTIONS,
    MAX_LOG_FILE_SIZE_MB,
)
from app.agents.system_instruction import (
    SPECTRA_SYSTEM_INSTRUCTION,
    build_system_instruction,
    EXAMPLES,
)
from app.agents.types_def import (
    VisionErrorResult,
    ValidationResult,
    ToolCall,
    InteractionTrace,
    DatasetStats,
)
from app.agents.metrics import (
    structured_logger,
    metrics,
    OrchestratorMetrics,
    track_performance,
    track_operation,
)

logger = logging.getLogger(__name__)

# System instruction now imported from system_instruction.py
# SPECTRA_SYSTEM_INSTRUCTION is imported at the top of this file

# ---------------------------------------------------------------------------
# Narration filtering — NO regex on sentence bodies (ReDoS-safe).
# All sentence-level filtering is done via plain substring lookup on the
# lowercased sentence.  Only the two bold-header patterns (which match a
# fixed prefix/suffix, not an unbounded body) are kept as compiled regex.
# ---------------------------------------------------------------------------

# Forbidden substrings — only match clear inner-monologue / process narration.
# IMPORTANT: Keep these specific enough that they don't match normal conversational
# responses. E.g. "i'm seeing" would wrongly strip "I'm seeing three emails".
# Only sentence-*start* patterns are checked via _is_narration().
_NARRATION_SUBSTRINGS: frozenset = frozenset([
    # "I've …" meta-commentary about internal process
    "i've begun analyzing", "i've started analyzing", "i've analyzed the",
    "i've identified the", "i've located the", "i've detailed the",
    "i've pinpointed the", "i've compiled the", "i've employed",
    "i've just refined", "i've now analyzed", "i've re-analyzed",
    # "I am / I'm …" process narration (keep specific)
    "i'm currently analyzing", "i am currently analyzing",
    "i'm currently examining", "i am currently examining",
    "i'm focusing on the screen", "i'm detailing the elements",
    "i'm cataloging", "i'm taking note of",
    "i'm zeroing in", "i'm re-examining the",
    "i'm re-analyzing the", "i am re-analyzing",
    # "Let me …" intent narration (only the meta ones)
    "let me analyze the screen", "let me examine the elements",
    "let me describe what i see internally",
    # Goal/focus narration
    "my next step is to", "my primary focus is", "my focus is on analyzing",
    "my immediate task is", "my analysis shows",
    # "I need to …" internal reasoning
    "i need to understand the layout", "i need to figure out the",
    "i need to determine the",
    # Internal screen-observation narration
    "looking at the screen description",
    # Task narration (internal)
    "to accomplish this i will", "this step is essential",
    # Misc inner-monologue
    "i plan to analyze", "i believe the user wants",
    "the previous attempt failed", "a fresh screen description",
    "a fresh description of", "its coordinates are",
    "prime candidate for",
    "appears incomplete", "lacks context", "remains ambiguous",
])

# Only these two patterns stay as regex — they match fixed delimiters (**…**),
# not unbounded sentence bodies, so they cannot catastrophically backtrack.
_BOLD_HEADER_RE = re.compile(r'\*\*[A-Z][^*]{1,80}\*\*\s*')
_BOLD_THINKING_RE = re.compile(
    r'\*\*(?:Analyzing|Thinking|Detailing|Examining|Noting|Identifying|Processing|Understanding)[^*]{0,80}\*\*',
    re.IGNORECASE,
)
# Strip <think>…</think> blocks using plain string search (no regex needed).
_THINK_OPEN = "<think>"
_THINK_CLOSE = "</think>"

# Keep for any external callers that imported these names.
ANTI_NARRATION_PATTERNS: list = []
COMPILED_ANTI_NARRATION_PATTERNS: list = []
COMPILED_THINKING_PARAGRAPH_PATTERNS: list = []
_THINKING_PATTERN_STRINGS: list = list(_NARRATION_SUBSTRINGS)


def is_location_query(text: str) -> bool:
    """Check if query is asking about digital location (not physical)."""
    location_triggers = [
        "where am i",
        "what site am i on",
        "what website is this",
        "what app am i in",
        "what page am i on",
        "which website",
        "what am i looking at",
        "where am i right now",
        "what am i on",
    ]
    text_lower = text.lower().strip()
    return any(trigger in text_lower for trigger in location_triggers)


@track_performance("remove_narration")
def remove_narration(text: Optional[str]) -> str:
    """
    Remove thinking/process narration from responses.

    Fully ReDoS-safe: no unbounded regex on sentence bodies.
    Uses plain string operations only:
      1. Strip <think>…</think> blocks via str.find (O(n))
      2. Strip **Bold Header** markers via bounded regex (max 80 chars)
      3. Split on sentence-ending punctuation, drop sentences that
         contain any narration substring (O(n * k) where k is fixed)
    """
    if not text or not isinstance(text, str):
        return ""

    # 1. Strip <think>…</think> blocks — plain string search, no regex
    while True:
        start = text.find(_THINK_OPEN)
        if start == -1:
            break
        end = text.find(_THINK_CLOSE, start)
        if end == -1:
            # No closing tag — drop everything from <think> onward
            text = text[:start]
            break
        text = text[:start] + " " + text[end + len(_THINK_CLOSE):]

    # 2. Strip **Bold Header** markers (bounded regex — safe)
    text = _BOLD_HEADER_RE.sub('', text)
    text = _BOLD_THINKING_RE.sub('', text)

    # 3. Sentence-level narration filter — pure substring lookup
    parts = re.split(r'([.!?]+)', text)   # split preserving punctuation
    rebuilt: list[str] = []
    buf = ""
    for chunk in parts:
        buf += chunk
        if chunk and chunk[-1] in ".!?":
            s = buf.strip()
            if s:
                lower = s.lower()
                if not _is_narration(lower):
                    rebuilt.append(s)
            buf = ""

    # Trailing fragment without punctuation
    if buf.strip():
        s = buf.strip()
        if not _is_narration(s.lower()):
            rebuilt.append(s)

    cleaned = " ".join(rebuilt)
    # Collapse whitespace artifacts
    cleaned = " ".join(cleaned.split())

    OrchestratorMetrics.track_narration_removal(
        input_length=len(text),
        output_length=len(cleaned),
        duration=0.0,
    )
    return cleaned


def _is_narration(lower: str) -> bool:
    """Return True if the lowercased sentence should be dropped.

    Only matches sentence *starts* — never arbitrary substrings — so
    normal conversational responses like "I'm seeing three emails" survive.
    """
    # Check FORBIDDEN_SENTENCE_STARTS (imported from config)
    if any(lower.startswith(bad) for bad in FORBIDDEN_SENTENCE_STARTS):
        return True
    # Check narration patterns at sentence start only
    return any(lower.startswith(sub) for sub in _NARRATION_SUBSTRINGS)


@track_performance("classify_vision_error")
def classify_vision_error(error_message: str) -> VisionErrorResult:
    """Classify a vision error into categories for better handling."""
    error_lower = error_message.lower()
    
    for error_type, patterns in VISION_ERROR_TYPES.items():
        for pattern in patterns:
            if re.search(pattern, error_lower):
                result = {
                    'type': error_type,
                    'user_message': _get_user_friendly_message(error_type, error_message),
                    'should_retry': error_type in ['timeout', 'network', 'rate_limit'],
                }
                
                # Track metrics
                OrchestratorMetrics.track_vision_error(
                    error_type=error_type,
                    should_retry=result['should_retry']
                )
                structured_logger.warning(
                    "Vision error classified",
                    error_type=error_type,
                    should_retry=result['should_retry'],
                    error_message=error_message[:100]
                )
                
                return result
    
    # Unknown error type
    OrchestratorMetrics.track_vision_error(error_type='unknown', should_retry=False)
    return {
        'type': 'unknown',
        'user_message': f"Vision analysis failed: {error_message[:100]}. Check backend logs for details.",
        'should_retry': False,
    }


def _get_user_friendly_message(error_type: str, original_error: str) -> str:
    """Get user-friendly error message based on error type."""
    messages = {
        'authentication': "Vision analysis failed: Invalid API key. Check GOOGLE_API_KEY in backend/.env",
        'rate_limit': "Vision analysis failed: Rate limit exceeded. Please wait a moment and try again.",
        'timeout': "Vision analysis timed out. Check your network connection.",
        'network': "Vision analysis failed: Network error. Check your internet connection.",
        'frame_invalid': "Vision analysis failed: Invalid screen capture. Try sharing your screen again.",
        'api_error': f"Vision analysis failed: {original_error[:100]}. Check backend logs for details.",
    }
    return messages.get(error_type, f"Vision analysis failed: {original_error[:100]}. Check backend logs for details.")


def validate_system_instruction_response(text: str) -> tuple[bool, list[str]]:
    """Validate that a response follows system instruction rules.
    
    Returns:
        (is_valid, list_of_violations)
    """
    violations = []
    text_lower = text.lower()
    
    # Check for AI self-reference
    if re.search(r'\b(ai|artificial intelligence)\b', text_lower):
        if 'spectra' not in text_lower:
            violations.append("Uses 'AI' without 'Spectra' context")
    
    # Check for deflection language
    deflection_phrases = [
        "i have limitations",
        "i cannot help",
        "i cannot assist",
        "as an ai",
        "as an assistant",
    ]
    for phrase in deflection_phrases:
        if phrase in text_lower:
            violations.append(f"Uses deflection language: '{phrase}'")
    
    # Check for narration/meta-commentary using the ReDoS-safe substring lookup
    if _is_narration(text_lower):
        violations.append("Contains meta-commentary or narration")
    
    return len(violations) == 0, violations


def requires_confirmation(text: str) -> bool:
    """Check if a command requires destructive action confirmation."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in DESTRUCTIVE_KEYWORDS)


def get_confirmation_reminder(text: str) -> str:
    """Get a confirmation reminder for destructive actions."""
    if requires_confirmation(text):
        return "Remember: this may be destructive, call confirm_action first."
    return ""


SPECTRA_TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="describe_screen",
            description="Analyze visible screen content and extract element positions. Call this when you need to see what's on screen (user asks 'what do you see', 'where am I', 'read this', etc.) or before taking action on elements you haven't seen yet. Returns detailed page context, interactive elements with coordinates, and current state.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "focus_area": types.Schema(
                        type="STRING",
                        description="Screen region to analyze: 'full' (entire viewport), 'center' (middle section), 'top' (header/nav), 'bottom' (footer/actions)",
                        enum=["full", "center", "top", "bottom"],
                    ),
                },
                required=[],
            ),
        ),
        types.FunctionDeclaration(
            name="wait_for_content",
            description=(
                "Wait for the screen to update after an action that triggers a visual change "
                "(typing into autocomplete/combobox, opening a dropdown, date picker, modal, or page transition). "
                "Returns a fresh screen description once a new frame arrives, or guidance if the page didn't update. "
                "ALWAYS use this instead of describe_screen after typing into flight/hotel/search autocomplete fields — "
                "suggestions need 1-2 seconds to render and describe_screen will see the OLD state."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "reason": types.Schema(
                        type="STRING",
                        description="Why you're waiting (e.g., 'autocomplete suggestions', 'date picker opened', 'search results loading')",
                    ),
                    "wait_ms": types.Schema(
                        type="INTEGER",
                        description="Max time to wait in milliseconds (default 2000, max 5000). Use 2000 for dropdowns, 3000 for page loads.",
                        minimum=500,
                        maximum=5000,
                    ),
                    "focus_area": types.Schema(
                        type="STRING",
                        description="Screen region to focus on after update",
                        enum=["full", "center", "top", "bottom"],
                    ),
                },
                required=["reason"],
            ),
        ),
        types.FunctionDeclaration(
            name="click_element",
            description="Click a UI element by description (text label, aria-label, role) or by coordinates. ALWAYS provide description — it is the primary matching method. Coordinates are optional and only needed when description alone is ambiguous.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "description": types.Schema(
                        type="STRING",
                        description="Text label, aria-label, or role of the element to click (e.g., 'Search', 'Sign in', 'Submit', 'search box', 'email input'). This is the PRIMARY matching method — always provide it.",
                        minLength=2,
                    ),
                    "x": types.Schema(type="INTEGER", description="X coordinate (optional, only if you have accurate coords from describe_screen)", minimum=0, maximum=4000),
                    "y": types.Schema(type="INTEGER", description="Y coordinate (optional, only if you have accurate coords from describe_screen)", minimum=0, maximum=4000),
                },
                required=["description"],
            ),
        ),
        types.FunctionDeclaration(
            name="type_text",
            description="Type text into an input field. Provide 'description' to target a specific field by label/placeholder (e.g., 'search box', 'email field', 'password'). Falls back to the currently focused field if no description given.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "text": types.Schema(type="STRING", description="Text to type into the field", minLength=1),
                    "description": types.Schema(type="STRING", description="Label or placeholder of the input field to type into (e.g., 'search box', 'email', 'password', 'username'). Recommended for accuracy."),
                    "x": types.Schema(type="INTEGER", description="X coordinate to click field first (optional, only with accurate coords)", minimum=0, maximum=4000),
                    "y": types.Schema(type="INTEGER", description="Y coordinate to click field first (optional, only with accurate coords)", minimum=0, maximum=4000),
                },
                required=["text"],
            ),
        ),
        types.FunctionDeclaration(
            name="scroll_page",
            description="Scroll page viewport up or down. Returns description of newly visible content. Smart scrolling adapts to page content and structure.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "direction": types.Schema(type="STRING", description="Scroll direction: 'up' (towards top) or 'down' (towards bottom)", enum=["up", "down"]),
                    "amount": types.Schema(type="INTEGER", description="Pixels to scroll (400=small, 800=medium, 1200=large)", minimum=100, maximum=2000),
                },
                required=["direction"],
            ),
        ),
        types.FunctionDeclaration(
            name="press_key",
            description="Press keyboard key for navigation and form submission. Use 'Enter' to submit forms, 'Tab' to navigate between fields, 'Escape' to close dialogs.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "key": types.Schema(
                        type="STRING",
                        description="Keyboard key to press",
                        enum=["Enter", "Tab", "Escape", "ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight", "Space", "Backspace", "Delete"],
                    ),
                },
                required=["key"],
            ),
        ),
        types.FunctionDeclaration(
            name="navigate",
            description="Navigate browser to a new URL. Always use complete URLs with https:// protocol. Waits for page load completion.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "url": types.Schema(
                        type="STRING",
                        description="Complete URL to navigate to (must include https:// or http://)",
                        pattern=r"^https?://.*",
                        minLength=10,
                    ),
                },
                required=["url"],
            ),
        ),
        types.FunctionDeclaration(
            name="confirm_action",
            description="Request user confirmation before executing potentially destructive actions (delete, purchase, submit sensitive forms). Call this FIRST for destructive actions, then wait for clear 'yes' from user before proceeding.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "action_description": types.Schema(
                        type="STRING",
                        description="Clear description of the action requiring confirmation",
                        minLength=5,
                    ),
                },
                required=["action_description"],
            ),
        ),
        types.FunctionDeclaration(
            name="save_snapshot",
            description="Save current screen state as named reference for later comparison. Useful for tracking changes during multi-step processes.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "label": types.Schema(
                        type="STRING",
                        description="Short memorable name for this screen state (e.g., 'before_checkout', 'search_results')",
                        minLength=3,
                        maxLength=20,
                    ),
                },
                required=["label"],
            ),
        ),
        types.FunctionDeclaration(
            name="diff_screen",
            description="Compare current screen to a previously saved snapshot. Shows what changed between states.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "label": types.Schema(
                        type="STRING",
                        description="Name of saved snapshot to compare against",
                        minLength=3,
                    ),
                },
                required=["label"],
            ),
        ),
        types.FunctionDeclaration(
            name="teach_me_app",
            description="Provide guided tour of current application, explaining key features and navigation patterns. Helps users understand unfamiliar interfaces. Identifies ARIA landmarks and accessibility features.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "focus": types.Schema(
                        type="STRING",
                        description="Aspect to focus on: 'navigation', 'features', 'workflow', or 'all'",
                        enum=["navigation", "features", "workflow", "all"],
                    ),
                },
                required=[],
            ),
        ),
        types.FunctionDeclaration(
            name="highlight_element",
            description="Visually highlight a UI element before clicking it. Draws a border around the element to show the user what Spectra is about to interact with. Useful for sighted or low-vision users.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "x": types.Schema(type="INTEGER", description="X coordinate of element to highlight", minimum=0, maximum=4000),
                    "y": types.Schema(type="INTEGER", description="Y coordinate of element to highlight", minimum=0, maximum=4000),
                    "label": types.Schema(
                        type="STRING",
                        description="Brief label to show near the highlight (e.g., 'Search button', 'Submit form')",
                        minLength=1,
                    ),
                },
                required=["x", "y"],
            ),
        ),
        types.FunctionDeclaration(
            name="read_selection",
            description="Read the currently selected or highlighted text on screen aloud to the user. Fundamental for screen reader functionality.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "mode": types.Schema(
                        type="STRING",
                        description="What to read: only selected text, current paragraph, or full visible page",
                        enum=["selected", "paragraph", "page"],
                    ),
                },
                required=[],
            ),
        ),
        types.FunctionDeclaration(
            name="read_page_structure",
            description=(
                "Get the exact DOM structure of the current page: every button, link, input, and heading "
                "with precise text labels and CSS selectors. Call this BEFORE filling forms or clicking elements "
                "on pages you haven't analysed yet — it gives far more accurate targets than vision alone. "
                "Essential for login forms, checkout flows, and any page where describe_screen returns vague coordinates. "
                "Optionally pass a URL; if omitted the current page URL is used automatically."
            ),
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "url": types.Schema(
                        type="STRING",
                        description="URL to analyse (optional — current page URL is used if not provided)",
                    ),
                },
                required=[],
            ),
        ),
    ])
]


# ━━━ STATE MACHINE FOR CONTEXT TRACKING ━━━


class SpectraState:
    """Minimal state machine to track context and avoid redundant operations."""
    
    def __init__(self):
        self.current_app = None        # "gmail", "reddit", "chrome", etc.
        self.last_action = None        # last tool called
        self.last_coordinates = None   # last x,y interacted with
        self.awaiting_confirmation = False
        self.snapshots = {}            # label -> screenshot
        self.last_screen_time = 0      # unix timestamp of last describe_screen
        self.interaction_log = []      # for fine-tuning dataset
    
    def needs_fresh_screen(self, max_age_seconds: int = SCREEN_CONTEXT_MAX_AGE_SECONDS) -> bool:
        """Returns True if screen context is stale."""
        return (time.time() - self.last_screen_time) > max_age_seconds
    
    def inject_context_hint(self, user_input: str) -> str:
        """Prepend context to user input so model doesn't have to re-infer."""
        hint = ""
        if self.current_app:
            hint += f"[Context: currently in {self.current_app}] "
        if self.awaiting_confirmation:
            hint += "[WARNING: waiting for confirm_action response] "
        if requires_confirmation(user_input):
            hint += "[REMINDER: call confirm_action first] "
        return hint + user_input
    
    def update_from_screen_description(self, description: str):
        """Extract app context from screen description."""
        desc_lower = description.lower()
        
        # Detect app type
        if 'gmail' in desc_lower or 'inbox' in desc_lower:
            self.current_app = 'gmail'
        elif 'reddit' in desc_lower:
            self.current_app = 'reddit'
        elif 'github' in desc_lower:
            self.current_app = 'github'
        elif 'google' in desc_lower and 'search' in desc_lower:
            self.current_app = 'google_search'
        elif 'youtube' in desc_lower:
            self.current_app = 'youtube'
        else:
            self.current_app = 'browser'
        
        self.last_screen_time = time.time()
    
    def record_action(self, action_name: str, params: dict):
        """Record action for undo/redo and logging."""
        self.last_action = action_name
        if 'x' in params and 'y' in params:
            self.last_coordinates = (params['x'], params['y'])


# ━━━ RESPONSE PROCESSING AND VALIDATION ━━━

def postprocess_spectra_reply(raw_text: str) -> str:
    """
    Mandatory postprocessing for ALL Spectra responses.
    
    This is the FINAL enforcement layer that ensures responses are clean,
    direct, and follow system instruction rules.
    
    Args:
        raw_text: Raw model output
        
    Returns:
        Cleaned, validated, and compliant response text
    """
    # 1. Strip meta narration (first pass)
    cleaned = remove_narration(raw_text)
    
    # 2. Enforce identity + no-AI language
    is_valid, violations = validate_system_instruction_response(cleaned)
    if not is_valid:
        # Best-effort auto-fix for common violations
        cleaned = re.sub(r"\bas an ai\b", "I'm Spectra", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bartificial intelligence\b", "Spectra", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bai assistant\b", "Spectra", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace("I have limitations", "")
        cleaned = cleaned.replace("I cannot help", "I'll try another way")
        cleaned = cleaned.replace("I cannot assist", "Let me try a different approach")
        
        # Log violations for training data
        logger.warning(f"Spectra violation: {violations} | text={raw_text[:100]!r}")
    
    # 3. Final clean-up
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def process_model_response(text: str) -> str:
    """
    Process model response: remove narration and validate compliance.
    
    DEPRECATED: Use postprocess_spectra_reply instead.
    Kept for backward compatibility.
    
    Args:
        text: Raw model response text
        
    Returns:
        Cleaned and validated response text
    """
    return postprocess_spectra_reply(text)


# ━━━ INTERACTION LOGGING FOR FINE-TUNING ━━━

@track_performance("log_interaction")
def log_interaction(
    user_input: str,
    tool_calls: list[ToolCall],
    model_response: str,
    violations: list[str] | None = None
) -> None:
    """
    Log every interaction for future fine-tuning dataset.
    
    Creates a JSONL file with interaction traces that can be used to fine-tune
    an open-source model to replicate Spectra's behavior.
    
    Args:
        user_input: The user's input text
        tool_calls: List of tool calls made by the model
        model_response: The model's response text
        violations: List of system instruction violations (if any)
    """
    if not LOG_INTERACTIONS:
        return
    
    quality = "good" if not violations else "needs_review"
    
    trace: InteractionTrace = {
        "timestamp": time.time(),
        "user": user_input,
        "tool_calls": tool_calls,
        "response": model_response,
        "violations": violations or [],
        "quality": quality
    }
    
    # Track metrics
    OrchestratorMetrics.track_interaction_logged(
        quality=quality,
        tool_count=len(tool_calls)
    )
    
    
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(INTERACTION_LOG_PATH)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # Check file size and rotate if needed
        if os.path.exists(INTERACTION_LOG_PATH):
            file_size_mb = os.path.getsize(INTERACTION_LOG_PATH) / (1024 * 1024)
            if file_size_mb > MAX_LOG_FILE_SIZE_MB:
                # Rotate log file
                backup_path = f"{INTERACTION_LOG_PATH}.{int(time.time())}"
                os.rename(INTERACTION_LOG_PATH, backup_path)
                structured_logger.info(
                    "Rotated log file",
                    backup_path=backup_path,
                    size_mb=file_size_mb
                )
        
        with open(INTERACTION_LOG_PATH, "a") as f:
            f.write(json.dumps(trace) + "\n")
    except (IOError, OSError) as e:
        structured_logger.error(
            "Failed to log interaction",
            error=str(e),
            error_type=type(e).__name__
        )
    except Exception as e:
        structured_logger.error(
            "Unexpected error logging interaction",
            error=str(e),
            error_type=type(e).__name__
        )


def get_training_dataset_stats() -> DatasetStats:
    """
    Get statistics about the training dataset.
    
    Returns:
        Dict with dataset statistics
    """
    try:
        if not os.path.exists(INTERACTION_LOG_PATH):
            return {
                "total_interactions": 0,
                "good_quality": 0,
                "needs_review": 0,
                "unique_tools": 0,
            }
        
        with open(INTERACTION_LOG_PATH, "r") as f:
            traces = [json.loads(line) for line in f]
        
        return {
            "total_interactions": len(traces),
            "good_quality": sum(1 for t in traces if t.get("quality") == "good"),
            "needs_review": sum(1 for t in traces if t.get("quality") == "needs_review"),
            "unique_tools": len(set(
                tc["name"] 
                for t in traces 
                for tc in t.get("tool_calls", [])
            )),
        }
    except FileNotFoundError:
        return {
            "total_interactions": 0,
            "good_quality": 0,
            "needs_review": 0,
            "unique_tools": 0,
        }
    except Exception as e:
        logger.error(f"Failed to get dataset stats: {e}", exc_info=True)
        return {
            "total_interactions": 0,
            "good_quality": 0,
            "needs_review": 0,
            "unique_tools": 0,
        }
