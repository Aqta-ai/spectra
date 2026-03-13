"""Spectra Error Handler - Comprehensive error handling for vision system and API calls.

This module provides structured error categorization, detailed logging with context information,
and user-friendly error messages with debugging hints for the Spectra accessibility system.
"""

import json
import logging
import os
import time
from enum import Enum
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for structured error handling."""
    VISION_API = "vision_api"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    RATE_LIMIT = "rate_limit"
    FRAME_PROCESSING = "frame_processing"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Context information for error logging and debugging."""
    timestamp: float
    error_type: str
    error_message: str
    frame_hash: Optional[str] = None
    frame_size: Optional[int] = None
    api_key_present: bool = False
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    retry_attempt: int = 0
    api_request_details: Optional[Dict[str, Any]] = None
    api_response_details: Optional[Dict[str, Any]] = None
    additional_context: Optional[Dict[str, Any]] = None


class SpectraErrorHandler:
    """Comprehensive error handler for Spectra vision system and API calls.
    
    Provides:
    - Structured error categorization
    - Detailed logging with context information
    - User-friendly error messages with debugging hints
    - Retry logic coordination
    """

    def __init__(self):
        self.error_categories = {
            ErrorCategory.VISION_API: "Gemini Vision API errors",
            ErrorCategory.NETWORK: "Network connectivity issues", 
            ErrorCategory.AUTHENTICATION: "API key or authentication problems",
            ErrorCategory.RATE_LIMIT: "API rate limiting",
            ErrorCategory.FRAME_PROCESSING: "Screen capture processing errors",
            ErrorCategory.TIMEOUT: "Request timeout errors",
            ErrorCategory.UNKNOWN: "Unclassified errors"
        }
        
        # Track error patterns for debugging
        self.error_history = []
        self.max_history = 100

    def categorize_error(self, error: Exception) -> ErrorCategory:
        """Categorize an error based on its type and message."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Authentication errors
        if any(indicator in error_str for indicator in ['401', 'unauthorized', 'invalid api key', 'authentication']):
            return ErrorCategory.AUTHENTICATION
            
        # Rate limiting errors
        if any(indicator in error_str for indicator in ['429', 'rate limit', 'quota exceeded', 'too many requests']):
            return ErrorCategory.RATE_LIMIT
            
        # Network errors
        if any(indicator in error_str for indicator in ['connection', 'network', 'dns', 'unreachable', 'timeout']):
            if 'timeout' in error_str:
                return ErrorCategory.TIMEOUT
            return ErrorCategory.NETWORK
            
        # Vision API specific errors
        if any(indicator in error_str for indicator in ['vision', 'gemini', 'api', 'invalid request']):
            return ErrorCategory.VISION_API
            
        # Frame processing errors
        if any(indicator in error_str for indicator in ['frame', 'image', 'decode', 'base64', 'jpeg']):
            return ErrorCategory.FRAME_PROCESSING
            
        return ErrorCategory.UNKNOWN

    def create_error_context(
        self,
        error: Exception,
        frame_hash: Optional[str] = None,
        frame_size: Optional[int] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        retry_attempt: int = 0,
        api_request_details: Optional[Dict[str, Any]] = None,
        api_response_details: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """Create comprehensive error context for logging."""
        return ErrorContext(
            timestamp=time.time(),
            error_type=type(error).__name__,
            error_message=str(error),
            frame_hash=frame_hash,
            frame_size=frame_size,
            api_key_present=bool(os.getenv('GOOGLE_API_KEY')),
            user_id=user_id,
            session_id=session_id,
            retry_attempt=retry_attempt,
            api_request_details=api_request_details,
            api_response_details=api_response_details,
            additional_context=additional_context or {}
        )

    def log_error(self, error_context: ErrorContext, category: ErrorCategory) -> None:
        """Log error with structured context information."""
        error_data = {
            "category": category.value,
            "context": asdict(error_context),
            "description": self.error_categories[category]
        }
        
        # Add to error history for pattern analysis
        self.error_history.append({
            "timestamp": error_context.timestamp,
            "category": category.value,
            "error_type": error_context.error_type,
            "retry_attempt": error_context.retry_attempt
        })
        
        # Keep history size manageable
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        # Log with appropriate level based on category
        if category in [ErrorCategory.AUTHENTICATION, ErrorCategory.RATE_LIMIT]:
            logger.error(f"Spectra error [{category.value}]: {json.dumps(error_data, indent=2)}")
        elif category == ErrorCategory.NETWORK:
            logger.warning(f"Spectra error [{category.value}]: {json.dumps(error_data, indent=2)}")
        else:
            logger.error(f"Spectra error [{category.value}]: {json.dumps(error_data, indent=2)}")

    def get_user_friendly_message(self, error: Exception, category: ErrorCategory, retry_attempt: int = 0) -> str:
        """Generate user-friendly error message with debugging hints."""
        error_str = str(error)
        
        if category == ErrorCategory.AUTHENTICATION:
            if '401' in error_str or 'unauthorized' in error_str.lower():
                return (
                    "Vision analysis failed: Invalid API key. "
                    "Check GOOGLE_API_KEY in backend/.env file. "
                    "Ensure the API key has Gemini API access enabled."
                )
            return (
                "Vision analysis failed: Authentication error. "
                "Please check your API key configuration."
            )
            
        elif category == ErrorCategory.RATE_LIMIT:
            if retry_attempt > 0:
                return (
                    f"Vision analysis failed: Rate limit exceeded (attempt {retry_attempt + 1}). "
                    "The system will retry automatically. Please wait a moment."
                )
            return (
                "Vision analysis failed: Rate limit exceeded. "
                "Please wait a moment and try again. "
                "Consider upgrading your API quota if this persists."
            )
            
        elif category == ErrorCategory.TIMEOUT:
            return (
                "Vision analysis timed out. "
                "Check your network connection and try again. "
                "If the problem persists, the API may be experiencing high load."
            )
            
        elif category == ErrorCategory.NETWORK:
            return (
                "Vision analysis failed: Network connectivity issue. "
                "Check your internet connection and firewall settings. "
                "Ensure access to googleapis.com is not blocked."
            )
            
        elif category == ErrorCategory.FRAME_PROCESSING:
            return (
                "Vision analysis failed: Screen frame processing error. "
                "Try refreshing the screen share or restarting the session. "
                "Check that screen sharing permissions are properly granted."
            )
            
        elif category == ErrorCategory.VISION_API:
            if 'invalid request' in error_str.lower():
                return (
                    "Vision analysis failed: Invalid request format. "
                    "This may indicate a compatibility issue. "
                    "Please report this error with the current screen content type."
                )
            return (
                f"Vision analysis failed: API error. "
                f"Error details: {error_str[:100]}{'...' if len(error_str) > 100 else ''}. "
                "Check backend logs for detailed information."
            )
            
        else:  # UNKNOWN category
            return (
                f"Vision analysis failed: Unexpected error. "
                f"Error: {error_str[:100]}{'...' if len(error_str) > 100 else ''}. "
                "Check backend logs for detailed debugging information."
            )

    def handle_vision_error(
        self,
        error: Exception,
        frame_hash: Optional[str] = None,
        frame_size: Optional[int] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        retry_attempt: int = 0,
        api_request_details: Optional[Dict[str, Any]] = None,
        api_response_details: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Handle vision system errors with comprehensive logging and user feedback.
        
        Args:
            error: The exception that occurred
            frame_hash: Hash of the screen frame being processed
            frame_size: Size of the frame data in bytes
            user_id: User identifier for the session
            session_id: Session identifier
            retry_attempt: Current retry attempt number (0-based)
            api_request_details: Details about the API request (method, endpoint, headers, etc.)
            api_response_details: Details about the API response (status, headers, body, etc.)
            additional_context: Additional context information
            
        Returns:
            User-friendly error message with debugging hints
        """
        # Categorize the error
        category = self.categorize_error(error)
        
        # Create comprehensive error context
        error_context = self.create_error_context(
            error=error,
            frame_hash=frame_hash,
            frame_size=frame_size,
            user_id=user_id,
            session_id=session_id,
            retry_attempt=retry_attempt,
            api_request_details=api_request_details,
            api_response_details=api_response_details,
            additional_context=additional_context
        )
        
        # Log the error with full context
        self.log_error(error_context, category)
        
        # Generate user-friendly message
        user_message = self.get_user_friendly_message(error, category, retry_attempt)
        
        return user_message

    def should_retry(self, error: Exception, retry_attempt: int, max_retries: int = 3) -> bool:
        """Determine if an error should trigger a retry attempt.
        
        Args:
            error: The exception that occurred
            retry_attempt: Current retry attempt number (0-based)
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if the error should be retried, False otherwise
        """
        if retry_attempt >= max_retries:
            return False
            
        category = self.categorize_error(error)
        
        # Don't retry authentication errors - they won't resolve automatically
        if category == ErrorCategory.AUTHENTICATION:
            return False
            
        # Don't retry frame processing errors - likely a persistent issue
        if category == ErrorCategory.FRAME_PROCESSING:
            return False
            
        # Retry network, timeout, rate limit, and API errors
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.RATE_LIMIT, ErrorCategory.VISION_API]:
            return True
            
        # Don't retry unknown errors by default
        return False

    def get_retry_delay(self, retry_attempt: int, category: ErrorCategory) -> float:
        """Calculate appropriate delay before retry based on error category.
        
        Args:
            retry_attempt: Current retry attempt number (0-based)
            category: Error category
            
        Returns:
            Delay in seconds before next retry attempt
        """
        base_delay = 0.5
        
        if category == ErrorCategory.RATE_LIMIT:
            # Longer delays for rate limiting
            return base_delay * (3 ** retry_attempt)  # 0.5s, 1.5s, 4.5s
        elif category == ErrorCategory.NETWORK:
            # Moderate delays for network issues
            return base_delay * (2 ** retry_attempt)  # 0.5s, 1.0s, 2.0s
        else:
            # Standard exponential backoff
            return base_delay * (1.5 ** retry_attempt)  # 0.5s, 0.75s, 1.125s

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring and debugging.
        
        Returns:
            Dictionary containing error statistics and patterns
        """
        if not self.error_history:
            return {"total_errors": 0, "categories": {}, "recent_errors": []}
        
        # Count errors by category
        category_counts = {}
        recent_errors = []
        current_time = time.time()
        
        for error_record in self.error_history:
            category = error_record["category"]
            category_counts[category] = category_counts.get(category, 0) + 1
            
            # Include errors from last 5 minutes in recent errors
            if current_time - error_record["timestamp"] < 300:
                recent_errors.append(error_record)
        
        return {
            "total_errors": len(self.error_history),
            "categories": category_counts,
            "recent_errors": recent_errors[-10:],  # Last 10 recent errors
            "error_rate": len(recent_errors) / 5.0 if recent_errors else 0.0  # Errors per minute
        }

    def log_api_request(
        self,
        endpoint: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        payload_size: Optional[int] = None,
        frame_hash: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log API request details for debugging.
        
        Args:
            endpoint: API endpoint being called
            method: HTTP method (GET, POST, etc.)
            headers: Request headers (sensitive data will be masked)
            payload_size: Size of request payload in bytes
            frame_hash: Hash of the frame being processed
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Request details dictionary for correlation with response
        """
        request_id = f"req_{int(time.time() * 1000)}_{hash(frame_hash or 'unknown') % 10000}"
        
        # Mask sensitive headers
        safe_headers = {}
        if headers:
            for key, value in headers.items():
                if key.lower() in ['authorization', 'x-api-key', 'x-goog-api-key']:
                    safe_headers[key] = f"{value[:8]}***" if len(value) > 8 else "***"
                else:
                    safe_headers[key] = value
        
        request_details = {
            "request_id": request_id,
            "timestamp": time.time(),
            "endpoint": endpoint,
            "method": method,
            "headers": safe_headers,
            "payload_size": payload_size,
            "frame_hash": frame_hash,
            "session_id": session_id,
            "user_id": user_id,
            "api_key_present": bool(os.getenv('GOOGLE_API_KEY'))
        }
        
        logger.info(f"🔵 API Request [{request_id}]: {json.dumps(request_details, indent=2)}")
        return request_details

    def log_api_response(
        self,
        request_details: Dict[str, Any],
        status_code: Optional[int] = None,
        response_size: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        error: Optional[Exception] = None,
        response_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Log API response details for debugging.
        
        Args:
            request_details: Request details from log_api_request
            status_code: HTTP status code
            response_size: Size of response in bytes
            response_time_ms: Response time in milliseconds
            error: Exception if request failed
            response_headers: Response headers
            
        Returns:
            Response details dictionary
        """
        request_id = request_details.get("request_id", "unknown")
        request_timestamp = request_details.get("timestamp", time.time())
        
        response_details = {
            "request_id": request_id,
            "response_timestamp": time.time(),
            "request_timestamp": request_timestamp,
            "response_time_ms": response_time_ms or (time.time() - request_timestamp) * 1000,
            "status_code": status_code,
            "response_size": response_size,
            "response_headers": response_headers or {},
            "success": error is None and (status_code is None or 200 <= status_code < 300),
            "error": str(error) if error else None,
            "frame_hash": request_details.get("frame_hash"),
            "session_id": request_details.get("session_id"),
            "user_id": request_details.get("user_id")
        }
        
        # Log with appropriate level
        if response_details["success"]:
            logger.info(f"🟢 API Response [{request_id}]: {json.dumps(response_details, indent=2)}")
        else:
            logger.error(f"🔴 API Response [{request_id}]: {json.dumps(response_details, indent=2)}")
        
        return response_details

    def log_vision_analysis_attempt(
        self,
        frame_hash: str,
        frame_size: int,
        focus: str,
        retry_attempt: int,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Log vision analysis attempt with comprehensive context.
        
        Args:
            frame_hash: Hash of the frame being analyzed
            frame_size: Size of frame data in bytes
            focus: Focus area for analysis
            retry_attempt: Current retry attempt (0-based)
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            Analysis context for correlation with results
        """
        analysis_id = f"vision_{int(time.time() * 1000)}_{frame_hash[:8]}"
        
        analysis_context = {
            "analysis_id": analysis_id,
            "timestamp": time.time(),
            "frame_hash": frame_hash,
            "frame_size": frame_size,
            "focus": focus,
            "retry_attempt": retry_attempt,
            "session_id": session_id,
            "user_id": user_id,
            "api_key_present": bool(os.getenv('GOOGLE_API_KEY'))
        }
        
        logger.info(f"🔍 Vision Analysis [{analysis_id}] Attempt {retry_attempt + 1}: {json.dumps(analysis_context, indent=2)}")
        return analysis_context

    def log_vision_analysis_result(
        self,
        analysis_context: Dict[str, Any],
        success: bool,
        result_length: Optional[int] = None,
        processing_time_ms: Optional[float] = None,
        error: Optional[Exception] = None,
        is_deflection: bool = False,
        cache_hit: bool = False
    ) -> None:
        """Log vision analysis result with comprehensive details.
        
        Args:
            analysis_context: Context from log_vision_analysis_attempt
            success: Whether analysis succeeded
            result_length: Length of result text
            processing_time_ms: Processing time in milliseconds
            error: Exception if analysis failed
            is_deflection: Whether result was a deflection response
            cache_hit: Whether result came from cache
        """
        analysis_id = analysis_context.get("analysis_id", "unknown")
        start_timestamp = analysis_context.get("timestamp", time.time())
        
        result_details = {
            "analysis_id": analysis_id,
            "result_timestamp": time.time(),
            "start_timestamp": start_timestamp,
            "processing_time_ms": processing_time_ms or (time.time() - start_timestamp) * 1000,
            "success": success,
            "result_length": result_length,
            "is_deflection": is_deflection,
            "cache_hit": cache_hit,
            "error": str(error) if error else None,
            "frame_hash": analysis_context.get("frame_hash"),
            "retry_attempt": analysis_context.get("retry_attempt"),
            "session_id": analysis_context.get("session_id"),
            "user_id": analysis_context.get("user_id")
        }
        
        # Log with appropriate level and emoji
        if success and not is_deflection:
            logger.info(f"✅ Vision Result [{analysis_id}]: {json.dumps(result_details, indent=2)}")
        elif is_deflection:
            logger.warning(f"⚠️ Vision Deflection [{analysis_id}]: {json.dumps(result_details, indent=2)}")
        else:
            logger.error(f"❌ Vision Failed [{analysis_id}]: {json.dumps(result_details, indent=2)}")

    def is_deflection_response(self, response: str) -> bool:
        """Check if a response contains deflection phrases that should be filtered out.
        
        Args:
            response: The response text to check
            
        Returns:
            True if the response contains deflection phrases, False otherwise
        """
        deflection_phrases = [
            "i have limitations",
            "i cannot see",
            "as an ai",
            "i don't have access",
            "i'm not able to",
            "i can't actually see",
            "i don't have the ability",
            "i'm unable to",
            "i cannot access",
            "i don't have visual capabilities"
        ]
        
        response_lower = response.lower()
        return any(phrase in response_lower for phrase in deflection_phrases)


# Global error handler instance
error_handler = SpectraErrorHandler()