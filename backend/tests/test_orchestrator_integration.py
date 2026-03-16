"""Integration tests for Spectra orchestrator with real API interactions."""

import pytest
import os
import time
from unittest.mock import Mock, patch, AsyncMock
from app.agents.orchestrator import (
    SPECTRA_SYSTEM_INSTRUCTION,
    SPECTRA_TOOLS,
    SpectraState,
    classify_vision_error,
    log_interaction,
    get_training_dataset_stats,
    postprocess_spectra_reply,
)
from app.agents.config import INTERACTION_LOG_PATH


@pytest.mark.integration
class TestOrchestratorIntegration:
    """Integration tests that verify orchestrator works with external systems."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        """Setup and teardown for each test."""
        # Use temporary log file for tests
        self.original_log_path = INTERACTION_LOG_PATH
        test_log_path = tmp_path / "test_traces.jsonl"
        
        with patch('app.agents.orchestrator.INTERACTION_LOG_PATH', str(test_log_path)):
            yield
        
        # Cleanup
        if test_log_path.exists():
            test_log_path.unlink()
    
    def test_system_instruction_is_valid(self):
        """Verify system instruction is properly formatted and complete."""
        assert len(SPECTRA_SYSTEM_INSTRUCTION) > 1000, "System instruction too short"
        assert "Spectra" in SPECTRA_SYSTEM_INSTRUCTION, "Missing identity"
        assert "describe_screen" in SPECTRA_SYSTEM_INSTRUCTION, "Missing tool reference"
        assert "CRITICAL" in SPECTRA_SYSTEM_INSTRUCTION, "Missing critical rules"
        
        # Verify no placeholder text
        assert "TODO" not in SPECTRA_SYSTEM_INSTRUCTION
        assert "FIXME" not in SPECTRA_SYSTEM_INSTRUCTION
        assert "{{" not in SPECTRA_SYSTEM_INSTRUCTION
    
    def test_tools_are_properly_defined(self):
        """Verify all tools have proper schemas."""
        assert len(SPECTRA_TOOLS) > 0, "No tools defined"
        
        tool = SPECTRA_TOOLS[0]
        assert hasattr(tool, 'function_declarations'), "Missing function declarations"
        
        functions = tool.function_declarations
        assert len(functions) > 0, "No functions declared"
        
        # Verify each function has required fields
        for func in functions:
            assert hasattr(func, 'name'), f"Function missing name"
            assert hasattr(func, 'description'), f"Function {func.name} missing description"
            assert hasattr(func, 'parameters'), f"Function {func.name} missing parameters"
            
            # Verify description is meaningful
            assert len(func.description) > 20, f"Function {func.name} has too short description"
    
    def test_end_to_end_location_query_workflow(self):
        """Test complete workflow for location query."""
        state = SpectraState()
        
        # Simulate user asking "where am I?"
        user_input = "where am I?"
        
        # State should recognize this needs fresh screen
        assert state.needs_fresh_screen(), "Should need fresh screen initially"
        
        # Simulate screen description
        screen_desc = "Gmail - Inbox - 15 unread messages"
        state.update_from_screen_description(screen_desc)
        
        # Verify state updated
        assert state.current_app == "gmail", f"Expected gmail, got {state.current_app}"
        assert not state.needs_fresh_screen(), "Should not need fresh screen after update"
        
        # Simulate model response
        raw_response = "You're on Gmail - I can see your inbox with 15 unread messages"
        cleaned_response = postprocess_spectra_reply(raw_response)
        
        # Verify response is clean
        assert "Gmail" in cleaned_response
        assert "inbox" in cleaned_response
        assert "I've" not in cleaned_response.lower()
        assert "I'm analyzing" not in cleaned_response.lower()
    
    def test_end_to_end_destructive_action_workflow(self):
        """Test complete workflow for destructive action."""
        state = SpectraState()
        
        # Simulate user asking to delete
        user_input = "delete this email"
        
        # Inject context hint
        enhanced_input = state.inject_context_hint(user_input)
        assert "confirm_action" in enhanced_input, "Should remind to confirm"
        
        # Simulate confirmation
        state.awaiting_confirmation = True
        
        # Verify state reflects waiting
        next_input = "yes, delete it"
        enhanced_next = state.inject_context_hint(next_input)
        assert "waiting for confirm_action" in enhanced_next.lower()
    
    def test_interaction_logging_creates_valid_jsonl(self, tmp_path):
        """Test that interaction logging creates valid JSONL format."""
        test_log = tmp_path / "test_log.jsonl"
        
        with patch('app.agents.orchestrator.INTERACTION_LOG_PATH', str(test_log)):
            # Log multiple interactions
            for i in range(3):
                log_interaction(
                    user_input=f"test query {i}",
                    tool_calls=[{"name": "describe_screen", "args": {}}],
                    model_response=f"test response {i}",
                    violations=[]
                )
        
        # Verify file exists and is valid JSONL
        assert test_log.exists(), "Log file not created"
        
        import json
        with open(test_log, 'r') as f:
            lines = f.readlines()
            assert len(lines) == 3, f"Expected 3 lines, got {len(lines)}"
            
            for line in lines:
                data = json.loads(line)  # Should not raise
                assert "timestamp" in data
                assert "user" in data
                assert "tool_calls" in data
                assert "response" in data
                assert "quality" in data
    
    def test_log_rotation_works(self, tmp_path):
        """Test that log rotation works when file exceeds size limit."""
        test_log = tmp_path / "test_log.jsonl"
        
        with patch('app.agents.orchestrator.INTERACTION_LOG_PATH', str(test_log)):
            with patch('app.agents.orchestrator.MAX_LOG_FILE_SIZE_MB', 0.000001):  # Very small limit
                # Create a large log entry
                large_response = "x" * 10000
                
                log_interaction(
                    user_input="test",
                    tool_calls=[],
                    model_response=large_response,
                    violations=[]
                )
                
                # Log another entry to trigger rotation
                log_interaction(
                    user_input="test2",
                    tool_calls=[],
                    model_response="response2",
                    violations=[]
                )
                
                # Check that backup file was created
                backup_files = list(tmp_path.glob("test_log.jsonl.*"))
                assert len(backup_files) > 0, "Backup file not created"
    
    def test_vision_error_classification_with_real_errors(self):
        """Test vision error classification with realistic error messages."""
        test_cases = [
            ("401 Unauthorized: Invalid API key", "authentication"),
            ("429 Too Many Requests: Rate limit exceeded", "rate_limit"),
            ("Request timed out after 30 seconds", "timeout"),
            ("Network connection failed: DNS resolution error", "network"),
            ("Invalid frame: Empty screen capture", "frame_invalid"),
            ("Gemini API error: Internal server error", "api_error"),
            ("Something went wrong", "unknown"),
        ]
        
        for error_msg, expected_type in test_cases:
            result = classify_vision_error(error_msg)
            assert result['type'] == expected_type, \
                f"Expected {expected_type} for '{error_msg}', got {result['type']}"
            assert result['user_message'], "User message should not be empty"
            assert isinstance(result['should_retry'], bool), "should_retry must be boolean"
    
    def test_state_machine_transitions(self):
        """Test state machine transitions through multiple interactions."""
        state = SpectraState()
        
        # Initial state
        assert state.current_app is None
        assert state.last_action is None
        assert not state.awaiting_confirmation
        
        # Transition 1: Screen description
        state.update_from_screen_description("Reddit - r/programming")
        assert state.current_app == "reddit"
        
        # Transition 2: Record action
        state.record_action("click_element", {"x": 100, "y": 200, "description": "upvote"})
        assert state.last_action == "click_element"
        assert state.last_coordinates == (100, 200)
        
        # Transition 3: Awaiting confirmation
        state.awaiting_confirmation = True
        hint = state.inject_context_hint("delete this post")
        assert "waiting for confirm_action" in hint.lower()
        
        # Transition 4: Confirmation received
        state.awaiting_confirmation = False
        hint = state.inject_context_hint("yes")
        assert "waiting for confirm_action" not in hint.lower()
    
    def test_dataset_stats_with_real_data(self, tmp_path):
        """Test dataset statistics with real logged data."""
        test_log = tmp_path / "test_log.jsonl"
        
        with patch('app.agents.orchestrator.INTERACTION_LOG_PATH', str(test_log)):
            # Log interactions with different qualities
            log_interaction("query1", [], "response1", violations=[])  # good
            log_interaction("query2", [], "response2", violations=["violation"])  # needs review
            log_interaction("query3", [{"name": "describe_screen", "args": {}}], "response3", violations=[])  # good
            log_interaction("query4", [{"name": "click_element", "args": {}}], "response4", violations=[])  # good
            
            # Get stats
            stats = get_training_dataset_stats()
            
            assert stats['total_interactions'] == 4
            assert stats['good_quality'] == 3
            assert stats['needs_review'] == 1
            assert stats['unique_tools'] == 2  # describe_screen, click_element
    
    def test_response_postprocessing_preserves_valid_content(self):
        """Test that postprocessing doesn't remove valid content."""
        valid_responses = [
            "You're on Gmail with 5 unread messages",
            "I found the search button at the top right",
            "Clicking the submit button now",
            "The page has three main sections: header, content, and footer",
            "Great! The form was submitted successfully",
        ]
        
        for response in valid_responses:
            processed = postprocess_spectra_reply(response)
            # Should preserve most of the content
            assert len(processed) >= len(response) * 0.8, \
                f"Too much content removed from: {response}"
            # Should not be empty
            assert len(processed.strip()) > 0, f"Response became empty: {response}"
    
    def test_concurrent_logging_safety(self, tmp_path):
        """Test that concurrent logging doesn't corrupt the log file."""
        import threading
        test_log = tmp_path / "test_log.jsonl"
        
        with patch('app.agents.orchestrator.INTERACTION_LOG_PATH', str(test_log)):
            def log_worker(worker_id):
                for i in range(10):
                    log_interaction(
                        user_input=f"worker{worker_id}_query{i}",
                        tool_calls=[],
                        model_response=f"worker{worker_id}_response{i}",
                        violations=[]
                    )
            
            # Create multiple threads
            threads = [threading.Thread(target=log_worker, args=(i,)) for i in range(5)]
            
            # Start all threads
            for t in threads:
                t.start()
            
            # Wait for completion
            for t in threads:
                t.join()
            
            # Verify all entries are valid JSON
            import json
            with open(test_log, 'r') as f:
                lines = f.readlines()
                assert len(lines) == 50, f"Expected 50 lines, got {len(lines)}"
                
                for line in lines:
                    json.loads(line)  # Should not raise


@pytest.mark.integration
@pytest.mark.slow
class TestOrchestratorPerformance:
    """Performance-focused integration tests."""
    
    def test_narration_removal_performance(self):
        """Test that narration removal is fast enough."""
        from app.agents.orchestrator import remove_narration
        
        # Create a large response with narration
        text = """
        I've begun analyzing the screen context. Currently, I'm focusing on identifying
        all interactive elements. I'm now cataloging the buttons and links. I've pinpointed
        the main navigation menu. I've completed the initial analysis. To accomplish this,
        I've decided to use the describe_screen tool. My next step will be to create a
        comprehensive picture of the page layout.
        """ * 100  # Repeat 100 times
        
        start = time.perf_counter()
        result = remove_narration(text)
        duration = time.perf_counter() - start
        
        # Should complete in under 100ms even for large text
        assert duration < 0.1, f"Narration removal too slow: {duration:.3f}s"

        # Should remove some narration (sentence-start patterns); exact ratio depends on config
        assert len(result) <= len(text), "Narration removal should not expand text"
        assert len(result) < len(text), "Some narration should be removed"
    
    def test_state_update_performance(self):
        """Test that state updates are fast."""
        state = SpectraState()
        
        descriptions = [
            "Gmail - Inbox",
            "Reddit - r/programming",
            "GitHub - Pull Requests",
            "YouTube - Home",
            "Google Search - Results",
        ] * 100
        
        start = time.perf_counter()
        for desc in descriptions:
            state.update_from_screen_description(desc)
        duration = time.perf_counter() - start
        
        # Should handle 500 updates in under 200ms (relaxed for CI/machine variance)
        assert duration < 0.2, f"State updates too slow: {duration:.3f}s"
    
    def test_vision_error_classification_performance(self):
        """Test that error classification is fast."""
        errors = [
            "401 Unauthorized",
            "429 Rate limit exceeded",
            "Timeout after 30s",
            "Network error",
            "Invalid frame",
            "API error",
        ] * 100
        
        start = time.perf_counter()
        for error in errors:
            classify_vision_error(error)
        duration = time.perf_counter() - start
        
        # Should classify 600 errors in under 200ms (relaxed for CI/machine variance)
        assert duration < 0.2, f"Error classification too slow: {duration:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
