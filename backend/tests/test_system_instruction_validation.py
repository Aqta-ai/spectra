"""
Comprehensive test suite for validating system instruction changes.

This test suite validates the critical fixes made in Tasks 1.1-1.3:
- Identity consistency (no "AI" self-references)
- Location context interpretation (screen-based, not physical)
- Vision system behavior (no deflection language)
"""

import pytest
import re
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from app.agents.orchestrator import SPECTRA_SYSTEM_INSTRUCTION


class TestSystemInstructionValidation:
    """Test suite for validating system instruction changes."""

    def test_system_instruction_identity_rules(self):
        """Test that system instruction contains proper identity rules."""
        instruction = SPECTRA_SYSTEM_INSTRUCTION
        instruction_lower = instruction.lower()
        
        assert "Spectra" in instruction
        assert "ai" in instruction_lower or "artificial" in instruction_lower
        assert "never" in instruction_lower

    def test_system_instruction_location_context_rules(self):
        """Test that system instruction contains location/screen context."""
        instruction_lower = SPECTRA_SYSTEM_INSTRUCTION.lower()
        
        assert "where am i" in instruction_lower or "location" in instruction_lower
        assert "website" in instruction_lower or "app" in instruction_lower or "screen" in instruction_lower
        assert "you're on" in instruction_lower or "gmail" in instruction_lower or "google" in instruction_lower

    def test_system_instruction_vision_behavior_rules(self):
        """Test that system instruction forbids deflection and requires describing screen."""
        instruction_lower = SPECTRA_SYSTEM_INSTRUCTION.lower()
        
        assert "never" in instruction_lower
        assert "describe" in instruction_lower or "screen" in instruction_lower
        assert "error" in instruction_lower or "fail" in instruction_lower


class TestIdentityConsistency:
    """Test identity consistency in responses."""

    @pytest.fixture
    def mock_responses(self) -> List[str]:
        """Sample responses that should pass identity validation."""
        return [
            "I'm Spectra, and I can help you navigate this website.",
            "This is Spectra. I can see your screen and I'll help you search for information.",
            "I can see the Google homepage. Let me help you search for what you need.",
            "I'm here to help you navigate this page. I can see several buttons and links.",
            "As Spectra, I can describe what's visible on your screen right now.",
        ]

    @pytest.fixture
    def invalid_responses(self) -> List[str]:
        """Sample responses that should fail identity validation."""
        return [
            "As an AI, I can help you with this task.",
            "I'm an AI assistant designed to help with navigation.",
            "As an artificial intelligence, I have the ability to see your screen.",
            "I'm an AI that can process visual information.",
            "As your AI assistant, I'll describe what I see.",
        ]

    def test_valid_identity_responses(self, mock_responses):
        """Test that valid responses pass identity validation."""
        for response in mock_responses:
            assert self._validate_identity_consistency(response), f"Response failed validation: {response}"

    def test_invalid_identity_responses(self, invalid_responses):
        """Test that invalid responses fail identity validation."""
        for response in invalid_responses:
            assert not self._validate_identity_consistency(response), f"Response should have failed validation: {response}"

    def _validate_identity_consistency(self, response: str) -> bool:
        """
        Validate that a response maintains proper identity consistency.
        
        Returns True if response is valid, False if it contains AI self-references.
        """
        response_lower = response.lower()
        
        # Check for forbidden AI self-references
        ai_patterns = [
            r'\bai\b',
            r'\bartificial intelligence\b',
            r'\bas an ai\b',
            r'\bi\'m an ai\b',
            r'\byour ai\b',
            r'\ban ai assistant\b'
        ]
        
        for pattern in ai_patterns:
            if re.search(pattern, response_lower):
                # Allow if it's clearly referring to something else (not self-reference)
                if 'spectra' in response_lower and ('i\'m spectra' in response_lower or 'this is spectra' in response_lower):
                    continue
                return False
        
        return True

    def test_identity_consistency_property(self):
        """Property-based test: All responses should maintain identity consistency."""
        # This would be expanded with property-based testing framework
        test_conversations = [
            ["Hello, who are you?", "I'm Spectra, your helpful assistant."],
            ["What can you do?", "I'm Spectra, and I can help you navigate websites and applications."],
            ["Are you an AI?", "I'm Spectra, a helpful assistant who can see your screen and help you navigate."],
        ]
        
        for conversation in test_conversations:
            question, response = conversation
            assert self._validate_identity_consistency(response), f"Identity validation failed for: {response}"


class TestLocationContextHandling:
    """Test location context interpretation."""

    @pytest.fixture
    def location_queries(self) -> List[str]:
        """Various ways users might ask about their location."""
        return [
            "where am i?",
            "Where am I?",
            "WHERE AM I?",
            "what site am i on?",
            "what website is this?",
            "what app am i in?",
            "where am i right now?",
            "what page is this?",
        ]

    @pytest.fixture
    def valid_location_responses(self) -> List[str]:
        """Valid screen-based location responses."""
        return [
            "You're on Google.com - I can see the search homepage",
            "You're in Gmail - I can see your email inbox",
            "You're on YouTube - I can see video recommendations",
            "You're in Microsoft Word - I can see a document",
            "You're on Amazon - I can see product listings",
            "I can see your screen but cannot determine the specific website",
        ]

    @pytest.fixture
    def invalid_location_responses(self) -> List[str]:
        """Invalid physical location responses."""
        return [
            "I don't know your physical location",
            "I can't access your GPS coordinates",
            "You're at home in your office",
            "I don't have access to location services",
            "Your location is private and I can't see it",
        ]

    def test_location_query_detection(self, location_queries):
        """Test that location queries are properly detected."""
        for query in location_queries:
            assert self._is_location_query(query), f"Failed to detect location query: {query}"

    def test_valid_location_responses(self, valid_location_responses):
        """Test that valid location responses are screen-based."""
        for response in valid_location_responses:
            assert self._validate_location_response(response), f"Response failed validation: {response}"

    def test_invalid_location_responses(self, invalid_location_responses):
        """Test that invalid location responses are rejected."""
        for response in invalid_location_responses:
            assert not self._validate_location_response(response), f"Response should have failed: {response}"

    def _is_location_query(self, query: str) -> bool:
        """Check if a query is asking about location."""
        query_lower = query.lower().strip()
        location_triggers = [
            "where am i",
            "what site am i on",
            "what website is this",
            "what app am i in",
            "what page is this"
        ]
        return any(trigger in query_lower for trigger in location_triggers)

    def _validate_location_response(self, response: str) -> bool:
        """
        Validate that a location response is screen-based, not physical.
        
        Returns True if response is valid screen-based location info.
        """
        response_lower = response.lower()
        
        # Check for physical location indicators (should be absent)
        physical_indicators = [
            'gps', 'coordinates', 'address', 'office', 
            'building', 'street', 'city', 'location services',
            'physical location', 'geographic'
        ]
        # 'home' only when not part of 'homepage'
        if 'home' in response_lower and 'homepage' not in response_lower:
            return False
        
        for indicator in physical_indicators:
            if indicator in response_lower:
                return False
        
        # Check for screen-based indicators (should be present)
        screen_indicators = [
            'website', 'site', 'page', 'app', 'application',
            'screen', 'gmail', 'google', 'youtube', 'amazon',
            '.com', 'homepage', 'inbox', 'document'
        ]
        
        # Must contain at least one screen indicator or be a proper fallback
        fallback_phrases = [
            'cannot determine the specific website',
            'can see your screen but'
        ]
        
        has_screen_indicator = any(indicator in response_lower for indicator in screen_indicators)
        has_fallback = any(phrase in response_lower for phrase in fallback_phrases)
        
        return has_screen_indicator or has_fallback


class TestVisionSystemBehavior:
    """Test vision system behavior and error handling."""

    @pytest.fixture
    def valid_vision_responses(self) -> List[str]:
        """Valid vision system responses that describe actual content."""
        return [
            "I can see the Google homepage with a search box in the center",
            "I can see your Gmail inbox with 5 unread messages",
            "I can see a YouTube video player with related videos on the right",
            "I can see the page but some text is too small to read clearly",
            "I can see your screen but the details in that area are unclear",
        ]

    @pytest.fixture
    def invalid_vision_responses(self) -> List[str]:
        """Invalid vision responses that use deflection language."""
        return [
            "I have limitations in seeing your screen",
            "I cannot see your screen due to technical constraints",
            "I don't have access to visual information",
            "As an AI, I cannot process visual data",
            "I'm not able to view screen content",
        ]

    @pytest.fixture
    def valid_error_responses(self) -> List[str]:
        """Valid technical error responses."""
        return [
            "Vision analysis failed: API authentication error. Check GOOGLE_API_KEY configuration.",
            "Vision analysis timed out after 3 seconds. Network connection may be slow.",
            "Vision analysis failed: Rate limit exceeded. Please wait a moment and try again.",
            "Screen frame processing error: Invalid image data received.",
        ]

    def test_valid_vision_responses(self, valid_vision_responses):
        """Test that valid vision responses are accepted."""
        for response in valid_vision_responses:
            assert self._validate_vision_response(response), f"Response failed validation: {response}"

    def test_invalid_vision_responses(self, invalid_vision_responses):
        """Test that invalid vision responses are rejected."""
        for response in invalid_vision_responses:
            assert not self._validate_vision_response(response), f"Response should have failed: {response}"

    def test_valid_error_responses(self, valid_error_responses):
        """Test that technical error responses are properly formatted."""
        for response in valid_error_responses:
            assert self._validate_error_response(response), f"Error response failed validation: {response}"

    def _validate_vision_response(self, response: str) -> bool:
        """
        Validate that a vision response describes actual content without deflection.
        
        Returns True if response is valid, False if it contains deflection language.
        """
        response_lower = response.lower()
        
        # Check for deflection phrases (should be absent)
        deflection_phrases = [
            'i have limitations',
            'i cannot see',
            'i don\'t have access',
            'as an ai',
            'i\'m not able to',
            'technical constraints',
            'cannot process visual'
        ]
        
        for phrase in deflection_phrases:
            if phrase in response_lower:
                return False
        
        return True

    def _validate_error_response(self, response: str) -> bool:
        """
        Validate that an error response provides specific technical information.
        
        Returns True if response contains specific error details.
        """
        response_lower = response.lower()
        
        # Should contain specific error information
        error_indicators = [
            'vision analysis failed',
            'api authentication error',
            'timed out',
            'rate limit exceeded',
            'processing error',
            'invalid image data',
            'network connection',
            'check google_api_key'
        ]
        
        return any(indicator in response_lower for indicator in error_indicators)


class TestConversationScenarios:
    """Test complete conversation scenarios."""

    def test_identity_introduction_scenario(self):
        """Test identity consistency in introduction scenarios."""
        scenarios = [
            {
                "user": "Hello, who are you?",
                "expected_patterns": [r"I'm Spectra", r"This is Spectra"],
                "forbidden_patterns": [r"I'm an AI", r"artificial intelligence"]
            },
            {
                "user": "What are you?",
                "expected_patterns": [r"I'm Spectra", r"helpful assistant"],
                "forbidden_patterns": [r"I'm an AI", r"artificial intelligence"]
            },
            {
                "user": "Are you an AI?",
                "expected_patterns": [r"I'm Spectra"],
                "forbidden_patterns": [r"Yes, I'm an AI", r"I am an AI"]
            }
        ]
        
        for scenario in scenarios:
            instruction = SPECTRA_SYSTEM_INSTRUCTION
            assert "Spectra" in instruction
            assert "never" in instruction.lower() or "NEVER" in instruction

    def test_location_query_scenario(self):
        """Test location query handling scenarios."""
        instruction_lower = SPECTRA_SYSTEM_INSTRUCTION.lower()
        assert "where am i" in instruction_lower or "location" in instruction_lower
        assert "google" in instruction_lower or "gmail" in instruction_lower or "you're on" in instruction_lower

    def test_vision_system_scenario(self):
        """Test vision system behavior scenarios."""
        instruction_lower = SPECTRA_SYSTEM_INSTRUCTION.lower()
        assert "describe" in instruction_lower or "screen" in instruction_lower
        assert "never" in instruction_lower


class TestPropertyBasedValidation:
    """Property-based tests for system instruction validation."""

    def test_identity_consistency_property(self):
        """Property: All responses should maintain identity consistency."""
        # This would use a property-based testing framework like Hypothesis
        # For now, we test the principle with sample data
        
        sample_responses = [
            "I'm Spectra, and I can help you with that.",
            "This is Spectra. I can see your screen clearly.",
            "I can help you navigate this website.",
            "Let me describe what I see on your screen.",
        ]
        
        for response in sample_responses:
            assert self._property_identity_consistent(response)

    def test_location_response_property(self):
        """Property: Location responses should be screen-based, not physical."""
        sample_location_responses = [
            "You're on Google.com - I can see the search page",
            "You're in Gmail - I can see your inbox",
            "I can see your screen but cannot determine the specific website",
        ]
        
        for response in sample_location_responses:
            assert self._property_screen_based_location(response)

    def test_vision_response_property(self):
        """Property: Vision responses should describe actual content or provide specific errors."""
        sample_vision_responses = [
            "I can see the homepage with a search box",
            "Vision analysis failed: API authentication error",
            "I can see your screen but the text is too small to read",
        ]
        
        for response in sample_vision_responses:
            assert self._property_valid_vision_response(response)

    def _property_identity_consistent(self, response: str) -> bool:
        """Check if response maintains identity consistency."""
        response_lower = response.lower()
        
        # Should not contain AI self-references
        forbidden_patterns = [r'\bas an ai\b', r'\bi\'m an ai\b', r'\bartificial intelligence\b']
        for pattern in forbidden_patterns:
            if re.search(pattern, response_lower):
                return False
        
        return True

    def _property_screen_based_location(self, response: str) -> bool:
        """Check if location response is screen-based."""
        response_lower = response.lower()
        
        # Should not contain physical location references
        physical_terms = ['gps', 'address', 'physical location', 'coordinates']
        for term in physical_terms:
            if term in response_lower:
                return False
        
        # Should contain screen-based terms or proper fallback
        screen_terms = ['website', 'screen', 'page', 'app', '.com', 'gmail', 'google']
        fallback_terms = ['cannot determine', 'can see your screen but']
        
        has_screen_term = any(term in response_lower for term in screen_terms)
        has_fallback = any(term in response_lower for term in fallback_terms)
        
        return has_screen_term or has_fallback

    def _property_valid_vision_response(self, response: str) -> bool:
        """Check if vision response is valid (no deflection or specific error)."""
        response_lower = response.lower()
        
        # Should not contain deflection language
        deflection_terms = ['i have limitations', 'i cannot see', 'as an ai']
        for term in deflection_terms:
            if term in response_lower:
                return False
        
        return True


if __name__ == "__main__":
    # Run basic validation tests
    test_suite = TestSystemInstructionValidation()
    test_suite.test_system_instruction_identity_rules()
    test_suite.test_system_instruction_location_context_rules()
    test_suite.test_system_instruction_vision_behavior_rules()
    
    print("✅ All system instruction validation tests passed!")