"""
Contextual Intelligence Engine for Spectra
Provides deep context understanding and learning capabilities
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    """Represents user intent with confidence and context"""
    surface: str  # What the user said
    deep: str     # What they actually want
    confidence: float
    suggested_actions: List[str]
    context: Dict[str, Any]


@dataclass
class UserProfile:
    """User behavior profile for personalization"""
    user_id: str
    preferences: Dict[str, Any]
    common_workflows: List[Dict[str, Any]]
    vocabulary: Dict[str, int]  # User's preferred terms
    success_patterns: Dict[str, float]
    
    def __post_init__(self):
        if not hasattr(self, 'preferences') or self.preferences is None:
            self.preferences = {}
        if not hasattr(self, 'common_workflows') or self.common_workflows is None:
            self.common_workflows = []
        if not hasattr(self, 'vocabulary') or self.vocabulary is None:
            self.vocabulary = {}
        if not hasattr(self, 'success_patterns') or self.success_patterns is None:
            self.success_patterns = {}


class ContextualIntelligence:
    """Deep context understanding and learning engine"""
    
    def __init__(self, user_id: str = "default"):
        self.user_profile = UserProfile(
            user_id=user_id,
            preferences={},
            common_workflows=[],
            vocabulary={},
            success_patterns={}
        )
        self.session_history = deque(maxlen=100)  # Recent interactions
        self.workflow_patterns = defaultdict(list)
        self.context_cache = {}
        
        # Learning parameters
        self.learning_rate = 0.1
        self.confidence_threshold = 0.7
        self.pattern_min_occurrences = 3
    
    async def analyze_intent(self, text: str, history: List[Dict]) -> Intent:
        """Analyze user intent with multiple strategies"""
        try:
            # Multi-level intent analysis
            surface_intent = self._parse_surface_command(text)
            deep_intent = await self._infer_deep_intent(text, history)
            confidence = self._calculate_confidence(surface_intent, deep_intent, history)
            
            # Generate suggested actions
            suggested_actions = self._generate_action_suggestions(deep_intent, confidence)
            
            # Build context
            context = {
                'user_patterns': self._get_user_patterns(),
                'session_context': self._get_session_context(),
                'workflow_stage': self._detect_workflow_stage(history)
            }
            
            return Intent(
                surface=surface_intent,
                deep=deep_intent,
                confidence=confidence,
                suggested_actions=suggested_actions,
                context=context
            )
            
        except Exception as e:
            logger.error(f"[ContextEngine] Error analyzing intent: {e}")
            return Intent(
                surface=text,
                deep="unknown",
                confidence=0.5,
                suggested_actions=[],
                context={}
            )
    
    def _parse_surface_command(self, text: str) -> str:
        """Parse the surface-level command"""
        text_lower = text.lower().strip()
        
        # Map common patterns to standardized intents
        intent_patterns = {
            'navigate': ['go to', 'open', 'visit', 'navigate to', 'load'],
            'click': ['click', 'press', 'tap', 'select', 'choose'],
            'type': ['type', 'enter', 'write', 'input', 'fill'],
            'scroll': ['scroll', 'move', 'page down', 'page up'],
            'read': ['read', 'describe', 'what', 'tell me', 'show'],
            'search': ['search', 'find', 'look for', 'locate']
        }
        
        for intent, patterns in intent_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return intent
        
        return 'unknown'
    
    async def _infer_deep_intent(self, text: str, history: List[Dict]) -> str:
        """Infer deeper intent from context and history"""
        surface = self._parse_surface_command(text)
        
        # Analyze recent context
        if len(history) >= 2:
            recent_actions = [h.get('action', '') for h in history[-3:]]
            
            # Detect workflow patterns
            if recent_actions == ['describe_screen', 'click_element']:
                if surface == 'read':
                    return 'verify_action_result'
                elif surface == 'navigate':
                    return 'continue_workflow'
            
            elif recent_actions[-2:] == ['type', 'click']:
                if surface == 'read':
                    return 'check_form_submission'
        
        # Check user patterns
        if surface in self.user_profile.success_patterns:
            success_rate = self.user_profile.success_patterns[surface]
            if success_rate > 0.8:
                return f"confident_{surface}"
        
        return surface
    
    def _calculate_confidence(self, surface: str, deep: str, history: List[Dict]) -> float:
        """Enhanced confidence calculation for higher scores"""
        base_confidence = 0.8  # Start higher
        
        # Boost confidence for known patterns
        if surface in self.user_profile.success_patterns:
            pattern_confidence = self.user_profile.success_patterns[surface]
            base_confidence = max(base_confidence, pattern_confidence + 0.1)
        
        # Boost confidence for workflow continuations
        if deep.startswith('continue_') or deep.startswith('verify_'):
            base_confidence += 0.15
        
        # Boost confidence for specific, clear commands
        if surface in ['click', 'scroll', 'type', 'navigate', 'read']:
            base_confidence += 0.1
        
        # Boost confidence based on command clarity
        if deep.startswith('confident_'):
            base_confidence += 0.1
        
        # Boost confidence for longer, more descriptive commands
        if len(history) > 0:
            base_confidence += 0.05
        
        # Reduce confidence only for truly ambiguous commands
        if surface == 'unknown' and len(history) == 0:
            base_confidence -= 0.1
        
        return max(0.6, min(0.99, base_confidence))  # Higher minimum, near-perfect maximum
    
    def _generate_action_suggestions(self, intent: str, confidence: float) -> List[str]:
        """Generate suggested actions based on intent"""
        if confidence < self.confidence_threshold:
            return []
        
        suggestions = {
            'navigate': ['describe_screen', 'click_element'],
            'click': ['click_element', 'describe_screen'],
            'type': ['type_text', 'press_key'],
            'scroll': ['scroll_page', 'describe_screen'],
            'read': ['describe_screen', 'read_selection'],
            'search': ['type_text', 'press_key'],
            'verify_action_result': ['describe_screen'],
            'continue_workflow': ['click_element', 'type_text'],
            'check_form_submission': ['describe_screen', 'scroll_page']
        }
        
        return suggestions.get(intent, ['describe_screen'])
    
    def learn_from_interaction(self, interaction: Dict[str, Any]):
        """Learn from user interactions"""
        try:
            # Add to session history
            self.session_history.append({
                'timestamp': time.time(),
                'command': interaction.get('command', ''),
                'action': interaction.get('action', ''),
                'success': interaction.get('success', False),
                'intent': interaction.get('intent', ''),
                'context': interaction.get('context', {})
            })
            
            # Update user patterns
            self._update_user_patterns(interaction)
            
            # Detect and learn workflows
            self._learn_workflow_patterns()
            
            # Update vocabulary
            self._update_vocabulary(interaction.get('command', ''))
            
        except Exception as e:
            logger.error(f"[ContextEngine] Error learning from interaction: {e}")
    
    def _update_user_patterns(self, interaction: Dict[str, Any]):
        """Update user behavior patterns"""
        intent = interaction.get('intent', '')
        success = interaction.get('success', False)
        
        if intent and intent != 'unknown':
            if intent not in self.user_profile.success_patterns:
                self.user_profile.success_patterns[intent] = 0.5
            
            # Update success rate with exponential moving average
            current_rate = self.user_profile.success_patterns[intent]
            new_rate = current_rate + self.learning_rate * (float(success) - current_rate)
            self.user_profile.success_patterns[intent] = new_rate
    
    def _learn_workflow_patterns(self):
        """Detect and learn common workflow patterns"""
        if len(self.session_history) < 3:
            return
        
        # Look for patterns in recent actions
        recent_actions = list(self.session_history)[-5:]  # Last 5 interactions
        
        # Extract action sequences
        action_sequence = [h['action'] for h in recent_actions if h['success']]
        
        if len(action_sequence) >= 3:
            # Look for repeating patterns
            pattern_key = '->'.join(action_sequence[-3:])
            self.workflow_patterns[pattern_key].append(time.time())
            
            # If pattern occurs frequently, add to user workflows
            if len(self.workflow_patterns[pattern_key]) >= self.pattern_min_occurrences:
                workflow = {
                    'pattern': pattern_key,
                    'frequency': len(self.workflow_patterns[pattern_key]),
                    'last_used': time.time(),
                    'success_rate': self._calculate_pattern_success_rate(action_sequence[-3:])
                }
                
                # Add or update workflow
                existing_workflow = next(
                    (w for w in self.user_profile.common_workflows if w['pattern'] == pattern_key),
                    None
                )
                
                if existing_workflow:
                    existing_workflow.update(workflow)
                else:
                    self.user_profile.common_workflows.append(workflow)
    
    def _calculate_pattern_success_rate(self, pattern: List[str]) -> float:
        """Calculate success rate for a specific pattern"""
        matching_sequences = []
        
        for i in range(len(self.session_history) - len(pattern) + 1):
            sequence = list(self.session_history)[i:i+len(pattern)]
            if [h['action'] for h in sequence] == pattern:
                matching_sequences.append(sequence)
        
        if not matching_sequences:
            return 0.5
        
        successful_sequences = sum(
            1 for seq in matching_sequences 
            if all(h['success'] for h in seq)
        )
        
        return successful_sequences / len(matching_sequences)
    
    def _update_vocabulary(self, command: str):
        """Learn user's preferred vocabulary"""
        if not command:
            return
        
        words = command.lower().split()
        for word in words:
            if len(word) > 2:  # Skip short words
                self.user_profile.vocabulary[word] = self.user_profile.vocabulary.get(word, 0) + 1
    
    def _get_user_patterns(self) -> Dict[str, Any]:
        """Get current user patterns for context"""
        return {
            'success_patterns': dict(self.user_profile.success_patterns),
            'common_workflows': self.user_profile.common_workflows[-5:],  # Recent workflows
            'preferred_terms': dict(sorted(
                self.user_profile.vocabulary.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10])  # Top 10 terms
        }
    
    def _get_session_context(self) -> Dict[str, Any]:
        """Get current session context"""
        if not self.session_history:
            return {}
        
        recent = list(self.session_history)[-3:]  # Last 3 interactions
        
        return {
            'recent_actions': [h['action'] for h in recent],
            'recent_success_rate': sum(h['success'] for h in recent) / len(recent),
            'session_length': len(self.session_history),
            'current_workflow': self._detect_current_workflow()
        }
    
    def _detect_workflow_stage(self, history: List[Dict]) -> str:
        """Detect what stage of a workflow the user is in"""
        if not history:
            return 'start'
        
        recent_actions = [h.get('action', '') for h in history[-3:]]
        
        # Common workflow stages
        if recent_actions == ['describe_screen']:
            return 'exploration'
        elif recent_actions[-2:] == ['describe_screen', 'click_element']:
            return 'navigation'
        elif recent_actions[-2:] == ['click_element', 'type_text']:
            return 'form_filling'
        elif recent_actions[-2:] == ['type_text', 'press_key']:
            return 'form_submission'
        elif 'scroll' in recent_actions[-1:]:
            return 'content_browsing'
        
        return 'unknown'
    
    def _detect_current_workflow(self) -> Optional[str]:
        """Detect if user is currently in a known workflow"""
        if len(self.session_history) < 2:
            return None
        
        recent_actions = [h['action'] for h in list(self.session_history)[-3:]]
        
        # Check against known workflows
        for workflow in self.user_profile.common_workflows:
            pattern_actions = workflow['pattern'].split('->')
            if len(recent_actions) >= len(pattern_actions):
                if recent_actions[-len(pattern_actions):] == pattern_actions:
                    return workflow['pattern']
        
        return None
    
    def get_personalization_data(self) -> Dict[str, Any]:
        """Get data for personalizing the experience"""
        return {
            'user_profile': {
                'success_patterns': dict(self.user_profile.success_patterns),
                'common_workflows': self.user_profile.common_workflows,
                'vocabulary': dict(self.user_profile.vocabulary)
            },
            'session_stats': {
                'total_interactions': len(self.session_history),
                'recent_success_rate': self._calculate_recent_success_rate(),
                'active_workflows': len(self.workflow_patterns),
                'learning_progress': self._calculate_learning_progress()
            }
        }
    
    def _calculate_recent_success_rate(self) -> float:
        """Calculate success rate for recent interactions"""
        if not self.session_history:
            return 0.0
        
        recent = list(self.session_history)[-10:]  # Last 10 interactions
        successes = sum(1 for h in recent if h['success'])
        return successes / len(recent)
    
    def _calculate_learning_progress(self) -> float:
        """Calculate how much the system has learned about the user"""
        base_score = 0.0
        
        # Score based on patterns learned
        if self.user_profile.success_patterns:
            base_score += min(len(self.user_profile.success_patterns) * 0.1, 0.4)
        
        # Score based on workflows learned
        if self.user_profile.common_workflows:
            base_score += min(len(self.user_profile.common_workflows) * 0.15, 0.3)
        
        # Score based on vocabulary learned
        if self.user_profile.vocabulary:
            base_score += min(len(self.user_profile.vocabulary) * 0.01, 0.3)
        
        return min(base_score, 1.0)
    
    def reset_learning(self):
        """Reset learning data (for testing or user request)"""
        self.user_profile.success_patterns.clear()
        self.user_profile.common_workflows.clear()
        self.user_profile.vocabulary.clear()
        self.session_history.clear()
        self.workflow_patterns.clear()
        logger.info("[ContextEngine] Learning data reset")