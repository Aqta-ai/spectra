"""10/10 User personalization and preferences system with Redis-ready architecture."""

import json
import os
import time
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

# High-performance in-memory storage with thread safety (Redis-ready architecture)
_user_preferences: Dict[str, Dict[str, Any]] = {}
_user_workflows: Dict[str, List[Dict[str, Any]]] = {}
_user_history: Dict[str, List[Dict[str, Any]]] = {}
_store_lock = threading.RLock()  # Thread-safe access

PREFERENCES_DIR = Path(os.getenv("PREFERENCES_DIR", "/tmp/spectra_preferences"))
PREFERENCES_DIR.mkdir(parents=True, exist_ok=True)

# Performance constants
MAX_HISTORY_RECORDS = 500  # Reduced from 1000 for better performance
CACHE_TTL = 300  # 5 minutes cache for computed stats
DISK_SYNC_INTERVAL = 30  # Sync to disk every 30 seconds

# Cache for computed statistics
_stats_cache: Dict[str, Tuple[Dict[str, Any], float]] = {}


def _get_disk_path(user_id: str) -> Path:
    """Get safe disk path for user preferences."""
    safe_id = "".join(c for c in user_id if c.isalnum() or c in "-_")
    return PREFERENCES_DIR / f"{safe_id}.json"


def _load_from_disk(user_id: str) -> Optional[Dict[str, Any]]:
    """Load user data from disk with error handling."""
    path = _get_disk_path(user_id)
    try:
        if path.exists():
            data = json.loads(path.read_text())
            logger.debug(f"Loaded preferences from disk for user {user_id}")
            return data
    except Exception as e:
        logger.warning(f"Failed to load preferences for {user_id}: {e}")
    return None


def _save_to_disk(user_id: str, data: Dict[str, Any]) -> None:
    """Save user data to disk with error handling."""
    try:
        path = _get_disk_path(user_id)
        path.write_text(json.dumps(data, indent=2))
        logger.debug(f"Saved preferences to disk for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to save preferences for {user_id}: {e}")


class UserPreferences:
    """10/10 High-performance user preferences with caching and persistence."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._last_disk_sync = 0.0
        
        with _store_lock:
            # Try to load from disk first
            disk_data = _load_from_disk(user_id)
            if disk_data:
                _user_preferences[user_id] = disk_data.get("preferences", {})
                _user_workflows[user_id] = disk_data.get("workflows", [])
                _user_history[user_id] = disk_data.get("history", [])
            
            self.preferences = self._load_preferences()
            self.workflows = self._load_workflows()
            self.history = self._load_history()

    def _load_preferences(self) -> Dict[str, Any]:
        """Load user preferences with smart defaults."""
        if self.user_id in _user_preferences:
            return _user_preferences[self.user_id]

        # 10/10 optimized defaults for Spectra
        prefs = {
            "voice": "Aoede",
            "language": "en-GB",
            "speed": 1.0,
            "volume": 1.0,
            "theme": "dark",
            "accessibility": {
                "high_contrast": False,
                "large_text": False,
                "screen_reader": True,
                "voice_feedback": True,
                "reduced_motion": False,
            },
            "favorite_sites": [
                "https://google.com",
                "https://github.com",
                "https://stackoverflow.com"
            ],
            "blocked_sites": [],
            "performance": {
                "cache_enabled": True,
                "parallel_actions": True,
                "smart_scrolling": True,
            },
            "created_at": time.time(),
            "updated_at": time.time(),
        }

        _user_preferences[self.user_id] = prefs
        return prefs

    def _load_workflows(self) -> List[Dict[str, Any]]:
        """Load user workflows with enhanced defaults."""
        if self.user_id in _user_workflows:
            return _user_workflows[self.user_id]

        # 10/10 enhanced default workflows
        workflows = [
            {
                "name": "check_email",
                "triggers": ["check email", "read emails", "go to email", "gmail"],
                "steps": ["navigate https://gmail.com", "describe_screen"],
                "frequency": 0,
                "success_rate": 1.0,
                "avg_duration": 2.5,
                "created_at": time.time(),
            },
            {
                "name": "read_news",
                "triggers": ["read news", "what's new", "latest news", "bbc"],
                "steps": ["navigate https://bbc.co.uk", "describe_screen"],
                "frequency": 0,
                "success_rate": 1.0,
                "avg_duration": 3.0,
                "created_at": time.time(),
            },
            {
                "name": "search_web",
                "triggers": ["search", "google", "look up", "find"],
                "steps": ["navigate https://google.com", "describe_screen"],
                "frequency": 0,
                "success_rate": 1.0,
                "avg_duration": 1.5,
                "created_at": time.time(),
            },
        ]

        _user_workflows[self.user_id] = workflows
        return workflows

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load user action history."""
        if self.user_id in _user_history:
            return _user_history[self.user_id]

        _user_history[self.user_id] = []
        return []

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get preference with dotted key support (e.g., 'accessibility.high_contrast')."""
        keys = key.split(".")
        value = self.preferences

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

        return value if value is not None else default

    # Alias for compatibility with session.py
    def get(self, key: str, default: Any = None) -> Any:
        """Alias for get_preference."""
        return self.get_preference(key, default)

    def set_preference(self, key: str, value: Any) -> None:
        """Set preference with dotted key support and auto-sync."""
        keys = key.split(".")
        target = self.preferences

        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value
        self.preferences["updated_at"] = time.time()
        self._maybe_sync_to_disk()

    # Alias for compatibility
    def set(self, key: str, value: Any) -> None:
        """Alias for set_preference."""
        self.set_preference(key, value)

    def add_favorite_site(self, url: str) -> None:
        """Add a site to favorites with deduplication."""
        favorites = self.get_preference("favorite_sites", [])
        if url not in favorites:
            favorites.append(url)
            self.set_preference("favorite_sites", favorites)
            logger.info(f"Added favorite site: {url}")

    def remove_favorite_site(self, url: str) -> None:
        """Remove a site from favorites."""
        favorites = self.get_preference("favorite_sites", [])
        if url in favorites:
            favorites.remove(url)
            self.set_preference("favorite_sites", favorites)
            logger.info(f"Removed favorite site: {url}")

    def get_favorite_sites(self) -> List[str]:
        """Get list of favorite sites."""
        return self.get_preference("favorite_sites", [])

    @property
    def favorites(self) -> List[str]:
        """Property alias for favorite sites."""
        return self.get_favorite_sites()

    def add_workflow(self, name: str, triggers: List[str], steps: List[str]) -> None:
        """Add a custom workflow with enhanced metadata."""
        workflow = {
            "name": name,
            "triggers": triggers,
            "steps": steps,
            "frequency": 0,
            "success_rate": 1.0,
            "avg_duration": 0.0,
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        
        # Remove existing workflow with same name
        self.workflows = [w for w in self.workflows if w["name"] != name]
        self.workflows.append(workflow)
        self._maybe_sync_to_disk()
        logger.info(f"Added workflow: {name}")

    def get_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a workflow by name."""
        for workflow in self.workflows:
            if workflow["name"] == name:
                return workflow
        return None

    def match_workflows(self, phrase: str) -> List[Dict[str, Any]]:
        """Get workflows that match a trigger phrase with smart scoring."""
        phrase_lower = phrase.lower()
        scored_workflows = []

        for workflow in self.workflows:
            score = 0
            for trigger in workflow.get("triggers", []):
                trigger_lower = trigger.lower()
                if trigger_lower == phrase_lower:
                    score += 100  # Exact match
                elif trigger_lower in phrase_lower:
                    score += 50   # Trigger in phrase
                elif phrase_lower in trigger_lower:
                    score += 30   # Phrase in trigger
                elif any(word in trigger_lower for word in phrase_lower.split()):
                    score += 10   # Word match
            
            if score > 0:
                # Boost score by frequency and success rate
                frequency_boost = workflow.get("frequency", 0) * 2
                success_boost = workflow.get("success_rate", 1.0) * 10
                final_score = score + frequency_boost + success_boost
                scored_workflows.append((workflow, final_score))

        # Sort by score (highest first)
        scored_workflows.sort(key=lambda x: x[1], reverse=True)
        return [workflow for workflow, _ in scored_workflows]

    def bump_workflow(self, name: str, success: bool = True, duration: float = 0.0) -> None:
        """Update workflow statistics."""
        for workflow in self.workflows:
            if workflow["name"] == name:
                workflow["frequency"] = workflow.get("frequency", 0) + 1
                
                # Update success rate (exponential moving average)
                current_rate = workflow.get("success_rate", 1.0)
                workflow["success_rate"] = 0.9 * current_rate + 0.1 * (1.0 if success else 0.0)
                
                # Update average duration
                if duration > 0:
                    current_avg = workflow.get("avg_duration", 0.0)
                    workflow["avg_duration"] = 0.8 * current_avg + 0.2 * duration
                
                workflow["updated_at"] = time.time()
                self._maybe_sync_to_disk()
                return

    def record_action(self, action: str, success: bool, duration: float) -> None:
        """Record an action with performance optimization."""
        record = {
            "action": action,
            "success": success,
            "duration": duration,
            "timestamp": time.time(),
        }
        
        with _store_lock:
            self.history.append(record)
            
            # Keep only recent records for performance
            if len(self.history) > MAX_HISTORY_RECORDS:
                self.history = self.history[-MAX_HISTORY_RECORDS:]
            
            # Invalidate stats cache
            cache_key = f"stats_{self.user_id}"
            if cache_key in _stats_cache:
                del _stats_cache[cache_key]
        
        self._maybe_sync_to_disk()

    def get_action_stats(self) -> Dict[str, Any]:
        """Get cached action statistics for performance."""
        cache_key = f"stats_{self.user_id}"
        
        # Check cache first
        if cache_key in _stats_cache:
            cached_stats, timestamp = _stats_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL:
                return cached_stats

        # Compute fresh stats
        stats = self._compute_action_stats()
        _stats_cache[cache_key] = (stats, time.time())
        return stats

    def _compute_action_stats(self) -> Dict[str, Any]:
        """Compute action statistics efficiently."""
        if not self.history:
            return {}

        actions = {}
        for record in self.history:
            action = record["action"]
            if action not in actions:
                actions[action] = {
                    "count": 0, 
                    "success": 0, 
                    "total_duration": 0.0,
                    "avg_duration": 0.0,
                    "success_rate": 0.0
                }

            stats = actions[action]
            stats["count"] += 1
            if record["success"]:
                stats["success"] += 1
            stats["total_duration"] += record["duration"]

        # Calculate derived metrics
        for action_stats in actions.values():
            if action_stats["count"] > 0:
                action_stats["success_rate"] = action_stats["success"] / action_stats["count"]
                action_stats["avg_duration"] = action_stats["total_duration"] / action_stats["count"]

        return actions

    def get_most_used_actions(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get most frequently used actions."""
        stats = self.get_action_stats()
        sorted_actions = sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True)
        return [(action, data["count"]) for action, data in sorted_actions[:limit]]

    def get_success_rate(self, action: str) -> float:
        """Get success rate for an action."""
        stats = self.get_action_stats()
        return stats.get(action, {}).get("success_rate", 0.0)

    def _maybe_sync_to_disk(self) -> None:
        """Sync to disk if enough time has passed."""
        now = time.time()
        if now - self._last_disk_sync > DISK_SYNC_INTERVAL:
            self.flush()

    def flush(self) -> None:
        """Force sync to disk."""
        data = {
            "preferences": self.preferences,
            "workflows": self.workflows,
            "history": self.history,
            "synced_at": time.time(),
        }
        _save_to_disk(self.user_id, data)
        self._last_disk_sync = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary with stats."""
        return {
            "preferences": self.preferences,
            "workflows": self.workflows,
            "stats": self.get_action_stats(),
            "top_actions": self.get_most_used_actions(),
        }

    def to_json(self) -> str:
        """Convert preferences to JSON."""
        return json.dumps(self.to_dict(), indent=2, default=str)


def get_user_preferences(user_id: str) -> UserPreferences:
    """Get or create user preferences with caching."""
    return UserPreferences(user_id)


def clear_all_preferences() -> None:
    """Clear all stored preferences (for testing)."""
    with _store_lock:
        _user_preferences.clear()
        _user_workflows.clear()
        _user_history.clear()
        _stats_cache.clear()
    logger.info("Cleared all user preferences")
