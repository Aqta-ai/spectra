"""Comprehensive test suite for Spectra orchestrator."""

import pytest
import re
from typing import Any

# Import from the orchestrator module
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.agents.config import (
    DESTRUCTIVE_KEYWORDS,
    FORBIDDEN_SENTENCE_STARTS,
    VISION_ERROR_TYPES,
)


class TestNarrationRemoval:
    """Test anti-narration filtering."""
    
    def test_removes_ive_begun_patterns(self):
        """Should remove 'I've begun' meta-commentary."""
        from app.agents.orchestrator import remove_narration
        
        text = "I've begun analyzing the screen. You're on Gmail."
        result = remove_narration(text)
        assert "I've begun" not in result
        assert "You're on Gmail" in result
    
    def test_removes_im_currently_patterns(self):
        """Should remove 'I'm currently analyzing' meta-commentary (matches _NARRATION_SUBSTRINGS)."""
        from app.agents.orchestrator import remove_narration
        
        text = "I'm currently analyzing the search box. Clicking it now."
        result = remove_narration(text)
        assert "I'm currently analyzing" not in result
        assert "Clicking it now" in result
    
    def test_removes_bold_headers(self):
        """Should remove bold headers like **Analyzing**."""
        from app.agents.orchestrator import remove_narration
        
        text = "**Analyzing Screen** You're on Reddit."
        result = remove_narration(text)
        assert "**Analyzing" not in result
        assert "You're on Reddit" in result
    
    def test_preserves_valid_responses(self):
        """Should preserve valid, direct responses."""
        from app.agents.orchestrator import remove_narration
        
        text = "You're on Gmail. I see 15 unread messages."
        result = remove_narration(text)
        assert result == text
    
    def test_removes_to_accomplish_this(self):
        """Should remove 'To accomplish this, I will' planning (FORBIDDEN_SENTENCE_STARTS)."""
        from app.agents.orchestrator import remove_narration
        
        text = "To accomplish this, I will use describe_screen. Scanning now."
        result = remove_narration(text)
        assert "To accomplish this" not in result
        assert "Scanning now" in result
    
    def test_handles_empty_string(self):
        """Should handle empty strings gracefully."""
        from app.agents.orchestrator import remove_narration
        
        result = remove_narration("")
        assert result == ""
    
    def test_handles_multiple_sentences(self):
        """Should strip narration sentences and keep user-facing content."""
        from app.agents.orchestrator import remove_narration
        
        text = "I've begun analyzing the screen. You're on Gmail. I'm cataloging the buttons."
        result = remove_narration(text)
        assert "I've begun analyzing" not in result
        assert "I'm cataloging" not in result
        assert "You're on Gmail" in result


class TestLocationQueries:
    """Test location query detection."""
    
    def test_detects_where_am_i(self):
        """Should detect 'where am i' as location query."""
        from app.agents.orchestrator import is_location_query
        
        assert is_location_query("where am i")
        assert is_location_query("Where am I?")
        assert is_location_query("WHERE AM I")
    
    def test_detects_what_site(self):
        """Should detect 'what site am i on' as location query."""
        from app.agents.orchestrator import is_location_query
        
        assert is_location_query("what site am i on")
        assert is_location_query("What website is this?")
    
    def test_rejects_non_location_queries(self):
        """Should reject non-location queries."""
        from app.agents.orchestrator import is_location_query
        
        assert not is_location_query("click the button")
        assert not is_location_query("search for cats")
        assert not is_location_query("scroll down")


class TestVisionErrorClassification:
    """Test vision error classification."""
    
    def test_classifies_authentication_error(self):
        """Should classify authentication errors."""
        from app.agents.orchestrator import classify_vision_error
        
        result = classify_vision_error("401 Unauthorized: Invalid API key")
        assert result['type'] == 'authentication'
        assert 'API key' in result['user_message']
        assert not result['should_retry']
    
    def test_classifies_rate_limit_error(self):
        """Should classify rate limit errors."""
        from app.agents.orchestrator import classify_vision_error
        
        result = classify_vision_error("429 Rate limit exceeded")
        assert result['type'] == 'rate_limit'
        assert 'Rate limit' in result['user_message']
        assert result['should_retry']
    
    def test_classifies_timeout_error(self):
        """Should classify timeout errors."""
        from app.agents.orchestrator import classify_vision_error
        
        result = classify_vision_error("Request timed out after 5 seconds")
        assert result['type'] == 'timeout'
        assert 'timed out' in result['user_message']
        assert result['should_retry']
    
    def test_classifies_network_error(self):
        """Should classify network errors."""
        from app.agents.orchestrator import classify_vision_error
        
        result = classify_vision_error("Network connection failed")
        assert result['type'] == 'network'
        assert 'network' in result['user_message'].lower()
        assert result['should_retry']
    
    def test_classifies_unknown_error(self):
        """Should handle unknown errors."""
        from app.agents.orchestrator import classify_vision_error
        
        result = classify_vision_error("Something went wrong")
        assert result['type'] == 'unknown'
        assert 'Something went wrong' in result['user_message']
        assert not result['should_retry']


class TestSystemInstructionValidation:
    """Test system instruction compliance validation."""
    
    def test_detects_ai_self_reference(self):
        """Should detect AI self-references."""
        from app.agents.orchestrator import validate_system_instruction_response
        
        is_valid, violations = validate_system_instruction_response(
            "As an AI, I cannot help with that."
        )
        assert not is_valid
        assert any("AI" in v for v in violations)
    
    def test_detects_deflection_language(self):
        """Should detect deflection language."""
        from app.agents.orchestrator import validate_system_instruction_response
        
        is_valid, violations = validate_system_instruction_response(
            "I have limitations and cannot assist with this."
        )
        assert not is_valid
        assert any("deflection" in v.lower() for v in violations)
    
    def test_detects_meta_commentary(self):
        """Should detect meta-commentary."""
        from app.agents.orchestrator import validate_system_instruction_response
        
        is_valid, violations = validate_system_instruction_response(
            "I've begun analyzing the screen to help you."
        )
        assert not is_valid
        assert any("meta-commentary" in v.lower() or "narration" in v.lower() for v in violations)
    
    def test_accepts_valid_response(self):
        """Should accept valid, direct responses."""
        from app.agents.orchestrator import validate_system_instruction_response
        
        is_valid, violations = validate_system_instruction_response(
            "You're on Gmail. I see 15 unread messages in your inbox."
        )
        assert is_valid
        assert len(violations) == 0


class TestDestructiveActionDetection:
    """Test destructive action detection."""
    
    def test_detects_delete_action(self):
        """Should detect delete as destructive."""
        from app.agents.orchestrator import requires_confirmation
        
        assert requires_confirmation("delete this email")
        assert requires_confirmation("Delete my account")
    
    def test_detects_purchase_action(self):
        """Should detect purchase as destructive."""
        from app.agents.orchestrator import requires_confirmation
        
        assert requires_confirmation("buy this item")
        assert requires_confirmation("Purchase the subscription")
    
    def test_detects_terminate_action(self):
        """Should detect terminate/bank/financial as destructive."""
        from app.agents.orchestrator import requires_confirmation

        assert requires_confirmation("terminate my account")
        assert requires_confirmation("transfer money from my bank")
        # "submit" and "send" intentionally removed from DESTRUCTIVE_KEYWORDS —
        # they caused double-confirm UX when user said "send it" as a confirmation.
        # Gemini now handles email-send confirmation contextually via confirm_action.
        assert not requires_confirmation("submit the form")
        assert not requires_confirmation("send this email")
    
    def test_rejects_safe_actions(self):
        """Should not flag safe actions."""
        from app.agents.orchestrator import requires_confirmation
        
        assert not requires_confirmation("click the search button")
        assert not requires_confirmation("scroll down")
        assert not requires_confirmation("read the page")


class TestSpectraState:
    """Test state machine functionality."""
    
    def test_initializes_correctly(self):
        """Should initialize with correct defaults."""
        from app.agents.orchestrator import SpectraState
        
        state = SpectraState()
        assert state.current_app is None
        assert state.last_action is None
        assert state.awaiting_confirmation is False
        assert len(state.snapshots) == 0
    
    def test_detects_stale_screen(self):
        """Should detect when screen context is stale."""
        from app.agents.orchestrator import SpectraState
        import time
        
        state = SpectraState()
        state.last_screen_time = time.time() - 10  # 10 seconds ago
        
        assert state.needs_fresh_screen(max_age_seconds=5)
        assert not state.needs_fresh_screen(max_age_seconds=15)
    
    def test_updates_from_screen_description(self):
        """Should extract app context from screen description."""
        from app.agents.orchestrator import SpectraState
        
        state = SpectraState()
        state.update_from_screen_description("You're on Gmail, viewing your inbox")
        
        assert state.current_app == 'gmail'
        assert state.last_screen_time > 0
    
    def test_records_action(self):
        """Should record actions correctly."""
        from app.agents.orchestrator import SpectraState
        
        state = SpectraState()
        state.record_action("click_element", {"x": 100, "y": 200})
        
        assert state.last_action == "click_element"
        assert state.last_coordinates == (100, 200)
    
    def test_injects_context_hint(self):
        """Should inject context hints into user input."""
        from app.agents.orchestrator import SpectraState
        
        state = SpectraState()
        state.current_app = "gmail"
        
        result = state.inject_context_hint("read my emails")
        assert "[Context: currently in gmail]" in result
        assert "read my emails" in result


class TestResponsePostprocessing:
    """Test response postprocessing."""
    
    def test_removes_narration(self):
        """Should remove narration from responses."""
        from app.agents.orchestrator import postprocess_spectra_reply
        
        text = "I've begun analyzing. You're on Gmail."
        result = postprocess_spectra_reply(text)
        
        assert "I've begun" not in result
        assert "You're on Gmail" in result
    
    def test_fixes_ai_references(self):
        """Should auto-fix AI references."""
        from app.agents.orchestrator import postprocess_spectra_reply
        
        text = "As an AI, I can help you navigate."
        result = postprocess_spectra_reply(text)
        
        assert "AI" not in result or "Spectra" in result
    
    def test_removes_deflection_language(self):
        """Should remove deflection language."""
        from app.agents.orchestrator import postprocess_spectra_reply
        
        text = "I have limitations but I'll try to help."
        result = postprocess_spectra_reply(text)
        
        assert "I have limitations" not in result


class TestInteractionLogging:
    """Test interaction logging functionality."""
    
    def test_logs_interaction(self, tmp_path, monkeypatch):
        """Should log interactions to file."""
        from app.agents.orchestrator import log_interaction
        import json
        
        # Use monkeypatch to override the config constant
        log_file = tmp_path / "test_traces.jsonl"
        monkeypatch.setattr("app.agents.orchestrator.INTERACTION_LOG_PATH", str(log_file))
        
        log_interaction(
            user_input="test input",
            tool_calls=[{"name": "describe_screen", "args": {}}],
            model_response="test response",
            violations=[]
        )
        
        # Verify file was created and contains data
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            line = f.readline()
            data = json.loads(line)
            assert data['user'] == "test input"
            assert data['response'] == "test response"
    
    def test_handles_logging_errors_gracefully(self):
        """Should handle logging errors without crashing."""
        from app.agents.orchestrator import log_interaction
        import app.agents.config as config
        
        # Set invalid path
        original_path = config.INTERACTION_LOG_PATH
        config.INTERACTION_LOG_PATH = "/invalid/path/that/does/not/exist/traces.jsonl"
        
        try:
            # Should not raise exception
            log_interaction(
                user_input="test",
                tool_calls=[],
                model_response="test",
                violations=[]
            )
        finally:
            config.INTERACTION_LOG_PATH = original_path


# ━━━ PROPERTY-BASED TESTS ━━━

class TestNarrationRemovalProperties:
    """Property-based tests for narration removal."""
    
    def test_idempotent(self):
        """Applying remove_narration twice should give same result."""
        from app.agents.orchestrator import remove_narration
        
        text = "I've begun analyzing. You're on Gmail. I'm currently checking buttons."
        result1 = remove_narration(text)
        result2 = remove_narration(result1)
        
        assert result1 == result2
    
    def test_preserves_length_order(self):
        """Result should not be longer than input."""
        from app.agents.orchestrator import remove_narration
        
        text = "I've begun analyzing the screen. You're on Gmail."
        result = remove_narration(text)
        
        assert len(result) <= len(text)
    
    def test_never_adds_forbidden_patterns(self):
        """Should never introduce forbidden patterns."""
        from app.agents.orchestrator import remove_narration
        
        text = "You're on Gmail. I see 15 messages."
        result = remove_narration(text)
        
        for forbidden in FORBIDDEN_SENTENCE_STARTS:
            assert forbidden not in result.lower()


# ━━━ INTEGRATION TESTS ━━━

class TestEndToEndWorkflow:
    """Test complete workflows."""
    
    def test_location_query_workflow(self):
        """Test complete location query workflow."""
        from app.agents.orchestrator import (
            is_location_query,
            SpectraState,
            postprocess_spectra_reply
        )
        
        user_input = "where am i?"
        assert is_location_query(user_input)
        
        state = SpectraState()
        enhanced_input = state.inject_context_hint(user_input)
        
        # Simulate model response
        raw_response = "I've begun analyzing. You're on Gmail."
        cleaned_response = postprocess_spectra_reply(raw_response)
        
        assert "I've begun" not in cleaned_response
        assert "Gmail" in cleaned_response
    
    def test_destructive_action_workflow(self):
        """Test complete destructive action workflow."""
        from app.agents.orchestrator import (
            requires_confirmation,
            get_confirmation_reminder,
            SpectraState
        )
        
        user_input = "delete this email"
        assert requires_confirmation(user_input)
        
        reminder = get_confirmation_reminder(user_input)
        assert "confirm_action" in reminder
        
        state = SpectraState()
        state.awaiting_confirmation = True
        enhanced_input = state.inject_context_hint("yes, delete it")
        
        assert "waiting for confirm_action" in enhanced_input.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
