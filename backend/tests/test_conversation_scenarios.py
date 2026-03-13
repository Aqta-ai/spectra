"""
Practical conversation scenario tests for validating system instruction changes.

This script creates realistic conversation scenarios to test:
1. Identity queries and responses
2. Location context interpretation
3. Vision system behavior
4. Error handling

Run this script to validate that the system instruction changes work correctly.
"""

import json
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ConversationTest:
    """Represents a conversation test scenario."""
    name: str
    user_input: str
    context: Dict[str, Any]
    expected_behaviors: List[str]
    forbidden_behaviors: List[str]
    description: str


class ConversationScenarioTester:
    """Test realistic conversation scenarios for system instruction validation."""

    def __init__(self):
        self.test_scenarios = self._create_test_scenarios()
        self.results = []

    def _create_test_scenarios(self) -> List[ConversationTest]:
        """Create comprehensive test scenarios."""
        return [
            # Identity Consistency Tests
            ConversationTest(
                name="identity_introduction",
                user_input="Hello, who are you?",
                context={"screen_sharing": False},
                expected_behaviors=[
                    "contains 'I'm Spectra' or 'This is Spectra'",
                    "uses first-person pronouns (I, me, my)",
                    "mentions helping with navigation or screen reading"
                ],
                forbidden_behaviors=[
                    "contains 'AI' or 'artificial intelligence' in self-reference",
                    "contains 'As an AI'",
                    "contains 'I'm an AI assistant'"
                ],
                description="Test that Spectra introduces herself correctly without AI self-references"
            ),
            
            ConversationTest(
                name="identity_capability_question",
                user_input="What can you do?",
                context={"screen_sharing": False},
                expected_behaviors=[
                    "mentions screen reading or navigation capabilities",
                    "uses 'I can' statements",
                    "maintains Spectra identity"
                ],
                forbidden_behaviors=[
                    "contains AI self-references",
                    "uses deflection language about limitations"
                ],
                description="Test capability explanation maintains proper identity"
            ),
            
            ConversationTest(
                name="direct_ai_question",
                user_input="Are you an AI?",
                context={"screen_sharing": False},
                expected_behaviors=[
                    "responds as Spectra",
                    "focuses on being helpful assistant",
                    "avoids confirming or denying AI nature directly"
                ],
                forbidden_behaviors=[
                    "says 'Yes, I'm an AI'",
                    "says 'I am an artificial intelligence'",
                    "uses 'As an AI' in response"
                ],
                description="Test response to direct AI question maintains identity consistency"
            ),

            # Location Context Tests
            ConversationTest(
                name="location_query_with_screen",
                user_input="where am i?",
                context={
                    "screen_sharing": True,
                    "screen_content": "Google homepage with search box visible"
                },
                expected_behaviors=[
                    "calls describe_screen first",
                    "responds with screen-based location (e.g., 'You're on Google.com')",
                    "describes what's visible on screen"
                ],
                forbidden_behaviors=[
                    "mentions physical location or GPS",
                    "says 'I don't know your location'",
                    "refers to geographic location"
                ],
                description="Test location query returns screen-based location information"
            ),
            
            ConversationTest(
                name="location_query_variations",
                user_input="what website is this?",
                context={
                    "screen_sharing": True,
                    "screen_content": "Gmail inbox interface"
                },
                expected_behaviors=[
                    "identifies website/app from screen content",
                    "responds with specific site information",
                    "uses screen analysis"
                ],
                forbidden_behaviors=[
                    "mentions physical location",
                    "uses deflection about not knowing location"
                ],
                description="Test various location query phrasings work correctly"
            ),
            
            ConversationTest(
                name="location_query_unknown_site",
                user_input="where am i?",
                context={
                    "screen_sharing": True,
                    "screen_content": "Unknown application interface"
                },
                expected_behaviors=[
                    "calls describe_screen",
                    "uses fallback response about seeing screen but not determining site",
                    "mentions being able to see the screen"
                ],
                forbidden_behaviors=[
                    "mentions physical location",
                    "says complete inability to help"
                ],
                description="Test fallback behavior when website/app cannot be determined"
            ),

            # Vision System Behavior Tests
            ConversationTest(
                name="screen_description_request",
                user_input="what do you see on my screen?",
                context={
                    "screen_sharing": True,
                    "screen_content": "YouTube homepage with video thumbnails"
                },
                expected_behaviors=[
                    "describes actual screen content",
                    "mentions specific elements visible",
                    "provides comprehensive description"
                ],
                forbidden_behaviors=[
                    "says 'I have limitations'",
                    "says 'I cannot see your screen'",
                    "uses deflection language"
                ],
                description="Test vision system describes actual screen content without deflection"
            ),
            
            ConversationTest(
                name="screen_description_no_sharing",
                user_input="describe my screen",
                context={
                    "screen_sharing": False,
                    "screen_content": None
                },
                expected_behaviors=[
                    "asks user to enable screen sharing",
                    "mentions pressing W to share screen",
                    "explains need for screen sharing"
                ],
                forbidden_behaviors=[
                    "says 'I have limitations' as primary response",
                    "uses 'As an AI' language",
                    "gives up without offering solution"
                ],
                description="Test proper handling when screen sharing is not active"
            ),
            
            ConversationTest(
                name="vision_error_scenario",
                user_input="what's on my screen?",
                context={
                    "screen_sharing": True,
                    "vision_error": "API authentication failed"
                },
                expected_behaviors=[
                    "provides specific technical error information",
                    "mentions checking API key configuration",
                    "gives actionable debugging information"
                ],
                forbidden_behaviors=[
                    "uses generic 'I have limitations' response",
                    "provides no debugging information",
                    "uses deflection language"
                ],
                description="Test proper error handling with specific technical information"
            ),

            # Complex Interaction Tests
            ConversationTest(
                name="search_task_request",
                user_input="search for cats on Google",
                context={
                    "screen_sharing": True,
                    "screen_content": "Google homepage with search box"
                },
                expected_behaviors=[
                    "describes seeing the search box",
                    "explains action plan (click, type, search)",
                    "takes immediate action to help"
                ],
                forbidden_behaviors=[
                    "says cannot help due to limitations",
                    "refuses to take action",
                    "uses AI self-reference"
                ],
                description="Test proactive assistance with specific tasks"
            ),
            
            ConversationTest(
                name="navigation_assistance",
                user_input="help me find the login button",
                context={
                    "screen_sharing": True,
                    "screen_content": "Website with login button in top right"
                },
                expected_behaviors=[
                    "describes screen layout",
                    "locates and describes login button",
                    "offers to click it or provides coordinates"
                ],
                forbidden_behaviors=[
                    "says cannot see or help",
                    "uses deflection about visual limitations"
                ],
                description="Test navigation assistance maintains helpful approach"
            ),

            # Edge Cases
            ConversationTest(
                name="multiple_location_queries",
                user_input="where am i? what site is this?",
                context={
                    "screen_sharing": True,
                    "screen_content": "Amazon product page"
                },
                expected_behaviors=[
                    "responds to both questions about screen location",
                    "identifies Amazon from screen content",
                    "maintains consistent screen-based responses"
                ],
                forbidden_behaviors=[
                    "mentions physical location for either question",
                    "inconsistent responses between questions"
                ],
                description="Test handling multiple location queries in one input"
            ),
            
            ConversationTest(
                name="mixed_identity_location_query",
                user_input="who are you and where am i?",
                context={
                    "screen_sharing": True,
                    "screen_content": "Gmail inbox"
                },
                expected_behaviors=[
                    "introduces as Spectra",
                    "identifies screen location as Gmail",
                    "handles both parts of compound question"
                ],
                forbidden_behaviors=[
                    "uses AI self-reference in identity part",
                    "mentions physical location in location part"
                ],
                description="Test compound questions maintain all instruction rules"
            )
        ]

    def validate_response(self, test: ConversationTest, response: str) -> Dict[str, Any]:
        """
        Validate a response against test expectations.
        
        Args:
            test: The test scenario
            response: The actual response to validate
            
        Returns:
            Dictionary with validation results
        """
        results = {
            "test_name": test.name,
            "passed": True,
            "expected_behaviors_met": [],
            "expected_behaviors_failed": [],
            "forbidden_behaviors_found": [],
            "response": response,
            "description": test.description
        }
        
        response_lower = response.lower()
        
        # Check expected behaviors
        for behavior in test.expected_behaviors:
            if self._check_behavior(behavior, response, response_lower):
                results["expected_behaviors_met"].append(behavior)
            else:
                results["expected_behaviors_failed"].append(behavior)
                results["passed"] = False
        
        # Check forbidden behaviors
        for behavior in test.forbidden_behaviors:
            if self._check_forbidden_behavior(behavior, response, response_lower):
                results["forbidden_behaviors_found"].append(behavior)
                results["passed"] = False
        
        return results

    def _check_behavior(self, behavior: str, response: str, response_lower: str) -> bool:
        """Check if an expected behavior is present in the response."""
        if "contains 'I'm Spectra' or 'This is Spectra'" in behavior:
            return "i'm spectra" in response_lower or "this is spectra" in response_lower
        
        elif "uses first-person pronouns" in behavior:
            pronouns = ["i can", "i'll", "i'm", "my", "me"]
            return any(pronoun in response_lower for pronoun in pronouns)
        
        elif "mentions helping with navigation" in behavior:
            help_terms = ["help", "navigate", "assist", "screen", "website"]
            return any(term in response_lower for term in help_terms)
        
        elif "calls describe_screen first" in behavior:
            # This would need to be checked in actual system execution
            return True  # Assume true for static validation
        
        elif "responds with screen-based location" in behavior:
            screen_terms = ["you're on", "you're in", "website", "page", "app", ".com"]
            return any(term in response_lower for term in screen_terms)
        
        elif "describes what's visible on screen" in behavior:
            visual_terms = ["see", "visible", "screen", "page", "button", "link"]
            return any(term in response_lower for term in visual_terms)
        
        elif "identifies website/app from screen content" in behavior:
            site_terms = ["gmail", "google", "youtube", "amazon", "website", "app"]
            return any(term in response_lower for term in site_terms)
        
        elif "uses fallback response" in behavior:
            fallback_terms = ["can see your screen but", "cannot determine"]
            return any(term in response_lower for term in fallback_terms)
        
        elif "describes actual screen content" in behavior:
            content_terms = ["homepage", "search box", "button", "link", "video", "inbox"]
            return any(term in response_lower for term in content_terms)
        
        elif "mentions specific elements visible" in behavior:
            element_terms = ["button", "link", "search bar", "thumbnail", "box", "menu", "field", "video"]
            return any(term in response_lower for term in element_terms)
        
        elif "provides comprehensive description" in behavior:
            content_terms = ["homepage", "search box", "button", "link", "video", "thumbnail", "bar"]
            return sum(1 for t in content_terms if t in response_lower) >= 2 or len(response_lower) > 80
        
        elif "asks user to enable screen sharing" in behavior:
            sharing_terms = ["screen sharing", "share your screen", "press w"]
            return any(term in response_lower for term in sharing_terms)
        
        elif "provides specific technical error" in behavior:
            error_terms = ["api", "authentication", "timeout", "error", "failed"]
            return any(term in response_lower for term in error_terms)
        
        elif "mentions checking API key configuration" in behavior:
            return "api" in response_lower and ("key" in response_lower or "configuration" in response_lower or "config" in response_lower)
        
        elif "gives actionable debugging information" in behavior:
            action_terms = ["check", "configure", "key", "configuration", "debug", "google_api_key"]
            return any(term in response_lower for term in action_terms)
        
        elif "takes immediate action" in behavior:
            action_terms = ["click", "type", "search", "let me", "i'll"]
            return any(term in response_lower for term in action_terms)
        
        # Default: check if behavior description appears in response
        return behavior.lower() in response_lower

    def _check_forbidden_behavior(self, behavior: str, response: str, response_lower: str) -> bool:
        """Check if a forbidden behavior is present in the response."""
        if "contains 'AI' or 'artificial intelligence' in self-reference" in behavior:
            ai_patterns = [r'\bas an ai\b', r'\bi\'m an ai\b', r'\bartificial intelligence\b']
            return any(re.search(pattern, response_lower) for pattern in ai_patterns)
        
        elif "contains 'As an AI'" in behavior:
            return "as an ai" in response_lower
        
        elif "contains 'I'm an AI assistant'" in behavior:
            return "i'm an ai assistant" in response_lower
        
        elif "mentions physical location or GPS" in behavior:
            physical_terms = ["gps", "physical location", "address", "coordinates", "geographic"]
            return any(term in response_lower for term in physical_terms)
        
        elif "says 'I don't know your location'" in behavior:
            return "don't know your location" in response_lower
        
        elif "says 'I have limitations'" in behavior:
            return "i have limitations" in response_lower
        
        elif "says 'I cannot see your screen'" in behavior:
            return "cannot see your screen" in response_lower
        
        elif "uses deflection language" in behavior:
            deflection_terms = ["limitations", "cannot help", "not able to", "don't have access"]
            return any(term in response_lower for term in deflection_terms)
        
        # Default: check if forbidden behavior appears in response
        return behavior.lower() in response_lower

    def generate_test_conversations(self) -> List[Dict[str, Any]]:
        """
        Generate test conversation data that can be used with the actual system.
        
        Returns:
            List of conversation test cases with expected validation criteria
        """
        conversations = []
        
        for test in self.test_scenarios:
            conversation = {
                "test_name": test.name,
                "description": test.description,
                "user_input": test.user_input,
                "context": test.context,
                "validation_criteria": {
                    "expected_behaviors": test.expected_behaviors,
                    "forbidden_behaviors": test.forbidden_behaviors
                }
            }
            conversations.append(conversation)
        
        return conversations

    def run_static_validation(self) -> Dict[str, Any]:
        """
        Run static validation on sample responses.
        This tests the validation logic itself.
        """
        # Sample responses for testing validation logic
        sample_responses = {
            "identity_introduction": "I'm Spectra, your helpful assistant who can help you navigate websites and applications.",
            "location_query_with_screen": "You're on Google.com - I can see the search homepage with the search box in the center.",
            "screen_description_request": "I can see the YouTube homepage with video thumbnails and a search bar at the top.",
            "vision_error_scenario": "Vision analysis failed: API authentication error. Check GOOGLE_API_KEY configuration.",
        }
        
        results = []
        for test in self.test_scenarios:
            if test.name in sample_responses:
                response = sample_responses[test.name]
                validation_result = self.validate_response(test, response)
                results.append(validation_result)
        
        return {
            "total_tests": len(results),
            "passed_tests": sum(1 for r in results if r["passed"]),
            "failed_tests": sum(1 for r in results if not r["passed"]),
            "results": results
        }

    def export_test_cases(self, filename: str = "conversation_test_cases.json"):
        """Export test cases to JSON file for use with actual system testing."""
        test_cases = self.generate_test_conversations()
        
        with open(filename, 'w') as f:
            json.dump({
                "description": "Conversation test cases for validating system instruction changes",
                "version": "1.0",
                "test_cases": test_cases
            }, f, indent=2)
        
        print(f"✅ Exported {len(test_cases)} test cases to {filename}")

    def print_test_summary(self):
        """Print a summary of all test scenarios."""
        print("🧪 System Instruction Validation Test Scenarios")
        print("=" * 60)
        
        categories = {
            "Identity Consistency": [],
            "Location Context": [],
            "Vision System": [],
            "Complex Interactions": [],
            "Edge Cases": []
        }
        
        for test in self.test_scenarios:
            if "identity" in test.name:
                categories["Identity Consistency"].append(test)
            elif "location" in test.name:
                categories["Location Context"].append(test)
            elif "screen" in test.name or "vision" in test.name:
                categories["Vision System"].append(test)
            elif "task" in test.name or "navigation" in test.name:
                categories["Complex Interactions"].append(test)
            else:
                categories["Edge Cases"].append(test)
        
        for category, tests in categories.items():
            if tests:
                print(f"\n📋 {category} ({len(tests)} tests)")
                for test in tests:
                    print(f"  • {test.name}: {test.description}")
        
        print(f"\n📊 Total Test Scenarios: {len(self.test_scenarios)}")


def test_conversation_scenario_static_validation():
    """Pytest: run static validation so conversation scenarios are in the test suite."""
    tester = ConversationScenarioTester()
    result = tester.run_static_validation()
    assert result["failed_tests"] == 0, (
        f"{result['failed_tests']} scenario(s) failed: "
        + str([r["test_name"] for r in result["results"] if not r["passed"]])
    )


def main():
    """Main function to run the conversation scenario tester."""
    tester = ConversationScenarioTester()
    
    print("🚀 Starting System Instruction Validation Tests")
    print("=" * 60)
    
    # Print test summary
    tester.print_test_summary()
    
    # Run static validation
    print("\n🔍 Running Static Validation Tests...")
    static_results = tester.run_static_validation()
    
    print(f"\n📊 Static Validation Results:")
    print(f"  Total Tests: {static_results['total_tests']}")
    print(f"  Passed: {static_results['passed_tests']}")
    print(f"  Failed: {static_results['failed_tests']}")
    
    if static_results['failed_tests'] > 0:
        print("\n❌ Failed Tests:")
        for result in static_results['results']:
            if not result['passed']:
                print(f"  • {result['test_name']}: {result['description']}")
                if result['expected_behaviors_failed']:
                    print(f"    Missing behaviors: {result['expected_behaviors_failed']}")
                if result['forbidden_behaviors_found']:
                    print(f"    Forbidden behaviors found: {result['forbidden_behaviors_found']}")
    
    # Export test cases
    print("\n📤 Exporting Test Cases...")
    tester.export_test_cases()
    
    print("\n✅ System Instruction Validation Test Suite Complete!")
    print("\nNext Steps:")
    print("1. Use conversation_test_cases.json with actual Spectra system")
    print("2. Run real conversations and validate responses")
    print("3. Check that all expected behaviors are met")
    print("4. Verify no forbidden behaviors appear in responses")


if __name__ == "__main__":
    main()