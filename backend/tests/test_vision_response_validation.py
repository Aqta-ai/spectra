"""Tests for vision response validation functionality."""

import pytest
from unittest.mock import patch, MagicMock
import os

from app.streaming.session import SpectraStreamingSession


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.sent_messages = []
    
    async def send_text(self, message):
        self.sent_messages.append(message)


class TestVisionResponseValidation:
    """Test suite for vision response validation."""

    def setup_method(self):
        """Set up test fixtures."""
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test_api_key'}):
            with patch('app.streaming.session.genai.Client'):
                self.session = SpectraStreamingSession(MockWebSocket())

    def test_is_valid_description_deflection_responses(self):
        """Test that deflection responses are correctly identified as invalid."""
        deflection_responses = [
            "I have limitations in processing this request",
            "I cannot see the screen content",
            "As an AI, I don't have access to visual data",
            "I don't have access to your screen",
            "I'm not able to view the screen",
            "I can't actually see what's on your screen",
            "I don't have the ability to see screens",
            "I'm unable to process visual content",
            "I cannot access your display",
            "I don't have visual capabilities"
        ]
        
        for response in deflection_responses:
            assert self.session._is_valid_description(response) is False, f"Should detect deflection: {response}"

    def test_is_valid_description_valid_responses(self):
        """Test that valid screen descriptions are correctly identified."""
        valid_responses = [
            "I can see a Google search page with a search bar in the center",
            "The screen shows a login form with username and password fields",
            "There's a navigation menu at the top with Home, About, and Contact links",
            "I notice several buttons on the right side: Submit, Cancel, and Reset",
            "The page contains a list of search results with blue links and descriptions",
            "I can see a Gmail inbox with several unread emails in bold text",
            "The screen displays a YouTube video player with a play button in the center",
            "There's a shopping cart icon in the top right corner showing 3 items"
        ]
        
        for response in valid_responses:
            assert self.session._is_valid_description(response) is True, f"Should accept valid description: {response}"

    def test_is_valid_description_empty_responses(self):
        """Test that empty or very short responses are invalid."""
        invalid_responses = [
            "",
            "   ",
            "Error",
            "Failed",
            "No data",
            "Empty"
        ]
        
        for response in invalid_responses:
            assert self.session._is_valid_description(response) is False, f"Should reject short response: {response}"

    def test_is_valid_description_generic_errors(self):
        """Test that generic error messages are identified as invalid."""
        generic_error_responses = [
            "An error occurred while processing the screen",
            "Something went wrong during analysis",
            "Unable to process the visual content",
            "Failed to analyze the screen content",
            "No content available for analysis",
            "Error occurred during vision processing"
        ]
        
        for response in generic_error_responses:
            assert self.session._is_valid_description(response) is False, f"Should reject generic error: {response}"

    def test_is_valid_description_case_insensitive(self):
        """Test that validation is case insensitive."""
        case_variations = [
            "I HAVE LIMITATIONS",
            "i cannot see the screen",
            "As An AI Assistant, I don't have access",
            "ERROR OCCURRED WHILE PROCESSING"
        ]
        
        for response in case_variations:
            assert self.session._is_valid_description(response) is False, f"Should be case insensitive: {response}"

    def test_is_valid_description_mixed_content(self):
        """Test responses that contain both valid and invalid elements."""
        mixed_responses = [
            # Valid description with deflection phrase - should be invalid
            "I can see a Google page, but I have limitations in describing it fully",
            # Valid description with generic error - should be invalid  
            "The screen shows a login form, but an error occurred during processing",
            # Valid description that mentions AI in context - should be valid
            "I can see an article about AI technology and machine learning on the screen"
        ]
        
        expected_results = [False, False, True]
        
        for response, expected in zip(mixed_responses, expected_results):
            result = self.session._is_valid_description(response)
            assert result == expected, f"Mixed content test failed for: {response}"

    def test_is_valid_description_edge_cases(self):
        """Test edge cases for response validation."""
        edge_cases = [
            # Exactly 10 characters (minimum length)
            ("1234567890", True),
            # Just under minimum length
            ("123456789", False),
            # Valid description with numbers and special characters
            ("I see 5 buttons: Save, Delete, Edit, Copy & Paste options available", True),
            # Response with only whitespace and short content
            ("   Error   ", False),
            # Long deflection response
            ("I have limitations and cannot see the screen content due to my AI constraints", False)
        ]
        
        for response, expected in edge_cases:
            result = self.session._is_valid_description(response)
            assert result == expected, f"Edge case failed for: '{response}' (expected {expected}, got {result})"

    @patch('app.error_handler.error_handler.is_deflection_response')
    def test_is_valid_description_uses_error_handler(self, mock_is_deflection):
        """Test that _is_valid_description properly uses the error handler."""
        mock_is_deflection.return_value = False
        
        response = "I can see a valid screen description"
        result = self.session._is_valid_description(response)
        
        # Should call the error handler's deflection detection
        mock_is_deflection.assert_called_once_with(response)
        assert result is True

    @patch('app.error_handler.error_handler.is_deflection_response')
    def test_is_valid_description_deflection_detected_by_handler(self, mock_is_deflection):
        """Test that deflections detected by error handler are properly handled."""
        mock_is_deflection.return_value = True
        
        response = "Some response that the handler considers a deflection"
        result = self.session._is_valid_description(response)
        
        mock_is_deflection.assert_called_once_with(response)
        assert result is False

    def test_is_valid_description_integration_with_retry_logic(self):
        """Test that the validation integrates properly with retry logic."""
        # This test verifies that the method exists and can be called
        # The actual retry integration is tested in the enhanced describe screen tests
        
        valid_response = "I can see a webpage with navigation menu and content area"
        invalid_response = "I have limitations in viewing screens"
        
        assert self.session._is_valid_description(valid_response) is True
        assert self.session._is_valid_description(invalid_response) is False