"""
Proactive Assistant - Offers help when user seems stuck or needs assistance
"""

import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProactiveContext:
    """Context for proactive assistance decisions"""
    last_user_input_time: float
    last_action_time: float
    last_action_type: Optional[str]
    last_action_success: bool
    repeated_action_count: int
    current_url: str
    has_errors_on_page: bool
    page_load_time: float
    help_offered_count: int


class ProactiveAssistant:
    """Provides proactive assistance to users"""
    
    def __init__(self):
        self.stuck_threshold = 30.0  # Offer help after 30s of inactivity
        self.repeated_action_threshold = 3  # Offer help after 3 failed attempts
        self.slow_page_load_threshold = 5.0  # Alert after 5s page load
        self.max_help_offers_per_session = 5  # Don't be annoying
        
    def should_offer_help(self, context: ProactiveContext) -> tuple[bool, str]:
        """
        Determine if we should proactively offer help.
        
        Returns:
            (should_offer, reason) tuple
        """
        now = time.time()
        
        # Don't offer help too many times
        if context.help_offered_count >= self.max_help_offers_per_session:
            return False, ""
        
        # User is stuck - no input for a while
        time_since_input = now - context.last_user_input_time
        if time_since_input >= self.stuck_threshold:
            return True, "inactivity"
        
        # User is repeating failed actions
        if (context.repeated_action_count >= self.repeated_action_threshold and 
            not context.last_action_success):
            return True, "repeated_failure"
        
        # Page has errors
        if context.has_errors_on_page:
            return True, "page_error"
        
        # Page is loading slowly
        if context.page_load_time >= self.slow_page_load_threshold:
            return True, "slow_load"
        
        return False, ""
    
    def generate_help_message(self, reason: str, context: ProactiveContext) -> str:
        """Generate appropriate help message based on context"""
        
        if reason == "inactivity":
            return "Would you like me to describe what's on screen?"
        
        elif reason == "repeated_failure":
            action = context.last_action_type or "that action"
            return f"I notice {action} isn't working. Would you like me to try a different approach or describe what's available?"
        
        elif reason == "page_error":
            return "I detected an error message on this page. Would you like me to read it to you?"
        
        elif reason == "slow_load":
            return "The page is still loading. Please wait a moment, or let me know if you'd like to try refreshing."
        
        return "Is there anything I can help you with?"
    
    def detect_page_errors(self, screen_description: str) -> bool:
        """Detect if there are error messages on the page"""
        error_indicators = [
            'error',
            'failed',
            'could not',
            'unable to',
            'something went wrong',
            'try again',
            'invalid',
            'not found',
            '404',
            '500',
            'server error',
            'connection failed',
        ]
        
        description_lower = screen_description.lower()
        return any(indicator in description_lower for indicator in error_indicators)
    
    def detect_important_notifications(self, screen_description: str) -> Optional[str]:
        """Detect important notifications or alerts that user should know about"""
        notification_indicators = [
            ('new message', 'You have a new message'),
            ('notification', 'You have a notification'),
            ('alert', 'There is an alert'),
            ('warning', 'There is a warning'),
            ('unread', 'You have unread items'),
            ('update available', 'An update is available'),
            ('expires', 'Something is expiring soon'),
            ('due', 'Something is due'),
        ]
        
        description_lower = screen_description.lower()
        for indicator, message in notification_indicators:
            if indicator in description_lower:
                return message
        
        return None
    
    def suggest_next_action(self, context: ProactiveContext) -> Optional[str]:
        """Suggest next action based on context"""
        
        # If user just navigated, suggest exploring
        if context.last_action_type == "navigate":
            return "Would you like me to describe what's on this page?"
        
        # If user just searched, suggest reading results
        if context.last_action_type == "search":
            return "Would you like me to read the search results?"
        
        # If user just filled a form, suggest submitting
        if context.last_action_type == "type":
            return "Would you like me to submit this form?"
        
        return None
    
    def track_action_pattern(
        self, 
        action_history: list[Dict[str, Any]]
    ) -> tuple[int, bool]:
        """
        Track if user is repeating the same action.
        
        Returns:
            (repeat_count, is_failing) tuple
        """
        if len(action_history) < 2:
            return 0, False
        
        # Look at last 5 actions
        recent_actions = action_history[-5:]
        
        # Check if same action type is being repeated
        action_types = [a.get('type') for a in recent_actions]
        if len(set(action_types)) == 1:
            # Same action repeated
            successes = [a.get('success', False) for a in recent_actions]
            is_failing = not any(successes)
            return len(recent_actions), is_failing
        
        return 0, False


# Global instance
_proactive_assistant = ProactiveAssistant()


def get_proactive_assistant() -> ProactiveAssistant:
    """Get the global proactive assistant instance"""
    return _proactive_assistant
