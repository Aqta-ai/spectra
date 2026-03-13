"""
Location Context Handler for Spectra Accessibility Enhancement

This module provides specialized handling for location queries from blind and visually impaired users.
When users ask "where am I?", they typically want to know what website or application they're currently
viewing, not their physical GPS location.

Key Features:
- Detects location-related queries
- Triggers fresh screen analysis for location queries
- Extracts website/app information from screen content
- Provides clear fallback messages when location cannot be determined
"""

import re
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LocationInfo:
    """Structured information about the user's current digital location."""
    site_name: Optional[str] = None
    url: Optional[str] = None
    app_name: Optional[str] = None
    page_title: Optional[str] = None
    context: Optional[str] = None
    confidence: float = 0.0


class LocationContextHandler:
    """
    Handles location queries by analyzing screen content to determine what website
    or application the user is currently viewing.
    
    This class is specifically designed for accessibility users who need to understand
    their digital location context through voice interaction.
    """
    
    def __init__(self):
        """Initialize the LocationContextHandler with query patterns and site indicators."""
        
        # Patterns that indicate a location query
        self.location_query_patterns = [
            r'\bwhere am i\b',
            r'\bwhat site am i on\b',
            r'\bwhat website is this\b',
            r'\bwhat app am i in\b',
            r'\bwhat page is this\b',
            r'\bwhere are we\b',
            r'\bwhat application is this\b',
            r'\bwhat program is this\b',
            r'\bwhat browser tab is this\b'
        ]
        
        # Common website indicators for pattern matching
        self.website_indicators = {
            'google': {
                'patterns': [r'google\.com', r'google search', r'search google', r'google logo', r'google homepage', r'\bgoogle\b', r'search bar.*google', r'google.*search engine'],
                'name': 'Google',
                'contexts': ['search engine', 'homepage', 'search results'],
                'ui_patterns': [r'search bar', r'search button', r'i\'m feeling lucky', r'google apps']
            },
            'gmail': {
                'patterns': [r'gmail\.com', r'gmail', r'google mail', r'inbox.*gmail', r'compose.*gmail'],
                'name': 'Gmail',
                'contexts': ['email', 'inbox', 'compose'],
                'ui_patterns': [r'compose', r'inbox', r'sent', r'drafts', r'starred', r'important', r'spam', r'trash']
            },
            'youtube': {
                'patterns': [r'youtube\.com', r'youtube', r'watch\?v=', r'youtube.*video', r'video.*youtube'],
                'name': 'YouTube',
                'contexts': ['video platform', 'video player', 'channel'],
                'ui_patterns': [r'play button', r'video player', r'subscribe', r'like.*dislike', r'comments', r'playlist']
            },
            'facebook': {
                'patterns': [r'facebook\.com', r'facebook', r'fb\.com', r'news feed', r'facebook.*profile'],
                'name': 'Facebook',
                'contexts': ['social media', 'news feed', 'profile'],
                'ui_patterns': [r'news feed', r'timeline', r'like.*comment.*share', r'friend requests', r'notifications']
            },
            'twitter': {
                'patterns': [r'twitter\.com', r'twitter', r'x\.com', r'tweet', r'timeline.*twitter'],
                'name': 'Twitter/X',
                'contexts': ['social media', 'timeline', 'tweet'],
                'ui_patterns': [r'tweet', r'retweet', r'like', r'reply', r'follow', r'trending', r'what\'s happening']
            },
            'linkedin': {
                'patterns': [r'linkedin\.com', r'linkedin', r'professional.*network'],
                'name': 'LinkedIn',
                'contexts': ['professional network', 'profile', 'feed'],
                'ui_patterns': [r'connections', r'jobs', r'messaging', r'notifications', r'my network', r'home feed']
            },
            'amazon': {
                'patterns': [r'amazon\.com', r'amazon', r'aws\.amazon', r'shopping.*amazon', r'buy.*amazon'],
                'name': 'Amazon',
                'contexts': ['shopping', 'product page', 'cart'],
                'ui_patterns': [r'add to cart', r'buy now', r'prime', r'wishlist', r'your account', r'orders', r'search products']
            },
            'github': {
                'patterns': [r'github\.com', r'github', r'repository.*github', r'code.*github'],
                'name': 'GitHub',
                'contexts': ['code repository', 'project', 'issues'],
                'ui_patterns': [r'repository', r'issues', r'pull requests', r'actions', r'projects', r'wiki', r'insights', r'fork', r'star']
            },
            'stackoverflow': {
                'patterns': [r'stackoverflow\.com', r'stack overflow', r'programming.*question'],
                'name': 'Stack Overflow',
                'contexts': ['programming Q&A', 'question', 'answer'],
                'ui_patterns': [r'ask question', r'vote up', r'vote down', r'accepted answer', r'tags', r'reputation']
            },
            'wikipedia': {
                'patterns': [r'wikipedia\.org', r'wikipedia', r'encyclopedia.*article'],
                'name': 'Wikipedia',
                'contexts': ['encyclopedia', 'article', 'reference'],
                'ui_patterns': [r'table of contents', r'references', r'external links', r'categories', r'edit', r'history']
            },
            'reddit': {
                'patterns': [r'reddit\.com', r'reddit', r'subreddit', r'r/'],
                'name': 'Reddit',
                'contexts': ['social news', 'discussion', 'community'],
                'ui_patterns': [r'upvote', r'downvote', r'comments', r'share', r'save', r'subreddit', r'post']
            },
            'instagram': {
                'patterns': [r'instagram\.com', r'instagram', r'insta'],
                'name': 'Instagram',
                'contexts': ['photo sharing', 'social media', 'stories'],
                'ui_patterns': [r'stories', r'reels', r'explore', r'activity', r'direct', r'profile', r'following']
            },
            'netflix': {
                'patterns': [r'netflix\.com', r'netflix', r'streaming.*netflix'],
                'name': 'Netflix',
                'contexts': ['streaming', 'movies', 'TV shows'],
                'ui_patterns': [r'my list', r'continue watching', r'trending now', r'play', r'add to list', r'rate']
            },
            'spotify': {
                'patterns': [r'spotify\.com', r'spotify', r'music.*spotify'],
                'name': 'Spotify',
                'contexts': ['music streaming', 'playlists', 'podcasts'],
                'ui_patterns': [r'play', r'pause', r'skip', r'playlist', r'library', r'search music', r'now playing']
            },
            'discord': {
                'patterns': [r'discord\.com', r'discord', r'chat.*discord'],
                'name': 'Discord',
                'contexts': ['chat', 'voice', 'gaming'],
                'ui_patterns': [r'servers', r'channels', r'direct messages', r'voice channel', r'text channel', r'members']
            }
        }
        
        # Common application indicators
        self.app_indicators = {
            'chrome': {
                'patterns': [r'google chrome', r'chrome browser', r'chrome.*tab', r'address bar.*chrome'],
                'name': 'Google Chrome',
                'ui_patterns': [r'address bar', r'bookmarks bar', r'new tab', r'extensions', r'settings', r'history']
            },
            'firefox': {
                'patterns': [r'mozilla firefox', r'firefox', r'firefox.*browser'],
                'name': 'Mozilla Firefox',
                'ui_patterns': [r'address bar', r'bookmarks toolbar', r'new tab', r'add-ons', r'preferences']
            },
            'safari': {
                'patterns': [r'safari', r'safari.*browser'],
                'name': 'Safari',
                'ui_patterns': [r'address bar', r'bookmarks', r'reading list', r'history', r'preferences']
            },
            'edge': {
                'patterns': [r'microsoft edge', r'edge', r'edge.*browser'],
                'name': 'Microsoft Edge',
                'ui_patterns': [r'address bar', r'favorites', r'collections', r'history', r'settings']
            },
            'vscode': {
                'patterns': [r'visual studio code', r'vscode', r'vs code', r'code editor'],
                'name': 'Visual Studio Code',
                'ui_patterns': [r'explorer', r'search', r'source control', r'run and debug', r'extensions', r'terminal', r'file tree']
            },
            'word': {
                'patterns': [r'microsoft word', r'word', r'document.*word'],
                'name': 'Microsoft Word',
                'ui_patterns': [r'ribbon', r'home tab', r'insert tab', r'page layout', r'references', r'review', r'view']
            },
            'excel': {
                'patterns': [r'microsoft excel', r'excel', r'spreadsheet.*excel'],
                'name': 'Microsoft Excel',
                'ui_patterns': [r'worksheet', r'cells', r'formulas', r'charts', r'pivot table', r'data tab', r'home tab']
            },
            'powerpoint': {
                'patterns': [r'microsoft powerpoint', r'powerpoint', r'presentation.*powerpoint'],
                'name': 'Microsoft PowerPoint',
                'ui_patterns': [r'slides', r'slide thumbnail', r'design tab', r'transitions', r'animations', r'slide show']
            },
            'outlook': {
                'patterns': [r'microsoft outlook', r'outlook', r'email.*outlook'],
                'name': 'Microsoft Outlook',
                'ui_patterns': [r'inbox', r'sent items', r'calendar', r'contacts', r'tasks', r'new email', r'reply']
            },
            'teams': {
                'patterns': [r'microsoft teams', r'teams', r'video.*call.*teams'],
                'name': 'Microsoft Teams',
                'ui_patterns': [r'chat', r'teams', r'calendar', r'calls', r'files', r'activity', r'apps']
            },
            'zoom': {
                'patterns': [r'zoom meeting', r'zoom', r'video.*conference.*zoom'],
                'name': 'Zoom',
                'ui_patterns': [r'mute', r'video', r'share screen', r'participants', r'chat', r'reactions', r'leave meeting']
            },
            'slack': {
                'patterns': [r'slack', r'workspace.*slack', r'channels.*slack'],
                'name': 'Slack',
                'ui_patterns': [r'channels', r'direct messages', r'activity', r'search', r'threads', r'mentions']
            },
            'discord': {
                'patterns': [r'discord', r'voice.*chat.*discord'],
                'name': 'Discord',
                'ui_patterns': [r'servers', r'channels', r'direct messages', r'voice channel', r'text channel', r'members']
            },
            'photoshop': {
                'patterns': [r'adobe photoshop', r'photoshop', r'image.*editor.*photoshop'],
                'name': 'Adobe Photoshop',
                'ui_patterns': [r'layers', r'tools', r'canvas', r'brushes', r'filters', r'adjustments']
            },
            'illustrator': {
                'patterns': [r'adobe illustrator', r'illustrator', r'vector.*graphics'],
                'name': 'Adobe Illustrator',
                'ui_patterns': [r'artboard', r'tools', r'layers', r'swatches', r'brushes', r'symbols']
            },
            'figma': {
                'patterns': [r'figma', r'design.*tool.*figma'],
                'name': 'Figma',
                'ui_patterns': [r'canvas', r'layers', r'properties', r'components', r'assets', r'prototype']
            },
            'notion': {
                'patterns': [r'notion', r'workspace.*notion', r'notes.*notion'],
                'name': 'Notion',
                'ui_patterns': [r'sidebar', r'page', r'blocks', r'database', r'templates', r'sharing']
            },
            'trello': {
                'patterns': [r'trello', r'board.*trello', r'cards.*trello'],
                'name': 'Trello',
                'ui_patterns': [r'boards', r'lists', r'cards', r'members', r'due dates', r'checklists']
            }
        }
    
    def is_location_query(self, query: str) -> bool:
        """
        Determine if the user's query is asking about their current location.
        
        Args:
            query: The user's input text
            
        Returns:
            True if this is a location query, False otherwise
        """
        if not query:
            return False
            
        query_lower = query.lower().strip()
        
        # Check against all location query patterns
        for pattern in self.location_query_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"Location query detected: '{query}' matched pattern '{pattern}'")
                return True
        
        return False
    
    def extract_location_info(self, screen_description: str) -> LocationInfo:
        """
        Extract location information from a screen description with enhanced pattern matching.
        
        Args:
            screen_description: The description of the current screen content
            
        Returns:
            LocationInfo object with extracted information
        """
        if not screen_description:
            return LocationInfo()
        
        description_lower = screen_description.lower()
        location_info = LocationInfo()
        
        # Extract website information
        website_info = self._extract_website_info(description_lower)
        if website_info:
            location_info.site_name = website_info['name']
            location_info.context = website_info.get('context', '')
            location_info.confidence = website_info.get('confidence', 0.0)
        
        # Extract logo information to boost confidence or provide fallback
        logo_info = self._extract_logo_info(screen_description)
        if logo_info and logo_info['confidence'] > 0.7:
            # If logo detection has higher confidence, use it
            if not location_info.site_name or logo_info['confidence'] > location_info.confidence:
                brand_name = logo_info['brand'].title()
                # Map brand names to proper site names
                brand_mapping = {
                    'Google': 'Google',
                    'Facebook': 'Facebook',
                    'Twitter': 'Twitter/X',
                    'Youtube': 'YouTube',
                    'Linkedin': 'LinkedIn',
                    'Instagram': 'Instagram',
                    'Amazon': 'Amazon',
                    'Netflix': 'Netflix',
                    'Spotify': 'Spotify'
                }
                location_info.site_name = brand_mapping.get(brand_name, brand_name)
                location_info.confidence = max(location_info.confidence, logo_info['confidence'])
        
        # Extract URL information
        url_info = self._extract_url_info(screen_description)
        if url_info:
            location_info.url = url_info
            if not location_info.site_name:
                location_info.site_name = self._domain_from_url(url_info)
            location_info.confidence = max(location_info.confidence, 0.8)
        
        # Extract application information
        app_info = self._extract_app_info(description_lower)
        if app_info:
            location_info.app_name = app_info['name']
            if not location_info.context:
                location_info.context = 'application'
            location_info.confidence = max(location_info.confidence, app_info['confidence'])
        
        # Extract page title information
        title_info = self._extract_title_info(screen_description)
        if title_info:
            location_info.page_title = title_info
            location_info.confidence = max(location_info.confidence, 0.6)
        
        logger.info(f"Extracted location info: {location_info}")
        return location_info
    
    def format_location_response(self, location_info: LocationInfo, fallback_description: str = "") -> str:
        """
        Format a user-friendly response about the user's current location.
        
        Args:
            location_info: The extracted location information
            fallback_description: Optional fallback description if location cannot be determined
            
        Returns:
            A formatted response string
        """
        # If we have high-confidence location information
        if location_info.confidence >= 0.7:
            if location_info.site_name and location_info.url:
                response = f"You're on {location_info.site_name}"
                if location_info.context:
                    response += f" - {location_info.context}"
                return response
            elif location_info.site_name:
                response = f"You're on {location_info.site_name}"
                if location_info.context:
                    response += f" - {location_info.context}"
                return response
            elif location_info.app_name:
                return f"You're in {location_info.app_name}"
        
        # If we have medium-confidence information
        if location_info.confidence >= 0.5:
            if location_info.page_title:
                return f"You're on a page titled '{location_info.page_title}'"
            elif location_info.url:
                domain = self._domain_from_url(location_info.url)
                return f"You're on {domain}"
        
        # Fallback responses
        if fallback_description and len(fallback_description) > 50:
            # Try to extract basic information from the description
            basic_info = self._extract_basic_info(fallback_description)
            if basic_info:
                return f"You're viewing {basic_info}"
        
        # Final fallback
        return "I can see your screen but cannot determine the specific website or application"
    
    def _extract_website_info(self, description_lower: str) -> Optional[Dict[str, Any]]:
        """Extract website information from screen description using enhanced pattern matching."""
        best_match = None
        best_confidence = 0.0
        
        for site_key, site_info in self.website_indicators.items():
            confidence = 0.0
            matched_patterns = 0
            matched_ui_patterns = 0
            
            # Check main patterns
            for pattern in site_info['patterns']:
                if re.search(pattern, description_lower):
                    confidence += 0.7  # Higher base confidence for pattern match
                    matched_patterns += 1
            
            # Check UI patterns if available
            if 'ui_patterns' in site_info:
                for ui_pattern in site_info['ui_patterns']:
                    if re.search(ui_pattern, description_lower):
                        confidence += 0.15  # Additional confidence for UI pattern match
                        matched_ui_patterns += 1
            
            # Boost confidence for multiple matches
            if matched_patterns > 1:
                confidence += min(0.1 * (matched_patterns - 1), 0.2)
            
            if matched_ui_patterns > 0:
                confidence += min(0.05 * matched_ui_patterns, 0.15)
            
            # Cap confidence at 1.0
            confidence = min(confidence, 1.0)
            
            if confidence > best_confidence and confidence >= 0.7:  # Minimum threshold for websites
                best_confidence = confidence
                best_match = {
                    'name': site_info['name'],
                    'confidence': confidence,
                    'context': self._determine_context(description_lower, site_info['contexts']),
                    'matched_patterns': matched_patterns,
                    'matched_ui_patterns': matched_ui_patterns
                }
        
        return best_match
    
    def _extract_url_info(self, description: str) -> Optional[str]:
        """Extract URL information from screen description."""
        # Look for URL patterns in the description
        url_patterns = [
            r'https?://[^\s]+',
            r'www\.[^\s]+',
            r'[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, description)
            if matches:
                # Return the first URL found
                return matches[0].rstrip('.,;:)')
        
        return None
    
    def _extract_app_info(self, description_lower: str) -> Optional[Dict[str, Any]]:
        """Extract application information from screen description using enhanced pattern matching."""
        best_match = None
        best_confidence = 0.0
        
        for app_key, app_info in self.app_indicators.items():
            confidence = 0.0
            matched_patterns = 0
            matched_ui_patterns = 0
            
            # Check main patterns
            for pattern in app_info['patterns']:
                if re.search(pattern, description_lower):
                    confidence += 0.4  # Base confidence for app pattern match
                    matched_patterns += 1
            
            # Check UI patterns if available
            if 'ui_patterns' in app_info:
                for ui_pattern in app_info['ui_patterns']:
                    if re.search(ui_pattern, description_lower):
                        confidence += 0.15  # Additional confidence for UI pattern match
                        matched_ui_patterns += 1
            
            # Boost confidence for multiple matches
            if matched_patterns > 1:
                confidence += min(0.1 * (matched_patterns - 1), 0.2)
            
            if matched_ui_patterns > 0:
                confidence += min(0.05 * matched_ui_patterns, 0.15)
            
            # Cap confidence at 1.0
            confidence = min(confidence, 1.0)
            
            if confidence > best_confidence and confidence >= 0.4:  # Minimum threshold for apps
                best_confidence = confidence
                best_match = {
                    'name': app_info['name'],
                    'confidence': confidence,
                    'matched_patterns': matched_patterns,
                    'matched_ui_patterns': matched_ui_patterns
                }
        
        return best_match
    
    def _extract_title_info(self, description: str) -> Optional[str]:
        """Extract page title information from screen description with enhanced patterns."""
        # Look for title patterns with improved regex
        title_patterns = [
            r'title:\s*([^\n\r\|]+)',  # "title: Page Title"
            r'page title:\s*([^\n\r\|]+)',  # "page title: Page Title"
            r'heading:\s*([^\n\r\|]+)',  # "heading: Page Title"
            r'window title:\s*([^\n\r\|]+)',  # "window title: App Name"
            r'^([^-\n\r\|]{5,60})\s*[-\|]\s*[^-\n\r\|]+',  # "Page Title - Site Name" or "Page Title | Site Name"
            r'tab.*?title:\s*([^\n\r\|]+)',  # "tab title: Page Title"
            r'browser.*?title:\s*([^\n\r\|]+)',  # "browser title: Page Title"
            r'document.*?title:\s*([^\n\r\|]+)',  # "document title: Document Name"
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, description, re.IGNORECASE | re.MULTILINE)
            if match:
                title = match.group(1).strip()
                # Clean up common title artifacts
                title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
                title = title.strip('.,;:()[]{}')  # Remove trailing punctuation
                
                # Validate title length and content
                if 5 <= len(title) <= 100 and not self._is_generic_title(title):
                    return title
        
        return None
    
    def _is_generic_title(self, title: str) -> bool:
        """Check if a title is too generic to be useful."""
        generic_titles = [
            'untitled', 'new document', 'new tab', 'blank page', 'loading',
            'error', 'not found', '404', 'home', 'default'
        ]
        title_lower = title.lower().strip()
        
        # Check for exact matches or very short titles that are just the generic word
        for generic in generic_titles:
            if title_lower == generic or (len(title_lower) <= len(generic) + 2 and generic in title_lower):
                return True
        
        # Special case: "welcome" alone is generic, but "Welcome to X" is not
        if title_lower == 'welcome':
            return True
            
        return False
    
    def _extract_logo_info(self, description: str) -> Optional[Dict[str, Any]]:
        """Extract logo and visual brand indicators from screen description."""
        logo_patterns = {
            'google': [r'google logo', r'google.*icon', r'colorful.*g.*logo', r'search.*logo.*google'],
            'facebook': [r'facebook logo', r'fb.*logo', r'blue.*f.*logo', r'meta.*logo'],
            'twitter': [r'twitter logo', r'bird.*logo', r'x.*logo', r'blue.*bird'],
            'youtube': [r'youtube logo', r'play.*button.*logo', r'red.*play.*button'],
            'linkedin': [r'linkedin logo', r'\bin.*logo\b', r'professional.*network.*logo'],
            'instagram': [r'instagram logo', r'camera.*logo', r'insta.*logo'],
            'amazon': [r'amazon logo', r'smile.*logo', r'arrow.*logo.*amazon', r'amazon.*smile.*arrow'],
            'apple': [r'apple logo', r'bitten.*apple', r'apple.*icon'],
            'microsoft': [r'microsoft logo', r'windows.*logo', r'four.*squares.*logo'],
            'netflix': [r'netflix logo', r'red.*n.*logo', r'netflix.*icon'],
            'spotify': [r'spotify logo', r'green.*circle.*logo', r'music.*logo.*spotify']
        }
        
        description_lower = description.lower()
        best_match = None
        best_confidence = 0.0
        
        for brand, patterns in logo_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description_lower):
                    confidence = 0.8  # High confidence for logo detection
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = {
                            'brand': brand,
                            'confidence': confidence,
                            'type': 'logo'
                        }
                        break
        
        return best_match
    
    def _determine_context(self, description_lower: str, contexts: List[str]) -> str:
        """Determine the most appropriate context from available options."""
        for context in contexts:
            if context.lower() in description_lower:
                return context
        
        # Return the first context as default
        return contexts[0] if contexts else ""
    
    def _domain_from_url(self, url: str) -> str:
        """Extract domain name from URL."""
        # Remove protocol
        url = re.sub(r'^https?://', '', url)
        # Remove www prefix
        url = re.sub(r'^www\.', '', url)
        # Extract domain (everything before first slash or space)
        domain = url.split('/')[0].split(' ')[0]
        return domain
    
    def _extract_basic_info(self, description: str) -> Optional[str]:
        """Extract basic information when specific patterns don't match."""
        # Look for common page elements that might indicate content type
        basic_patterns = [
            (r'search results', 'search results'),
            (r'shopping', 'a shopping page'),
            (r'news', 'a news page'),
            (r'article', 'an article'),
            (r'blog', 'a blog'),
            (r'forum', 'a forum'),
            (r'login', 'a login page'),
            (r'sign in', 'a sign-in page'),
            (r'dashboard', 'a dashboard'),
            (r'profile', 'a profile page'),
            (r'settings', 'a settings page'),
            (r'home', 'a homepage'),
            (r'contact', 'a contact page'),
            (r'about', 'an about page'),
            (r'video.*player', 'a video player'),
            (r'music.*player', 'a music player'),
            (r'streaming', 'a streaming service'),
            (r'social.*media', 'a social media platform'),
            (r'email.*client', 'an email application'),
            (r'text.*editor', 'a text editor'),
            (r'code.*editor', 'a code editor'),
            (r'spreadsheet', 'a spreadsheet application'),
            (r'presentation', 'a presentation application'),
            (r'document.*editor', 'a document editor'),
            (r'web.*browser', 'a web browser'),
            (r'file.*manager', 'a file manager'),
            (r'calendar', 'a calendar application'),
            (r'chat.*application', 'a chat application'),
            (r'video.*conference', 'a video conferencing application'),
            (r'design.*tool', 'a design application'),
            (r'photo.*editor', 'a photo editing application'),
            (r'game', 'a game'),
            (r'e-commerce', 'an e-commerce site'),
            (r'online.*store', 'an online store'),
            (r'marketplace', 'a marketplace'),
            (r'learning.*platform', 'a learning platform'),
            (r'documentation', 'documentation'),
            (r'wiki', 'a wiki'),
            (r'knowledge.*base', 'a knowledge base')
        ]
        
        description_lower = description.lower()
        for pattern, description_text in basic_patterns:
            if re.search(pattern, description_lower):
                return description_text
        
        return None

    async def handle_location_query(self, query: str, screen_description: str) -> Optional[str]:
        """
        Handle a location query by analyzing screen content and returning a formatted response.
        
        This is the main entry point for processing location queries.
        
        Args:
            query: The user's query text
            screen_description: The current screen description from vision analysis
            
        Returns:
            A formatted location response, or None if this is not a location query
        """
        if not self.is_location_query(query):
            return None
        
        logger.info(f"Processing location query: '{query}'")
        
        # Extract location information from screen description
        location_info = self.extract_location_info(screen_description)
        
        # Format and return the response
        response = self.format_location_response(location_info, screen_description)
        
        logger.info(f"Location query response: '{response}'")
        return response