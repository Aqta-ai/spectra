"""Persistent session manager to prevent unnecessary reconnections."""

import time
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """Persistent state for a single user session."""
    
    session_id: str
    user_id: str
    screen_stream_active: bool = False
    last_frame_ts: float = 0.0
    last_describe_screen_ok: bool = False
    connection_state: str = "closed"  # "open" | "degraded" | "closed"
    created_at: float = 0.0
    last_activity: float = 0.0
    reconnect_attempts: int = 0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        if self.last_activity == 0.0:
            self.last_activity = time.time()
    
    def is_active(self) -> bool:
        """Check if session is actively streaming."""
        return (
            self.screen_stream_active and
            self.connection_state == "open" and
            time.time() - self.last_frame_ts < 5.0  # Frame within last 5s
        )
    
    def mark_frame_received(self):
        """Update state when frame is received."""
        self.last_frame_ts = time.time()
        self.last_activity = time.time()
        self.screen_stream_active = True
        self.connection_state = "open"
        self.reconnect_attempts = 0
    
    def mark_describe_success(self):
        """Update state when describe_screen succeeds."""
        self.last_describe_screen_ok = True
        self.last_activity = time.time()
    
    def mark_describe_failure(self):
        """Update state when describe_screen fails."""
        self.last_describe_screen_ok = False
    
    def should_request_share(self) -> bool:
        """
        Determine if we should ask user to share screen.
        
        Only request if:
        - No active stream
        - Haven't received frame recently
        - Connection is closed
        """
        return (
            not self.screen_stream_active or
            self.connection_state == "closed" or
            time.time() - self.last_frame_ts > 10.0
        )
    
    def attempt_reconnect(self) -> bool:
        """
        Attempt silent reconnection.
        
        Returns:
            True if reconnect should be attempted, False if should prompt user
        """
        self.reconnect_attempts += 1
        
        # Allow up to 2 silent reconnect attempts
        if self.reconnect_attempts <= 2:
            self.connection_state = "degraded"
            logger.info(f"Attempting silent reconnect #{self.reconnect_attempts}")
            return True
        
        # After 2 failed attempts, prompt user
        logger.warning(f"Reconnect attempts exhausted, prompting user")
        self.connection_state = "closed"
        self.screen_stream_active = False
        return False


class SessionManager:
    """
    Manages persistent sessions to prevent unnecessary reconnections.
    
    Key features:
    - Tracks screen stream state per session
    - Prevents redundant "please share screen" prompts
    - Enables silent reconnection when possible
    - Maintains session continuity across messages
    """
    
    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
        self._cleanup_interval = 300.0  # Clean up stale sessions every 5 min
        self._last_cleanup = time.time()
    
    def get_or_create_session(self, session_id: str, user_id: str = "default") -> SessionState:
        """
        Get existing session or create new one.
        
        This ensures session continuity across messages.
        """
        if session_id not in self._sessions:
            logger.info(f"Creating new session: {session_id} for user {user_id}")
            self._sessions[session_id] = SessionState(
                session_id=session_id,
                user_id=user_id
            )
        
        # Periodic cleanup
        if time.time() - self._last_cleanup > self._cleanup_interval:
            self._cleanup_stale_sessions()
        
        return self._sessions[session_id]
    
    def remove_session(self, session_id: str):
        """Remove session on explicit disconnect."""
        if session_id in self._sessions:
            logger.info(f"Removing session: {session_id}")
            del self._sessions[session_id]
    
    def _cleanup_stale_sessions(self):
        """Remove sessions inactive for > 1 hour."""
        current_time = time.time()
        stale_threshold = 3600.0  # 1 hour
        
        stale_sessions = [
            sid for sid, state in self._sessions.items()
            if current_time - state.last_activity > stale_threshold
        ]
        
        for sid in stale_sessions:
            logger.info(f"Cleaning up stale session: {sid}")
            del self._sessions[sid]
        
        self._last_cleanup = current_time
        
        if stale_sessions:
            logger.info(f"Cleaned up {len(stale_sessions)} stale sessions")
    
    def get_active_session_count(self) -> int:
        """Get count of active sessions."""
        return sum(1 for state in self._sessions.values() if state.is_active())
    
    def get_session_stats(self) -> dict:
        """Get statistics about sessions."""
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": self.get_active_session_count(),
            "sessions_with_stream": sum(
                1 for state in self._sessions.values()
                if state.screen_stream_active
            ),
        }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
