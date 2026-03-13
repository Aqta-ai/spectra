"""Diff and snapshot tools with performance optimizations."""

import hashlib
import json
import os
import time
from typing import Optional

# In-memory storage for snapshots: name → {frame, description}
_snapshots: dict[str, dict] = {}
_snapshots_dir = os.getenv("SNAPSHOTS_DIR", "/tmp/spectra_snapshots")

# Performance caching
_cache: dict[str, tuple[str, float]] = {}
_CACHE_TTL = 30.0  # 30 second cache TTL


def _get_snapshot_path(name: str) -> str:
    """Get snapshot file path."""
    return os.path.join(_snapshots_dir, f"{name}.json")


def save_snapshot(name: Optional[str], frame_data: Optional[str], description: str = "") -> str:
    """Save screen snapshot with deduplication."""
    if not name or not frame_data:
        return "error: missing name or frame data"

    # Deduplicate identical frames
    frame_hash = hashlib.md5(frame_data.encode()).hexdigest()[:8]
    cache_key = f"save:{name}:{frame_hash}"

    if cache_key in _cache:
        return _cache[cache_key][0]

    try:
        # Create directory if needed
        os.makedirs(_snapshots_dir, exist_ok=True)

        # Save snapshot
        snapshot_path = _get_snapshot_path(name)
        with open(snapshot_path, "w") as f:
            json.dump({"frame": frame_data, "description": description, "timestamp": os.path.getmtime(snapshot_path) if os.path.exists(snapshot_path) else 0}, f)

        _snapshots[name] = {"frame": frame_data, "description": description}
        _cache[cache_key] = ("snapshot_saved", time.time())

        return "snapshot_saved"
    except Exception as e:
        return f"error: {e}"


def diff_screen(name: str, capture_width: int = 0, capture_height: int = 0) -> str:
    """Return a prompt asking Gemini to compare the current screen to a saved snapshot."""
    try:
        if name not in _snapshots:
            return f"error: snapshot '{name}' not found. Available snapshots: {list(_snapshots.keys()) or 'none saved yet'}"

        saved = _snapshots[name]
        saved_desc = saved.get("description", "")

        size_info = f" Resolution: {capture_width}x{capture_height}." if capture_width else ""
        desc_context = f" When saved, the screen showed: {saved_desc}." if saved_desc else ""

        return (
            f"Compare the current screen to the saved snapshot called '{name}'.{desc_context}"
            f"{size_info}"
            f" Describe exactly what has changed and what remains the same."
            f" Focus on: new or removed elements, text changes, layout shifts, and state differences."
            f" Be specific and concise — your user is listening, not reading."
        )
    except Exception as e:
        return f"error: {e}"


def teach_me_app(focus: str = "all") -> str:
    """Return a prompt asking Gemini to give a guided tour of the current screen."""
    focus_instructions = {
        "navigation": "Focus on navigation menus, links, breadcrumbs, and how to move around the app.",
        "features": "Focus on the main features and tools visible on screen — what each button and section does.",
        "workflow": "Focus on the typical user workflow — what to do first, what steps follow, and how to complete common tasks.",
        "all": "Cover everything: the app name and purpose, navigation structure, key features, and the typical workflow.",
    }
    focus_detail = focus_instructions.get(focus, focus_instructions["all"])

    return (
        f"Look at the current screen and give a guided tour of this application. "
        f"{focus_detail} "
        f"Identify: the app name, its purpose, key UI sections, important buttons and what they do, "
        f"any forms or input areas, and any accessibility features visible. "
        f"Explain clearly as if teaching someone who has never used this app before. "
        f"Be structured and concise — your user is listening, not reading."
    )


def clear_cache():
    """Clear performance cache."""
    _cache.clear()


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return {
        "size": len(_cache),
        "snapshots": len(_snapshots),
    }
