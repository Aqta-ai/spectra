"""
Voice Command Processor for Spectra Accessibility Enhancement

This module provides natural language voice command processing for blind and visually impaired users.
It handles command pattern matching, context-dependent command resolution, and command variations
to enable intuitive voice-controlled interaction with screen content.

Key Features:
- Command pattern matching for click, type, navigate actions
- Support for command variations ("click", "press", "tap", "select")
- Context-dependent command resolution ("click it" references)
- Compound command parsing and execution
- Command suggestions for ambiguous requests
"""

import re
import logging
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CommandAction(Enum):
    """Enumeration of supported command actions."""
    CLICK = "click"
    TYPE = "type"
    NAVIGATE = "navigate"
    SCROLL = "scroll"
    READ = "read"
    FIND = "find"
    WAIT = "wait"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Structured representation of a parsed voice command."""
    action: CommandAction
    target: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    original_text: str = ""
    context_dependent: bool = False
    compound: bool = False
    sub_commands: Optional[List['ParsedCommand']] = None
    suggestions: Optional[List[str]] = None


@dataclass
class CommandContext:
    """Context information for command resolution."""
    last_mentioned_element: Optional[str] = None
    current_page_elements: Optional[List[str]] = None
    recent_commands: Optional[List[ParsedCommand]] = None
    screen_description: Optional[str] = None
    conversation_history: Optional[List[str]] = None


class VoiceCommandProcessor:
    """
    Natural language voice command processor for accessibility users.
    
    This class processes voice commands from blind and visually impaired users,
    converting natural language into structured actions that can be executed
    by the system. It supports command variations, context-dependent references,
    and compound commands.
    """
    
    def __init__(self):
        """Initialize the VoiceCommandProcessor with command patterns and context."""
        
        # Enhanced command patterns with more sophisticated regex for natural language
        self.command_patterns = {
            CommandAction.CLICK: [
                # Basic patterns
                r'click\s+(?:on\s+)?(?:the\s+)?(.+)',
                r'press\s+(?:on\s+)?(?:the\s+)?(.+)',
                r'tap\s+(?:on\s+)?(?:the\s+)?(.+)',
                r'select\s+(?:the\s+)?(.+)',
                r'choose\s+(?:the\s+)?(.+)',
                r'activate\s+(?:the\s+)?(.+)',
                r'hit\s+(?:the\s+)?(.+)',
                r'push\s+(?:the\s+)?(.+)',
                r'touch\s+(?:the\s+)?(.+)',
                # Natural language variations
                r'(?:please\s+)?(?:can\s+you\s+)?click\s+(?:on\s+)?(?:the\s+)?(.+?)(?:\s+please)?',
                r'(?:i\s+want\s+to\s+|i\s+need\s+to\s+)?(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?(.+)',
                r'(?:could\s+you\s+)?(?:please\s+)?(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?(.+?)(?:\s+for\s+me)?',
                r'(?:let\'s\s+|let\s+me\s+)?(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?(.+)',
                # Positional references
                r'(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?(.+?)\s+(?:at\s+the\s+)?(?:top|bottom|left|right|center)',
                r'(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?(?:first|second|third|last|next|previous)\s+(.+)',
                # Ordinal patterns
                r'(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?(\d+)(?:st|nd|rd|th)\s+(.+)',
                # Color/appearance based
                r'(?:click|press|tap)\s+(?:on\s+)?(?:the\s+)?(?:blue|red|green|yellow|white|black|gray|grey)\s+(.+)',
            ],
            CommandAction.TYPE: [
                # Basic patterns
                r'type\s+(.+)',
                r'enter\s+(.+)',
                r'write\s+(.+)',
                r'input\s+(.+)',
                r'fill\s+in\s+(.+)',
                r'put\s+in\s+(.+)',
                r'insert\s+(.+)',
                # Natural language variations
                r'(?:please\s+)?(?:can\s+you\s+)?type\s+(.+?)(?:\s+please)?',
                r'(?:i\s+want\s+to\s+|i\s+need\s+to\s+)?(?:type|enter|write)\s+(.+)',
                r'(?:could\s+you\s+)?(?:please\s+)?(?:type|enter|write)\s+(.+?)(?:\s+for\s+me)?',
                # Field-specific patterns
                r'(?:type|enter|write|input)\s+(.+?)\s+(?:in|into)\s+(?:the\s+)?(.+?)(?:\s+field|\s+box)?',
                r'(?:fill\s+(?:in|out)\s+)?(?:the\s+)?(.+?)\s+(?:field|box)\s+with\s+(.+)',
                r'(?:put|enter)\s+(.+?)\s+(?:in|into)\s+(?:the\s+)?(.+?)(?:\s+field|\s+box)?',
                # Special typing commands
                r'(?:type|enter)\s+(?:my\s+)?(?:name|email|password|address|phone)',
                r'(?:clear\s+(?:the\s+)?(?:field|box)\s+and\s+)?(?:type|enter)\s+(.+)',
            ],
            CommandAction.NAVIGATE: [
                # Basic patterns
                r'go\s+to\s+(.+)',
                r'open\s+(.+)',
                r'visit\s+(.+)',
                r'navigate\s+to\s+(.+)',
                r'browse\s+to\s+(.+)',
                r'load\s+(.+)',
                r'access\s+(.+)',
                # Natural language variations
                r'(?:please\s+)?(?:can\s+you\s+)?(?:go\s+to|open|visit|navigate\s+to)\s+(.+?)(?:\s+please)?',
                r'(?:i\s+want\s+to\s+|i\s+need\s+to\s+)?(?:go\s+to|visit|open)\s+(.+)',
                r'(?:could\s+you\s+)?(?:please\s+)?(?:take\s+me\s+to|show\s+me)\s+(.+)',
                r'(?:let\'s\s+|let\s+me\s+)?(?:go\s+to|visit|check\s+out)\s+(.+)',
                # URL patterns
                r'(?:go\s+to|open|visit)\s+(?:the\s+)?(?:website|site|page|url)\s+(.+)',
                r'(?:navigate\s+to|browse\s+to)\s+(?:the\s+)?(?:website|site|page)\s+(.+)',
                # Back/forward navigation
                r'go\s+(?:back|forward|home)',
                r'(?:navigate|go)\s+(?:back\s+to|forward\s+to)\s+(.+)',
            ],
            CommandAction.SCROLL: [
                # Basic directional scrolling
                r'scroll\s+(up|down|left|right)',
                r'scroll\s+(up|down|left|right)\s+(?:by\s+)?(\d+)?',
                r'page\s+(up|down)',
                r'move\s+(up|down|left|right)',
                r'go\s+(up|down|left|right)',
                # Natural language variations
                r'(?:please\s+)?(?:can\s+you\s+)?scroll\s+(up|down|left|right)(?:\s+please)?',
                r'(?:i\s+want\s+to\s+|i\s+need\s+to\s+)?scroll\s+(up|down|left|right)',
                r'(?:could\s+you\s+)?(?:please\s+)?scroll\s+(up|down|left|right)(?:\s+for\s+me)?',
                # Amount-based scrolling
                r'scroll\s+(up|down|left|right)\s+(?:by\s+)?(\d+)\s*(?:lines?|pixels?|pages?)?',
                r'scroll\s+(?:a\s+)?(?:little|bit)\s+(up|down|left|right)',
                r'scroll\s+(?:a\s+)?(?:lot|much)\s+(up|down|left|right)',
                # Position-based scrolling
                r'scroll\s+to\s+(?:the\s+)?(top|bottom|beginning|end)',
                r'(?:go\s+to|jump\s+to)\s+(?:the\s+)?(top|bottom|beginning|end)',
                r'scroll\s+(?:all\s+the\s+way\s+)?(up|down)',
                # Page-based scrolling
                r'(?:turn\s+the\s+)?page\s+(up|down|forward|back)',
                r'(?:next|previous)\s+page',
            ],
            CommandAction.READ: [
                # Basic reading patterns
                r'read\s+(?:the\s+)?(.+)',
                r'tell\s+me\s+(?:about\s+)?(?:the\s+)?(.+)',
                r'what\s+(?:does|is)\s+(?:the\s+)?(.+)\s+(?:say|contain)?',
                r'describe\s+(?:the\s+)?(.+)',
                r'explain\s+(?:the\s+)?(.+)',
                # Natural language variations
                r'(?:please\s+)?(?:can\s+you\s+)?read\s+(?:the\s+)?(.+?)(?:\s+(?:to\s+me|please))?',
                r'(?:i\s+want\s+to\s+|i\s+need\s+to\s+)?(?:hear|know)\s+(?:about\s+)?(?:the\s+)?(.+)',
                r'(?:could\s+you\s+)?(?:please\s+)?(?:tell\s+me|let\s+me\s+know)\s+(?:about\s+)?(?:the\s+)?(.+)',
                r'what\s+(?:does\s+)?(?:the\s+)?(.+?)\s+(?:say|contain|have|show)',
                # Content-specific reading
                r'read\s+(?:the\s+)?(?:first|second|third|last|next|previous)\s+(.+)',
                r'read\s+(?:all\s+)?(?:the\s+)?(.+?)\s+(?:on\s+(?:the\s+)?(?:page|screen))',
                r'(?:what\'s|what\s+is)\s+(?:in\s+)?(?:the\s+)?(.+?)(?:\s+section|\s+area)?',
                # Page/screen reading
                r'read\s+(?:the\s+)?(?:entire\s+|whole\s+)?(?:page|screen)',
                r'(?:tell\s+me\s+)?what\'s\s+on\s+(?:the\s+)?(?:page|screen)',
            ],
            CommandAction.FIND: [
                # Basic finding patterns
                r'find\s+(?:the\s+)?(.+)',
                r'search\s+for\s+(?:the\s+)?(.+)',
                r'look\s+for\s+(?:the\s+)?(.+)',
                r'locate\s+(?:the\s+)?(.+)',
                r'where\s+is\s+(?:the\s+)?(.+)',
                # Natural language variations
                r'(?:please\s+)?(?:can\s+you\s+)?(?:find|locate)\s+(?:the\s+)?(.+?)(?:\s+please)?',
                r'(?:i\s+want\s+to\s+|i\s+need\s+to\s+)?(?:find|locate|search\s+for)\s+(?:the\s+)?(.+)',
                r'(?:could\s+you\s+)?(?:please\s+)?(?:help\s+me\s+)?(?:find|locate)\s+(?:the\s+)?(.+)',
                r'(?:do\s+you\s+see\s+)?(?:the\s+)?(.+?)(?:\s+anywhere)?',
                # Question-based finding
                r'where\s+(?:can\s+i\s+find|is)\s+(?:the\s+)?(.+)',
                r'(?:is\s+there\s+)?(?:a|an)\s+(.+?)(?:\s+(?:on\s+(?:the\s+)?(?:page|screen)))?',
                r'(?:can\s+you\s+see\s+)?(?:a|an|the)\s+(.+?)(?:\s+(?:on\s+(?:the\s+)?(?:page|screen)))?',
                # Search-specific patterns
                r'search\s+(?:the\s+page\s+)?for\s+(.+)',
                r'look\s+(?:around\s+)?for\s+(?:a|an|the)\s+(.+)',
            ],
            CommandAction.WAIT: [
                # Basic wait patterns
                r'wait\s+(?:for\s+)?(\d+)?\s*(?:seconds?|minutes?)?',
                r'pause\s+(?:for\s+)?(\d+)?\s*(?:seconds?|minutes?)?',
                r'hold\s+on',
                r'give\s+me\s+a\s+moment',
                # Natural language variations
                r'(?:please\s+)?(?:can\s+you\s+)?wait\s+(?:for\s+)?(\d+)?\s*(?:seconds?|minutes?)?',
                r'(?:i\s+need\s+)?(?:a\s+)?(?:moment|second|minute)',
                r'(?:just\s+)?(?:wait|hold\s+on)\s+(?:a\s+)?(?:moment|second|minute)',
                r'(?:let\s+me\s+)?(?:think|pause)\s+(?:for\s+)?(?:a\s+)?(?:moment|second)',
                # Specific duration patterns
                r'wait\s+(?:for\s+)?(?:a\s+)?(?:few\s+)?(?:seconds?|minutes?)',
                r'pause\s+(?:for\s+)?(?:a\s+)?(?:brief\s+)?(?:moment|second)',
                r'(?:give\s+me|wait)\s+(?:just\s+)?(?:a\s+)?(?:quick\s+)?(?:moment|second)',
            ]
        }
        
        # Enhanced context-dependent command patterns with better pronoun handling
        self.context_patterns = [
            # Direct pronoun references
            r'^(?:click|press|tap|select|choose|activate|hit|push|touch)\s+(?:on\s+)?it$',
            r'^(?:type|enter|write|input)\s+(?:in|into)\s+it$',
            r'^(?:read|describe|explain|tell\s+me\s+about)\s+it$',
            r'^(?:find|locate|search\s+for)\s+it$',
            r'^(?:go|navigate)\s+(?:to\s+)?there$',
            r'^(?:scroll|move)\s+(?:to\s+)?there$',
            
            # Demonstrative pronouns
            r'^(?:click|press|tap|select)\s+(?:on\s+)?(?:that|this)(?:\s+one)?$',
            r'^(?:type|enter|write)\s+(?:in|into)\s+(?:that|this)(?:\s+one)?$',
            r'^(?:read|describe)\s+(?:that|this)(?:\s+one)?$',
            r'^(?:find|locate)\s+(?:that|this)(?:\s+one)?$',
            
            # Action repetition patterns
            r'^(?:do\s+)?(?:that|it)\s*(?:again)?$',
            r'^(?:repeat|redo)\s+(?:that|it)$',
            r'^(?:try\s+)?(?:that|it)\s+again$',
            r'^(?:same\s+)?(?:thing|action)(?:\s+again)?$',
            
            # Relative references
            r'^(?:click|press|tap)\s+(?:the\s+)?(?:same|previous|last)\s+(?:one|thing|button|link)$',
            r'^(?:go\s+)?(?:back\s+)?(?:to\s+)?(?:the\s+)?(?:previous|last)\s+(?:one|page|place)$',
            r'^(?:type|enter)\s+(?:the\s+)?(?:same|previous|last)\s+(?:thing|text)$',
            
            # Contextual action patterns
            r'^(?:yes|ok|okay|sure|alright)(?:\s+do\s+it)?$',
            r'^(?:no|nope|cancel|never\s+mind)$',
            r'^(?:continue|proceed|keep\s+going)$',
            r'^(?:stop|halt|cancel)$',
            
            # Enhanced compound context patterns
            r'^(?:and\s+)?(?:then\s+)?(?:click|press|tap)\s+(?:on\s+)?it$',
            r'^(?:and\s+)?(?:then\s+)?(?:type|enter)\s+(?:in|into)\s+it$',
            r'^(?:and\s+)?(?:then\s+)?(?:read|describe)\s+it$',
        ]
        
        # Enhanced compound command separators for natural language
        self.compound_separators = [
            r'\s+and\s+(?:then\s+)?',
            r'\s+then\s+',
            r'\s+after\s+that\s+',
            r'\s+next\s+',
            r'\s+followed\s+by\s+',
            r'\s+and\s+after\s+that\s+',
            r'\s+and\s+also\s+',
            r'[,;]\s*(?:then\s+|and\s+)?',
            r'\.\s+(?:then\s+|next\s+|after\s+that\s+)?',
            r'\s+before\s+',  # For reverse order commands
        ]
        
        # Enhanced element reference patterns for context resolution
        self.element_patterns = [
            # Basic element patterns
            r'(?:the\s+)?(.+?)\s+(?:button|link|field|input|box|menu|dropdown|checkbox|radio)',
            r'(?:the\s+)?(.+?)\s+(?:at\s+the\s+)?(?:top|bottom|left|right|center)',
            r'(?:the\s+)?(?:first|second|third|last|next|previous)\s+(.+)',
            r'(?:the\s+)?(.+?)\s+(?:labeled|titled|named)\s+["\'](.+?)["\']',
            
            # Enhanced positional patterns
            r'(?:the\s+)?(.+?)\s+(?:in\s+the\s+)?(?:upper|lower)\s+(?:left|right|center)',
            r'(?:the\s+)?(.+?)\s+(?:on\s+the\s+)?(?:left|right)\s+(?:side|hand\s+side)',
            r'(?:the\s+)?(.+?)\s+(?:near|next\s+to|beside|below|above)\s+(?:the\s+)?(.+)',
            
            # Ordinal and numbered patterns
            r'(?:the\s+)?(\d+)(?:st|nd|rd|th)\s+(.+?)\s+(?:from\s+the\s+)?(?:top|bottom|left|right)',
            r'(?:the\s+)?(.+?)\s+(?:number|#)\s*(\d+)',
            r'(?:item|option)\s+(\d+)',
            
            # Color and appearance patterns
            r'(?:the\s+)?(?:blue|red|green|yellow|white|black|gray|grey|orange|purple)\s+(.+)',
            r'(?:the\s+)?(?:big|small|large|tiny|huge)\s+(.+)',
            r'(?:the\s+)?(?:highlighted|selected|active|disabled|enabled)\s+(.+)',
            
            # Content-based patterns
            r'(?:the\s+)?(.+?)\s+(?:that\s+says|containing|with\s+text)\s+["\'](.+?)["\']',
            r'(?:the\s+)?(.+?)\s+(?:that\s+says|containing)\s+(.+)',
            r'(?:the\s+)?(.+?)\s+with\s+(?:the\s+)?(?:word|text|label)\s+(.+)',
            
            # Contextual patterns
            r'(?:the\s+)?(?:main|primary|default)\s+(.+)',
            r'(?:the\s+)?(?:current|selected|active)\s+(.+)',
            r'(?:the\s+)?(?:empty|blank)\s+(.+)',
        ]
        
        # Command context for tracking state
        self.context = CommandContext()
        
        # Common UI element synonyms
        self.element_synonyms = {
            'btn': 'button',
            'lnk': 'link',
            'txt': 'text',
            'img': 'image',
            'pic': 'picture',
            'photo': 'image',
            'form': 'form field',
            'dropdown': 'select',
            'combo': 'combobox',
            'check': 'checkbox',
            'radio': 'radio button',
            'tab': 'tab',
            'menu': 'menu',
            'nav': 'navigation',
            'search': 'search box',
            'login': 'login button',
            'submit': 'submit button',
            'cancel': 'cancel button',
            'ok': 'ok button',
            'yes': 'yes button',
            'no': 'no button',
        }
    
    def is_voice_command(self, text: str) -> bool:
        """
        Determine if the input text contains a voice command.
        
        Args:
            text: The user's input text
            
        Returns:
            True if this appears to be a voice command, False otherwise
        """
        if not text:
            return False
            
        text_lower = text.lower().strip()
        
        # Exclude common conversational phrases that might match patterns
        conversational_phrases = [
            r'^what is',
            r'^how are',
            r'^hello',
            r'^hi\b',
            r'^good morning',
            r'^good afternoon',
            r'^good evening',
            r'^thank you',
            r'^thanks',
            r'^please help',
            r'^i need help',
            r'^can you help',
            # Identity / chitchat — must go straight to Gemini
            r'^who are you',
            r'^what are you',
            r'^who built you',
            r'^who made you',
            r'^who created you',
            r'^tell me about yourself',
            r'^introduce yourself',
            r'^are you',
            r'^do you',
            r'^can you$',
            r'^what can you do',
            r'^how do you work',
        ]
        
        for phrase in conversational_phrases:
            if re.search(phrase, text_lower):
                return False
        
        # Check for context-dependent commands
        for pattern in self.context_patterns:
            if re.match(pattern, text_lower):
                return True
        
        # Check for explicit command patterns
        for action, patterns in self.command_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return True
        
        return False
    
    def parse_command(self, text: str, context: Optional[CommandContext] = None) -> ParsedCommand:
        """
        Parse natural language text into a structured command.
        
        Args:
            text: The user's input text
            context: Optional context information for command resolution
            
        Returns:
            ParsedCommand object with parsed information
        """
        if not text:
            return ParsedCommand(action=CommandAction.UNKNOWN, original_text=text)
        
        # Update context if provided
        if context:
            self.context = context
        
        text_lower = text.lower().strip()
        
        # Check for compound commands first
        if self._is_compound_command(text_lower):
            return self._parse_compound_command(text, text_lower)
        
        # Check for context-dependent commands
        context_command = self._parse_context_command(text, text_lower)
        if context_command:
            return context_command
        
        # Parse explicit commands
        explicit_command = self._parse_explicit_command(text, text_lower)
        if explicit_command:
            return explicit_command
        
        # If no pattern matches, return unknown command with suggestions
        suggestions = self._generate_suggestions(text_lower)
        return ParsedCommand(
            action=CommandAction.UNKNOWN,
            original_text=text,
            confidence=0.0,
            suggestions=suggestions
        )
    
    def update_context(self, screen_description: str = None, mentioned_element: str = None, 
                      recent_command: ParsedCommand = None, conversation_history: List[str] = None):
        """
        Update the command context with new information.
        
        Args:
            screen_description: Current screen description
            mentioned_element: Recently mentioned UI element
            recent_command: Recently executed command
            conversation_history: Recent conversation messages
        """
        if screen_description:
            self.context.screen_description = screen_description
            self.context.current_page_elements = self._extract_elements_from_description(screen_description)
        
        if mentioned_element:
            self.context.last_mentioned_element = mentioned_element
        
        if recent_command:
            if not self.context.recent_commands:
                self.context.recent_commands = []
            self.context.recent_commands.append(recent_command)
            # Keep only last 5 commands
            self.context.recent_commands = self.context.recent_commands[-5:]
        
        if conversation_history:
            self.context.conversation_history = conversation_history[-10:]  # Keep last 10 messages
    
    def _is_compound_command(self, text_lower: str) -> bool:
        """Enhanced compound command detection with better natural language understanding."""
        # Check for explicit compound separators
        separator_count = 0
        for separator in self.compound_separators:
            if re.search(separator, text_lower):
                separator_count += 1
        
        if separator_count == 0:
            return False
        
        # Count distinct action words to ensure it's actually compound
        action_words = [
            'click', 'press', 'tap', 'select', 'choose', 'activate',
            'type', 'enter', 'write', 'input', 'fill',
            'scroll', 'move', 'page',
            'go', 'open', 'visit', 'navigate',
            'read', 'tell', 'describe', 'explain',
            'find', 'search', 'look', 'locate'
        ]
        
        # Use word boundaries to avoid partial matches
        action_count = 0
        found_actions = set()
        for word in action_words:
            if re.search(r'\b' + word + r'\b', text_lower) and word not in found_actions:
                action_count += 1
                found_actions.add(word)
        
        # Also check for implicit compound patterns
        implicit_compound_patterns = [
            r'\b(?:scroll|move)\s+(?:down|up)\s+and\s+(?:read|tell|describe)',
            r'\b(?:click|press|tap)\s+.+\s+and\s+(?:type|enter|write)',
            r'\b(?:find|locate)\s+.+\s+and\s+(?:click|press|tap)',
            r'\b(?:go|navigate)\s+to\s+.+\s+and\s+(?:find|search)',
        ]
        
        for pattern in implicit_compound_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return action_count >= 2
    
    def _parse_compound_command(self, original_text: str, text_lower: str) -> ParsedCommand:
        """Enhanced compound command parsing with better natural language support."""
        # Split the command using compound separators
        parts = [original_text]
        used_separator = None
        
        for separator in self.compound_separators:
            new_parts = []
            for part in parts:
                split_parts = re.split(separator, part)
                if len(split_parts) > 1:
                    used_separator = separator
                    new_parts.extend(split_parts)
                else:
                    new_parts.append(part)
            parts = new_parts
            if len(parts) > 1:
                break
        
        # Clean and parse each part as a separate command
        sub_commands = []
        context_carryover = {}
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            # Handle context carryover for pronouns in later parts
            if i > 0 and sub_commands:
                # If this part starts with a pronoun, try to resolve from previous command
                if re.match(r'^\s*(?:and\s+)?(?:then\s+)?(?:it|that|this)\b', part.lower()):
                    if sub_commands[-1].target:
                        context_carryover['last_mentioned_element'] = sub_commands[-1].target
            
            # Create temporary context for this sub-command
            temp_context = CommandContext(
                last_mentioned_element=context_carryover.get('last_mentioned_element', self.context.last_mentioned_element),
                current_page_elements=self.context.current_page_elements,
                recent_commands=self.context.recent_commands,
                screen_description=self.context.screen_description,
                conversation_history=self.context.conversation_history
            )
            
            # Parse the sub-command with enhanced context
            original_context = self.context
            self.context = temp_context
            sub_command = self.parse_command(part)
            self.context = original_context
            
            if sub_command.action != CommandAction.UNKNOWN:
                sub_commands.append(sub_command)
                # Update context carryover for next iteration
                if sub_command.target:
                    context_carryover['last_mentioned_element'] = sub_command.target
        
        if sub_commands:
            # Use the first command's action as the primary action
            primary_action = sub_commands[0].action
            
            # Calculate compound confidence based on individual confidences
            compound_confidence = sum(cmd.confidence for cmd in sub_commands) / len(sub_commands)
            
            return ParsedCommand(
                action=primary_action,
                original_text=original_text,
                compound=True,
                sub_commands=sub_commands,
                confidence=compound_confidence,
                parameters={'separator_used': used_separator}
            )
        
        return ParsedCommand(action=CommandAction.UNKNOWN, original_text=original_text)
    
    def _parse_context_command(self, original_text: str, text_lower: str) -> Optional[ParsedCommand]:
        """Enhanced context-dependent command parsing with better pronoun resolution."""
        for pattern in self.context_patterns:
            if re.match(pattern, text_lower):
                # Determine action from the pattern with more sophisticated matching
                action = CommandAction.UNKNOWN
                
                if any(word in text_lower for word in ['click', 'press', 'tap', 'select', 'choose', 'activate', 'hit', 'push', 'touch']):
                    action = CommandAction.CLICK
                elif any(word in text_lower for word in ['type', 'enter', 'write', 'input', 'fill']):
                    action = CommandAction.TYPE
                elif any(word in text_lower for word in ['read', 'describe', 'explain', 'tell']):
                    action = CommandAction.READ
                elif any(word in text_lower for word in ['find', 'locate', 'search']):
                    action = CommandAction.FIND
                elif any(word in text_lower for word in ['go', 'navigate', 'visit', 'open']):
                    action = CommandAction.NAVIGATE
                elif any(word in text_lower for word in ['scroll', 'move', 'page']):
                    action = CommandAction.SCROLL
                elif any(word in text_lower for word in ['wait', 'pause', 'hold']):
                    action = CommandAction.WAIT
                elif any(word in text_lower for word in ['repeat', 'redo', 'again']):
                    # For repeat commands, try to get the last action
                    if self.context.recent_commands:
                        action = self.context.recent_commands[-1].action
                elif any(word in text_lower for word in ['yes', 'ok', 'okay', 'sure', 'alright', 'continue', 'proceed']):
                    # Confirmation commands - use last action or default to click
                    if self.context.recent_commands:
                        action = self.context.recent_commands[-1].action
                    else:
                        action = CommandAction.CLICK
                elif any(word in text_lower for word in ['no', 'nope', 'cancel', 'stop', 'halt']):
                    action = CommandAction.WAIT  # Use wait as a "stop" action
                
                # Try to resolve the target using enhanced context resolution
                target = self._enhanced_context_resolution(text_lower)
                if not target:
                    target = self._resolve_context_target()
                
                # Calculate confidence based on context availability and pattern match
                confidence = 0.3  # Base confidence for context commands
                if target:
                    confidence += 0.4
                if self.context.recent_commands:
                    confidence += 0.2
                if self.context.screen_description:
                    confidence += 0.1
                
                # Special handling for confirmation/cancellation commands
                if any(word in text_lower for word in ['yes', 'ok', 'okay', 'sure', 'alright']):
                    confidence += 0.2  # Higher confidence for confirmations
                elif any(word in text_lower for word in ['no', 'nope', 'cancel']):
                    confidence += 0.2  # Higher confidence for cancellations
                
                return ParsedCommand(
                    action=action,
                    target=target,
                    original_text=original_text,
                    context_dependent=True,
                    confidence=min(confidence, 1.0),
                    parameters={'context_type': 'pronoun_reference'}
                )
        
        return None
    
    def _parse_explicit_command(self, original_text: str, text_lower: str) -> Optional[ParsedCommand]:
        """Parse explicit commands with clear targets."""
        best_match = None
        best_confidence = 0.0
        
        for action, patterns in self.command_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    target = match.group(1).strip() if match.groups() else None
                    
                    # Calculate confidence based on pattern specificity and target clarity
                    confidence = self._calculate_confidence(action, target, text_lower)
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        
                        # Process target for better matching
                        processed_target = self._process_target(target) if target else None
                        
                        # Extract parameters for specific actions
                        parameters = self._extract_parameters(action, match, text_lower)
                        
                        best_match = ParsedCommand(
                            action=action,
                            target=processed_target,
                            parameters=parameters,
                            original_text=original_text,
                            confidence=confidence
                        )
        
        return best_match
    
    def _resolve_context_target(self) -> Optional[str]:
        """Enhanced context target resolution with better pronoun handling."""
        # Priority 1: Last explicitly mentioned element
        if self.context.last_mentioned_element:
            return self.context.last_mentioned_element
        
        # Priority 2: Target from most recent successful command
        if self.context.recent_commands:
            for command in reversed(self.context.recent_commands):
                if command.target and command.action != CommandAction.UNKNOWN:
                    return command.target
        
        # Priority 3: Extract from conversation history with better parsing
        if self.context.conversation_history:
            for message in reversed(self.context.conversation_history):
                # Look for explicit element mentions
                elements = self._extract_elements_from_text(message)
                if elements:
                    return elements[0]
                
                # Look for quoted text that might be element labels
                quoted_matches = re.findall(r'["\']([^"\']+)["\']', message)
                if quoted_matches:
                    return quoted_matches[0]
        
        # Priority 4: Extract from current screen description
        if self.context.screen_description:
            elements = self._extract_elements_from_description(self.context.screen_description)
            if elements:
                # Return the most likely interactive element
                interactive_elements = [elem for elem in elements 
                                      if any(ui_type in elem.lower() 
                                           for ui_type in ['button', 'link', 'field', 'input', 'menu'])]
                if interactive_elements:
                    return interactive_elements[0]
                return elements[0]
        
        return None
    
    def _enhanced_context_resolution(self, text_lower: str) -> Optional[str]:
        """Enhanced context resolution for complex pronoun references."""
        # Handle demonstrative pronouns with context
        if re.search(r'\b(?:that|this)\s+(?:one|thing|button|link|field)\b', text_lower):
            return self._resolve_context_target()
        
        # Handle relative references
        if re.search(r'\b(?:same|previous|last)\s+(?:one|thing|button|link)\b', text_lower):
            return self._resolve_context_target()
        
        # Handle action-based references
        if re.search(r'\b(?:it|that|this)\b', text_lower):
            return self._resolve_context_target()
        
        return None
    
    def _calculate_confidence(self, action: CommandAction, target: str, text_lower: str) -> float:
        """Calculate confidence score for a parsed command."""
        confidence = 0.3  # Lower base confidence
        
        # Boost confidence for clear action words
        action_words = {
            CommandAction.CLICK: ['click', 'press', 'tap', 'select'],
            CommandAction.TYPE: ['type', 'enter', 'write', 'input'],
            CommandAction.NAVIGATE: ['go', 'open', 'visit', 'navigate'],
            CommandAction.SCROLL: ['scroll', 'page'],
            CommandAction.READ: ['read', 'tell', 'describe'],
            CommandAction.FIND: ['find', 'search', 'look', 'locate'],
        }
        
        if action in action_words:
            for word in action_words[action]:
                if word in text_lower:
                    confidence += 0.2
                    break
        
        # Boost confidence for specific targets
        if target:
            confidence += 0.2
            
            # Higher confidence for common UI elements
            ui_elements = ['button', 'link', 'field', 'input', 'menu', 'dropdown', 'checkbox']
            if any(element in target.lower() for element in ui_elements):
                confidence += 0.2
            
            # Higher confidence for quoted targets
            if '"' in target or "'" in target:
                confidence += 0.1
        
        # Cap confidence at 1.0
        return min(confidence, 1.0)
    
    def _process_target(self, target: str) -> str:
        """Process and normalize the target string."""
        if not target:
            return target
        
        # Remove quotes
        target = target.strip('"\'')
        
        # Normalize whitespace
        target = re.sub(r'\s+', ' ', target).strip()
        
        # Apply synonyms
        words = target.lower().split()
        normalized_words = []
        for word in words:
            normalized_words.append(self.element_synonyms.get(word, word))
        
        return ' '.join(normalized_words)
    
    def _extract_parameters(self, action: CommandAction, match: re.Match, text_lower: str) -> Optional[Dict[str, Any]]:
        """Extract additional parameters for specific actions."""
        parameters = {}
        
        if action == CommandAction.SCROLL:
            # Extract direction and amount
            if len(match.groups()) >= 1:
                parameters['direction'] = match.group(1)
            
            # Look for numbers in the text for amount
            number_match = re.search(r'(\d+)', text_lower)
            if number_match:
                try:
                    parameters['amount'] = int(number_match.group(1))
                except ValueError:
                    parameters['amount'] = 1
            else:
                parameters['amount'] = 1
        
        elif action == CommandAction.WAIT:
            # Extract duration
            number_match = re.search(r'(\d+)', text_lower)
            if number_match:
                try:
                    duration = int(number_match.group(1))
                    # Convert minutes to seconds if needed
                    if 'minute' in text_lower:
                        duration *= 60
                    parameters['duration'] = duration
                except ValueError:
                    parameters['duration'] = 1
            else:
                parameters['duration'] = 1
        
        elif action == CommandAction.TYPE:
            # Check for special typing instructions
            if 'slowly' in text_lower:
                parameters['speed'] = 'slow'
            elif 'quickly' in text_lower or 'fast' in text_lower:
                parameters['speed'] = 'fast'
            
            if 'clear' in text_lower or 'replace' in text_lower:
                parameters['clear_first'] = True
        
        return parameters if parameters else None
    
    def _extract_elements_from_description(self, description: str) -> List[str]:
        """Extract UI elements from screen description."""
        elements = []
        
        # Common UI element patterns
        element_patterns = [
            r'(\w+)\s+button',
            r'(\w+)\s+link',
            r'(\w+)\s+field',
            r'(\w+)\s+input',
            r'(\w+)\s+menu',
            r'(\w+)\s+dropdown',
            r'(\w+)\s+checkbox',
            r'(\w+)\s+tab',
            r'button\s+(?:labeled|titled|named)\s+["\']([^"\']+)["\']',
            r'link\s+(?:labeled|titled|named)\s+["\']([^"\']+)["\']',
        ]
        
        for pattern in element_patterns:
            matches = re.findall(pattern, description.lower())
            elements.extend(matches)
        
        return list(set(elements))  # Remove duplicates
    
    def _extract_elements_from_text(self, text: str) -> List[str]:
        """Extract UI elements mentioned in text."""
        elements = []
        
        for pattern in self.element_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                if isinstance(matches[0], tuple):
                    elements.extend([match[0] for match in matches])
                else:
                    elements.extend(matches)
        
        return elements
    
    def _generate_suggestions(self, text_lower: str) -> List[str]:
        """Enhanced suggestion generation with better natural language understanding."""
        suggestions = []
        
        # Check for partial matches and suggest completions
        if any(word in text_lower for word in ['click', 'press', 'tap', 'select']):
            suggestions.extend([
                "Try: 'click the [element name]' (e.g., 'click the login button')",
                "Try: 'press the [button name]' (e.g., 'press the submit button')",
                "Try: 'click it' (if you just mentioned an element)",
                "Try: 'click the first button' or 'click the blue button'"
            ])
        
        elif any(word in text_lower for word in ['type', 'enter', 'write', 'input']):
            suggestions.extend([
                "Try: 'type [your text]' (e.g., 'type hello world')",
                "Try: 'enter [text] in the [field name]' (e.g., 'enter my email in the username field')",
                "Try: 'type it' (to type in the last mentioned field)",
                "Try: 'fill in the form with [information]'"
            ])
        
        elif any(word in text_lower for word in ['go', 'open', 'visit', 'navigate']):
            suggestions.extend([
                "Try: 'go to [website]' (e.g., 'go to google.com')",
                "Try: 'open [application or link]' (e.g., 'open the settings page')",
                "Try: 'navigate to [location]' (e.g., 'navigate to the homepage')",
                "Try: 'visit [website]' (e.g., 'visit youtube.com')"
            ])
        
        elif any(word in text_lower for word in ['scroll', 'move', 'page']):
            suggestions.extend([
                "Try: 'scroll down' or 'scroll up'",
                "Try: 'scroll down 3' (to scroll multiple times)",
                "Try: 'page down' or 'page up'",
                "Try: 'scroll to the bottom' or 'scroll to the top'"
            ])
        
        elif any(word in text_lower for word in ['read', 'tell', 'describe', 'what']):
            suggestions.extend([
                "Try: 'read the [element name]' (e.g., 'read the first paragraph')",
                "Try: 'tell me about [element]' (e.g., 'tell me about the menu')",
                "Try: 'describe the page' or 'read the screen'",
                "Try: 'what does the [element] say?' (e.g., 'what does the error message say?')"
            ])
        
        elif any(word in text_lower for word in ['find', 'search', 'look', 'locate', 'where']):
            suggestions.extend([
                "Try: 'find the [element name]' (e.g., 'find the search box')",
                "Try: 'search for [text]' (e.g., 'search for the login button')",
                "Try: 'where is the [element]?' (e.g., 'where is the menu?')",
                "Try: 'locate the [element]' (e.g., 'locate the submit button')"
            ])
        
        elif any(word in text_lower for word in ['and', 'then', 'after']):
            suggestions.extend([
                "Try compound commands like: 'scroll down and read the first paragraph'",
                "Try: 'click the menu and then select settings'",
                "Try: 'type my name and press enter'",
                "Try: 'find the search box and type hello world'"
            ])
        
        else:
            # General suggestions based on common patterns
            if len(text_lower.split()) == 1:
                # Single word - might be incomplete
                suggestions.extend([
                    "Try adding more details: 'click the [element]', 'type [text]', 'go to [website]'",
                    "Use complete commands like: 'scroll down', 'read the page', 'find the button'",
                    "For context commands, try: 'click it', 'type in it', 'read it'"
                ])
            else:
                # Multi-word but not recognized
                suggestions.extend([
                    "Try commands like: 'click the button', 'type hello', 'scroll down'",
                    "Use 'it' to refer to recently mentioned elements",
                    "Combine commands with 'and': 'scroll down and read the first paragraph'",
                    "Be specific: 'click the blue button' or 'type in the search field'"
                ])
        
        # Add context-specific suggestions if we have context
        if self.context.last_mentioned_element:
            suggestions.append(f"Try: 'click it' (referring to {self.context.last_mentioned_element})")
        
        if self.context.recent_commands:
            last_action = self.context.recent_commands[-1].action.value
            suggestions.append(f"Try: 'do that again' (to repeat the last {last_action} action)")
        
        return suggestions[:4]  # Return top 4 suggestions
    
    def get_command_help(self) -> Dict[str, List[str]]:
        """Get help information about supported commands."""
        return {
            "Click/Press/Tap": [
                "click the button",
                "press the login button", 
                "tap the menu",
                "select the first option",
                "click it (refers to last mentioned element)"
            ],
            "Type/Enter": [
                "type hello world",
                "enter my email address",
                "write a message",
                "input the password"
            ],
            "Navigate": [
                "go to google.com",
                "open the settings page",
                "visit the homepage",
                "navigate to the next page"
            ],
            "Scroll": [
                "scroll down",
                "scroll up 3",
                "page down",
                "move to the bottom"
            ],
            "Read/Describe": [
                "read the page",
                "tell me about the button",
                "describe the menu",
                "what does the error message say"
            ],
            "Find/Search": [
                "find the search box",
                "locate the submit button",
                "where is the menu",
                "search for the login link"
            ],
            "Compound Commands": [
                "scroll down and read the first paragraph",
                "click the menu and then select settings",
                "type my name and press enter"
            ]
        }
    
    def format_command_for_execution(self, command: ParsedCommand) -> Dict[str, Any]:
        """Format a parsed command for execution by the action system."""
        if command.action == CommandAction.UNKNOWN:
            return {
                "type": "error",
                "message": "Command not recognized",
                "suggestions": command.suggestions or []
            }
        
        execution_format = {
            "type": "command",
            "action": command.action.value,
            "target": command.target,
            "parameters": command.parameters or {},
            "confidence": command.confidence,
            "context_dependent": command.context_dependent,
            "original_text": command.original_text
        }
        
        # Handle compound commands
        if command.compound and command.sub_commands:
            execution_format["type"] = "compound_command"
            execution_format["sub_commands"] = [
                self.format_command_for_execution(sub_cmd) 
                for sub_cmd in command.sub_commands
            ]
        
        return execution_format