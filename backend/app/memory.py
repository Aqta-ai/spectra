"""
Spectra Memory System - Persistent user context and learning.

Transforms Spectra from a stateless tool into a personal assistant that remembers:
- User preferences (speech rate, verbosity, navigation style)
- Frequently used apps and websites
- Learned shortcuts and corrections
- Session history and patterns
"""

import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class SpectraMemory:
    """Persistent memory system for user preferences and learned patterns."""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.memory_dir = Path(".spectra/memory")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / f"{user_id}.json"
        self._save_lock = threading.Lock()
        self.memory = self._load()
        logger.debug(f"💾 Memory loaded for user {user_id}: Session #{self.memory['session_count']}")
    
    def _load(self) -> Dict[str, Any]:
        """Load memory from disk or create new memory structure."""
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text())
            except Exception as e:
                logger.error(f"Failed to load memory: {e}. Creating new memory.")
        
        # Default memory structure
        return {
            "user_id": self.user_id,
            "created_at": time.time(),
            "session_count": 0,
            "last_session": None,
            "user_preferences": {
                "speech_rate": 1.0,
                "verbosity": "detailed",  # brief, detailed, verbose
                "preferred_navigation": "keyboard",  # keyboard, mouse, voice
                "audio_ducking": True,
                "announce_links": True,
                "announce_headings": True,
                "read_alt_text": True
            },
            "frequent_apps": [],  # [{name, url, count, last_used}]
            "learned_shortcuts": {},  # {phrase: action}
            "correction_history": [],  # [{original, corrected, timestamp}]
            "favorite_sites": [],  # [url]
            "custom_instructions": ""  # User-specific system instruction additions
        }
    
    def save(self):
        """Persist memory to disk atomically (temp file + rename to prevent corruption)."""
        with self._save_lock:
            try:
                data = json.dumps(self.memory, indent=2)
                tmp_fd, tmp_path = tempfile.mkstemp(
                    dir=self.memory_dir, prefix=f"{self.user_id}_", suffix=".tmp"
                )
                try:
                    with os.fdopen(tmp_fd, "w") as f:
                        f.write(data)
                    os.replace(tmp_path, self.memory_file)
                except Exception:
                    os.unlink(tmp_path)
                    raise
                logger.debug(f"💾 Memory saved for user {self.user_id}")
            except Exception as e:
                logger.error(f"Failed to save memory: {e}")
    
    def start_session(self):
        """Increment session count and update last session time."""
        self.memory["session_count"] += 1
        self.memory["last_session"] = time.time()
        self.save()
        logger.info(f"🎯 Session #{self.memory['session_count']} started for {self.user_id}")
    
    def remember(self, key: str, value: Any):
        """
        Remember a user preference or learned pattern.
        
        Supports nested keys with dot notation:
        - remember("user_preferences.speech_rate", 1.5)
        - remember("verbosity", "brief")
        """
        if "." in key:
            # Handle nested keys
            parts = key.split(".")
            current = self.memory
            for part in parts[:-1]:
                current = current.setdefault(part, {})
            current[parts[-1]] = value
        else:
            self.memory[key] = value
        
        self.save()
        logger.info(f"🧠 Remembered: {key} = {value}")
    
    def recall(self, key: str, default=None) -> Any:
        """
        Recall a stored memory.
        
        Supports nested keys with dot notation:
        - recall("user_preferences.speech_rate")
        - recall("verbosity")
        """
        if "." in key:
            parts = key.split(".")
            current = self.memory
            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return default
            return current if current is not None else default
        return self.memory.get(key, default)
    
    def add_correction(self, original: str, corrected: str):
        """
        Learn from user corrections.
        
        Example:
        User: "No, that's the compose button, not send"
        System: add_correction("send button", "compose button")
        """
        correction = {
            "original": original,
            "corrected": corrected,
            "timestamp": time.time()
        }
        self.memory["correction_history"].append(correction)
        
        # Keep only last 100 corrections
        if len(self.memory["correction_history"]) > 100:
            self.memory["correction_history"] = self.memory["correction_history"][-100:]
        
        self.save()
        logger.info(f"✏️ Correction learned: '{original}' → '{corrected}'")
    
    def track_app_usage(self, app_name: str, url: str = ""):
        """
        Track frequently used apps and websites.
        
        Maintains a list of top 10 most-used apps for context.
        """
        apps = self.memory["frequent_apps"]
        
        # Find existing app or create new entry
        for app in apps:
            if app["name"] == app_name or (url and app.get("url") == url):
                app["count"] += 1
                app["last_used"] = time.time()
                break
        else:
            apps.append({
                "name": app_name,
                "url": url,
                "count": 1,
                "last_used": time.time()
            })
        
        # Sort by usage count and keep top 10
        apps.sort(key=lambda x: x["count"], reverse=True)
        self.memory["frequent_apps"] = apps[:10]
        self.save()
    
    def learn_shortcut(self, phrase: str, action: str):
        """
        Learn a user-defined shortcut.
        
        Example:
        User: "When I say 'check email', navigate to Gmail"
        System: learn_shortcut("check email", "navigate https://gmail.com")
        """
        self.memory["learned_shortcuts"][phrase.lower()] = action
        self.save()
        logger.info(f"⚡ Shortcut learned: '{phrase}' → '{action}'")
    
    def get_shortcut(self, phrase: str) -> Optional[str]:
        """Get learned shortcut for a phrase."""
        return self.memory["learned_shortcuts"].get(phrase.lower())
    
    def add_favorite_site(self, url: str):
        """Add a site to favorites."""
        if url not in self.memory["favorite_sites"]:
            self.memory["favorite_sites"].append(url)
            self.save()
            logger.info(f"⭐ Added favorite: {url}")
    
    def get_context_for_system_instruction(self) -> str:
        """
        Generate memory context to inject into system instruction.
        
        This personalizes Spectra's behavior based on learned patterns.
        """
        prefs = self.memory["user_preferences"]
        apps = self.memory["frequent_apps"][:3]
        shortcuts = self.memory["learned_shortcuts"]
        corrections = self.memory["correction_history"][-5:]  # Last 5 corrections
        
        context = f"""
━━━ USER MEMORY (Session #{self.memory['session_count']}) ━━━
I remember this user's preferences and patterns:

Preferences:
- Speech rate: {prefs['speech_rate']}x
- Verbosity: {prefs['verbosity']}
- Navigation style: {prefs['preferred_navigation']}
- Audio ducking: {'enabled' if prefs['audio_ducking'] else 'disabled'}

Frequently used apps: {', '.join(app['name'] for app in apps) if apps else 'None yet'}

Learned shortcuts: {len(shortcuts)} custom commands
{self._format_shortcuts(shortcuts)}

Recent corrections I've learned:
{self._format_corrections(corrections)}

Custom instructions: {self.memory['custom_instructions'] if self.memory['custom_instructions'] else 'None'}

I adapt my responses based on these learned patterns.
"""
        return context
    
    def _format_shortcuts(self, shortcuts: Dict[str, str]) -> str:
        """Format shortcuts for display."""
        if not shortcuts:
            return "- None yet"
        return "\n".join(f"- '{phrase}' → {action}" for phrase, action in list(shortcuts.items())[:5])
    
    def _format_corrections(self, corrections: List[Dict]) -> str:
        """Format recent corrections for display."""
        if not corrections:
            return "- None yet"
        return "\n".join(f"- '{c['original']}' should be '{c['corrected']}'" for c in corrections)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics for debugging/monitoring."""
        return {
            "user_id": self.user_id,
            "session_count": self.memory["session_count"],
            "frequent_apps_count": len(self.memory["frequent_apps"]),
            "shortcuts_count": len(self.memory["learned_shortcuts"]),
            "corrections_count": len(self.memory["correction_history"]),
            "favorites_count": len(self.memory["favorite_sites"]),
            "last_session": self.memory["last_session"]
        }
    
    def clear(self):
        """Clear all memory (for testing or user request)."""
        self.memory = {
            "user_id": self.user_id,
            "created_at": time.time(),
            "session_count": 0,
            "last_session": None,
            "user_preferences": {
                "speech_rate": 1.0,
                "verbosity": "detailed",
                "preferred_navigation": "keyboard",
                "audio_ducking": True,
                "announce_links": True,
                "announce_headings": True,
                "read_alt_text": True
            },
            "frequent_apps": [],
            "learned_shortcuts": {},
            "correction_history": [],
            "favorite_sites": [],
            "custom_instructions": ""
        }
        self.save()
        logger.warning(f"🗑️ Memory cleared for user {self.user_id}")
    
    def export(self) -> str:
        """Export memory as JSON string."""
        return json.dumps(self.memory, indent=2)
    
    def import_memory(self, json_str: str):
        """Import memory from JSON string."""
        try:
            self.memory = json.loads(json_str)
            self.save()
            logger.info(f"📥 Memory imported for user {self.user_id}")
        except Exception as e:
            logger.error(f"Failed to import memory: {e}")
            raise
