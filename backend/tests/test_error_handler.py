"""Tests for SpectraErrorHandler class."""

import json
import os
import time
from unittest.mock import patch, MagicMock
import pytest

from app.error_handler import (
    SpectraErrorHandler,
    ErrorCategory,
    ErrorContext,
    error_handler
)


class TestSpectraErrorHandler:
    """Test suite for SpectraErrorHandler class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.handler = SpectraErrorHandler()

    def test_categorize_authentication_errors(self):
        """Test categorization of authentication errors."""
        # Test 401 error
        error_401 = Exception("401 Unauthorized")
        assert self.handler.categorize_error(error_401) == ErrorCategory.AUTHENTICATION
        
        # Test invalid API key error
        error_api_key = Exception("Invalid API key provided")
        assert self.handler.categorize_error(error_api_key) == ErrorCategory.AUTHENTICATION
        
        # Test authentication error
        error_auth = Exception("Authentication failed")
        assert self.handler.categorize_error(error_auth) == ErrorCategory.AUTHENTICATION

    def test_categorize_rate_limit_errors(self):
        """Test categorization of rate limiting errors."""
        # Test 429 error
        error_429 = Exception("429 Too Many Requests")
        assert self.handler.categorize_error(error_429) == ErrorCategory.RATE_LIMIT
        
        # Test quota exceeded error
        error_quota = Exception("Quota exceeded for this API")
        assert self.handler.categorize_error(error_quota) == ErrorCategory.RATE_LIMIT
        
        # Test rate limit error
        error_rate = Exception("Rate limit exceeded")
        assert self.handler.categorize_error(error_rate) == ErrorCategory.RATE_LIMIT

    def test_categorize_network_errors(self):
        """Test categorization of network errors."""
        # Test connection error
        error_connection = Exception("Connection refused")
        assert self.handler.categorize_error(error_connection) == ErrorCategory.NETWORK
        
        # Test DNS error
        error_dns = Exception("DNS resolution failed")
        assert self.handler.categorize_error(error_dns) == ErrorCategory.NETWORK
        
        # Test network unreachable
        error_unreachable = Exception("Network unreachable")
        assert self.handler.categorize_error(error_unreachable) == ErrorCategory.NETWORK

    def test_categorize_timeout_errors(self):
        """Test categorization of timeout errors."""
        # Test timeout error
        error_timeout = Exception("Request timeout")
        assert self.handler.categorize_error(error_timeout) == ErrorCategory.TIMEOUT
        
        # Test connection timeout
        error_conn_timeout = Exception("Connection timeout occurred")
        assert self.handler.categorize_error(error_conn_timeout) == ErrorCategory.TIMEOUT

    def test_categorize_vision_api_errors(self):
        """Test categorization of Vision API errors."""
        # Test Gemini API error
        error_gemini = Exception("Gemini API request failed")
        assert self.handler.categorize_error(error_gemini) == ErrorCategory.VISION_API
        
        # Test invalid request error
        error_invalid = Exception("Invalid request format")
        assert self.handler.categorize_error(error_invalid) == ErrorCategory.VISION_API

    def test_categorize_frame_processing_errors(self):
        """Test categorization of frame processing errors."""
        # Test base64 decode error
        error_base64 = Exception("Invalid base64 encoding")
        assert self.handler.categorize_error(error_base64) == ErrorCategory.FRAME_PROCESSING
        
        # Test JPEG error
        error_jpeg = Exception("Invalid JPEG format")
        assert self.handler.categorize_error(error_jpeg) == ErrorCategory.FRAME_PROCESSING
        
        # Test frame error
        error_frame = Exception("Frame processing failed")
        assert self.handler.categorize_error(error_frame) == ErrorCategory.FRAME_PROCESSING

    def test_categorize_unknown_errors(self):
        """Test categorization of unknown errors."""
        error_unknown = Exception("Some random error message")
        assert self.handler.categorize_error(error_unknown) == ErrorCategory.UNKNOWN

    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'})
    def test_create_error_context(self):
        """Test creation of error context."""
        error = Exception("Test error")
        context = self.handler.create_error_context(
            error=error,
            frame_hash="abc123",
            frame_size=1024,
            user_id="user123",
            session_id="session456",
            retry_attempt=1,
            additional_context={"test": "data"}
        )
        
        assert isinstance(context, ErrorContext)
        assert context.error_type == "Exception"
        assert context.error_message == "Test error"
        assert context.frame_hash == "abc123"
        assert context.frame_size == 1024
        assert context.api_key_present is True
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.retry_attempt == 1
        assert context.additional_context == {"test": "data"}
        assert isinstance(context.timestamp, float)

    @patch.dict(os.environ, {}, clear=True)
    def test_create_error_context_no_api_key(self):
        """Test error context creation when API key is not present."""
        error = Exception("Test error")
        context = self.handler.create_error_context(error)
        
        assert context.api_key_present is False

    def test_log_error(self):
        """Test error logging functionality."""
        error = Exception("Test error")
        context = self.handler.create_error_context(error, user_id="test_user")
        category = ErrorCategory.VISION_API
        
        # Clear error history
        self.handler.error_history = []
        
        with patch('app.error_handler.logger') as mock_logger:
            self.handler.log_error(context, category)
            
            # Check that error was logged
            mock_logger.error.assert_called_once()
            log_call = mock_logger.error.call_args[0][0]
            assert "vision_api" in log_call
            assert "Test error" in log_call
        
        # Check error history was updated
        assert len(self.handler.error_history) == 1
        assert self.handler.error_history[0]["category"] == "vision_api"
        assert self.handler.error_history[0]["error_type"] == "Exception"

    def test_error_history_size_limit(self):
        """Test that error history respects size limit."""
        # Set a small max history for testing
        self.handler.max_history = 5
        
        # Add more errors than the limit
        for i in range(10):
            error = Exception(f"Error {i}")
            context = self.handler.create_error_context(error)
            self.handler.log_error(context, ErrorCategory.UNKNOWN)
        
        # Check that history is limited
        assert len(self.handler.error_history) == 5
        # Check that the most recent errors are kept
        assert self.handler.error_history[-1]["error_type"] == "Exception"

    def test_get_user_friendly_message_authentication(self):
        """Test user-friendly messages for authentication errors."""
        error_401 = Exception("401 Unauthorized")
        message = self.handler.get_user_friendly_message(error_401, ErrorCategory.AUTHENTICATION)
        
        assert "Invalid API key" in message
        assert "GOOGLE_API_KEY" in message
        assert "backend/.env" in message

    def test_get_user_friendly_message_rate_limit(self):
        """Test user-friendly messages for rate limit errors."""
        error_429 = Exception("429 Too Many Requests")
        message = self.handler.get_user_friendly_message(error_429, ErrorCategory.RATE_LIMIT)
        
        assert "Rate limit exceeded" in message
        assert "wait a moment" in message
        
        # Test with retry attempt
        message_retry = self.handler.get_user_friendly_message(error_429, ErrorCategory.RATE_LIMIT, retry_attempt=1)
        assert "attempt 2" in message_retry

    def test_get_user_friendly_message_timeout(self):
        """Test user-friendly messages for timeout errors."""
        error_timeout = Exception("Request timeout")
        message = self.handler.get_user_friendly_message(error_timeout, ErrorCategory.TIMEOUT)
        
        assert "timed out" in message
        assert "network connection" in message

    def test_get_user_friendly_message_network(self):
        """Test user-friendly messages for network errors."""
        error_network = Exception("Connection refused")
        message = self.handler.get_user_friendly_message(error_network, ErrorCategory.NETWORK)
        
        assert "Network connectivity issue" in message
        assert "internet connection" in message
        assert "googleapis.com" in message

    def test_get_user_friendly_message_frame_processing(self):
        """Test user-friendly messages for frame processing errors."""
        error_frame = Exception("Invalid base64")
        message = self.handler.get_user_friendly_message(error_frame, ErrorCategory.FRAME_PROCESSING)
        
        assert "Screen frame processing error" in message
        assert "screen share" in message

    def test_get_user_friendly_message_vision_api(self):
        """Test user-friendly messages for Vision API errors."""
        error_api = Exception("Invalid request format")
        message = self.handler.get_user_friendly_message(error_api, ErrorCategory.VISION_API)
        
        assert "Invalid request format" in message
        assert "compatibility issue" in message
        
        # Test generic API error
        error_generic = Exception("Some API error")
        message_generic = self.handler.get_user_friendly_message(error_generic, ErrorCategory.VISION_API)
        assert "API error" in message_generic
        assert "Some API error" in message_generic

    def test_get_user_friendly_message_unknown(self):
        """Test user-friendly messages for unknown errors."""
        error_unknown = Exception("Mysterious error")
        message = self.handler.get_user_friendly_message(error_unknown, ErrorCategory.UNKNOWN)
        
        assert "Unexpected error" in message
        assert "Mysterious error" in message
        assert "backend logs" in message

    def test_handle_vision_error_complete_flow(self):
        """Test the complete vision error handling flow."""
        error = Exception("401 Unauthorized")
        
        with patch('app.error_handler.logger') as mock_logger:
            message = self.handler.handle_vision_error(
                error=error,
                frame_hash="test_hash",
                frame_size=2048,
                user_id="test_user",
                session_id="test_session",
                retry_attempt=0,
                additional_context={"test": "context"}
            )
        
        # Check that error was logged
        mock_logger.error.assert_called_once()
        
        # Check that user-friendly message was returned
        assert "Invalid API key" in message
        assert "GOOGLE_API_KEY" in message
        
        # Check that error was added to history
        assert len(self.handler.error_history) == 1

    def test_should_retry_authentication_errors(self):
        """Test retry logic for authentication errors."""
        error_auth = Exception("401 Unauthorized")
        
        # Authentication errors should not be retried
        assert self.handler.should_retry(error_auth, 0) is False
        assert self.handler.should_retry(error_auth, 1) is False

    def test_should_retry_frame_processing_errors(self):
        """Test retry logic for frame processing errors."""
        error_frame = Exception("Invalid base64")
        
        # Frame processing errors should not be retried
        assert self.handler.should_retry(error_frame, 0) is False

    def test_should_retry_network_errors(self):
        """Test retry logic for network errors."""
        error_network = Exception("Connection refused")
        
        # Network errors should be retried up to max attempts
        assert self.handler.should_retry(error_network, 0) is True
        assert self.handler.should_retry(error_network, 1) is True
        assert self.handler.should_retry(error_network, 2) is True
        assert self.handler.should_retry(error_network, 3) is False  # Exceeds max retries

    def test_should_retry_rate_limit_errors(self):
        """Test retry logic for rate limit errors."""
        error_rate = Exception("429 Too Many Requests")
        
        # Rate limit errors should be retried
        assert self.handler.should_retry(error_rate, 0) is True
        assert self.handler.should_retry(error_rate, 1) is True

    def test_should_retry_max_retries(self):
        """Test retry logic respects max retries parameter."""
        error_network = Exception("Connection refused")
        
        # Test with custom max retries
        assert self.handler.should_retry(error_network, 0, max_retries=1) is True
        assert self.handler.should_retry(error_network, 1, max_retries=1) is False

    def test_get_retry_delay_rate_limit(self):
        """Test retry delay calculation for rate limit errors."""
        delay_0 = self.handler.get_retry_delay(0, ErrorCategory.RATE_LIMIT)
        delay_1 = self.handler.get_retry_delay(1, ErrorCategory.RATE_LIMIT)
        delay_2 = self.handler.get_retry_delay(2, ErrorCategory.RATE_LIMIT)
        
        assert delay_0 == 0.5
        assert delay_1 == 1.5
        assert delay_2 == 4.5

    def test_get_retry_delay_network(self):
        """Test retry delay calculation for network errors."""
        delay_0 = self.handler.get_retry_delay(0, ErrorCategory.NETWORK)
        delay_1 = self.handler.get_retry_delay(1, ErrorCategory.NETWORK)
        delay_2 = self.handler.get_retry_delay(2, ErrorCategory.NETWORK)
        
        assert delay_0 == 0.5
        assert delay_1 == 1.0
        assert delay_2 == 2.0

    def test_get_retry_delay_other(self):
        """Test retry delay calculation for other error types."""
        delay_0 = self.handler.get_retry_delay(0, ErrorCategory.VISION_API)
        delay_1 = self.handler.get_retry_delay(1, ErrorCategory.VISION_API)
        delay_2 = self.handler.get_retry_delay(2, ErrorCategory.VISION_API)
        
        assert delay_0 == 0.5
        assert delay_1 == 0.75
        assert delay_2 == 1.125

    def test_get_error_statistics_empty(self):
        """Test error statistics when no errors have occurred."""
        self.handler.error_history = []
        stats = self.handler.get_error_statistics()
        
        assert stats["total_errors"] == 0
        assert stats["categories"] == {}
        assert stats["recent_errors"] == []

    def test_get_error_statistics_with_errors(self):
        """Test error statistics with error history."""
        # Add some test errors
        current_time = time.time()
        self.handler.error_history = [
            {
                "timestamp": current_time - 400,  # 400 seconds ago (not recent)
                "category": "vision_api",
                "error_type": "Exception",
                "retry_attempt": 0
            },
            {
                "timestamp": current_time - 350,  # 350 seconds ago (not recent)
                "category": "network",
                "error_type": "ConnectionError",
                "retry_attempt": 1
            },
            {
                "timestamp": current_time - 30,   # 30 seconds ago (recent)
                "category": "vision_api",
                "error_type": "Exception",
                "retry_attempt": 0
            }
        ]
        
        stats = self.handler.get_error_statistics()
        
        assert stats["total_errors"] == 3
        assert stats["categories"]["vision_api"] == 2
        assert stats["categories"]["network"] == 1
        assert len(stats["recent_errors"]) == 1  # Only the 30-second-old error is recent
        assert stats["error_rate"] == 0.2  # 1 error in 5 minutes = 0.2 errors per minute

    def test_is_deflection_response_positive_cases(self):
        """Test deflection response detection for positive cases."""
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
            assert self.handler.is_deflection_response(response) is True

    def test_is_deflection_response_negative_cases(self):
        """Test deflection response detection for negative cases."""
        valid_responses = [
            "I can see a Google search page with a search bar",
            "The screen shows a login form with username and password fields",
            "There's a navigation menu at the top of the page",
            "I notice several buttons on the right side",
            "The page contains a list of search results"
        ]
        
        for response in valid_responses:
            assert self.handler.is_deflection_response(response) is False

    def test_is_deflection_response_case_insensitive(self):
        """Test that deflection response detection is case insensitive."""
        responses = [
            "I HAVE LIMITATIONS",
            "i cannot see",
            "As An AI assistant",
            "I DON'T HAVE ACCESS"
        ]
        
        for response in responses:
            assert self.handler.is_deflection_response(response) is True

    def test_global_error_handler_instance(self):
        """Test that global error handler instance is available."""
        from app.error_handler import error_handler
        
        assert isinstance(error_handler, SpectraErrorHandler)
        assert error_handler is not None


class TestErrorContext:
    """Test suite for ErrorContext dataclass."""

    def test_error_context_creation(self):
        """Test ErrorContext creation and field access."""
        context = ErrorContext(
            timestamp=1234567890.0,
            error_type="TestError",
            error_message="Test message",
            frame_hash="abc123",
            frame_size=1024,
            api_key_present=True,
            user_id="user123",
            session_id="session456",
            retry_attempt=2,
            additional_context={"key": "value"}
        )
        
        assert context.timestamp == 1234567890.0
        assert context.error_type == "TestError"
        assert context.error_message == "Test message"
        assert context.frame_hash == "abc123"
        assert context.frame_size == 1024
        assert context.api_key_present is True
        assert context.user_id == "user123"
        assert context.session_id == "session456"
        assert context.retry_attempt == 2
        assert context.additional_context == {"key": "value"}

    def test_error_context_optional_fields(self):
        """Test ErrorContext with optional fields as None."""
        context = ErrorContext(
            timestamp=1234567890.0,
            error_type="TestError",
            error_message="Test message"
        )
        
        assert context.frame_hash is None
        assert context.frame_size is None
        assert context.api_key_present is False
        assert context.user_id is None
        assert context.session_id is None
        assert context.retry_attempt == 0
        assert context.additional_context is None


class TestErrorCategory:
    """Test suite for ErrorCategory enum."""

    def test_error_category_values(self):
        """Test ErrorCategory enum values."""
        assert ErrorCategory.VISION_API.value == "vision_api"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.RATE_LIMIT.value == "rate_limit"
        assert ErrorCategory.FRAME_PROCESSING.value == "frame_processing"
        assert ErrorCategory.TIMEOUT.value == "timeout"
        assert ErrorCategory.UNKNOWN.value == "unknown"

    def test_error_category_membership(self):
        """Test ErrorCategory enum membership."""
        categories = list(ErrorCategory)
        assert len(categories) == 7
        assert ErrorCategory.VISION_API in categories
        assert ErrorCategory.NETWORK in categories
        assert ErrorCategory.AUTHENTICATION in categories
        assert ErrorCategory.RATE_LIMIT in categories
        assert ErrorCategory.FRAME_PROCESSING in categories
        assert ErrorCategory.TIMEOUT in categories
        assert ErrorCategory.UNKNOWN in categories