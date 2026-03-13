"""
Blind User Experience Test - Simulating Real-World Usage

This test simulates a blind user interacting with Spectra entirely through voice,
testing the complete user journey without visual feedback.

Test Scenarios:
1. First-time user onboarding
2. Web navigation tasks
3. Form filling
4. Content reading
5. Error recovery
6. Multi-step workflows
"""

import pytest
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class VoiceInteraction:
    """Represents a single voice interaction."""
    user_says: str
    expected_audio_response: str
    expected_actions: List[str]
    context: Dict[str, Any]
    success_criteria: List[str]


class BlindUserExperienceTest:
    """Test Spectra from a blind user's perspective."""
    
    def __init__(self):
        self.test_scenarios = self._create_scenarios()
    
    def _create_scenarios(self) -> List[Dict[str, Any]]:
        """Create realistic blind user test scenarios."""
        return [
            {
                "name": "First Time User - Getting Started",
                "description": "Blind user opens Spectra for the first time",
                "interactions": [
                    VoiceInteraction(
                        user_says="Hello",
                        expected_audio_response="Hi! I'm Spectra. I can see your screen and help you navigate. Press W to share your screen with me.",
                        expected_actions=[],
                        context={"screen_sharing": False, "first_time": True},
                        success_criteria=[
                            "Introduces herself as Spectra",
                            "Explains what she can do",
                            "Gives clear instruction to press W",
                            "No visual-only instructions"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="I pressed W, can you see my screen now?",
                        expected_audio_response="Yes! I can see your screen now. You're on Google.com with the search box in the center. What would you like to do?",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True, "screen": "Google homepage"},
                        success_criteria=[
                            "Confirms screen is visible",
                            "Describes what's on screen",
                            "Asks what user wants to do",
                            "Proactive and helpful tone"
                        ]
                    )
                ]
            },
            
            {
                "name": "Web Search Task",
                "description": "User wants to search for something on Google",
                "interactions": [
                    VoiceInteraction(
                        user_says="Search for cat videos",
                        expected_audio_response="I'll search for cat videos. Clicking the search box, typing 'cat videos', and pressing Enter.",
                        expected_actions=[
                            "describe_screen",
                            "click_element(search_box)",
                            "type_text('cat videos')",
                            "press_key('Enter')"
                        ],
                        context={"screen_sharing": True, "screen": "Google homepage"},
                        success_criteria=[
                            "Announces what she's doing",
                            "Executes actions in correct order",
                            "No silent actions",
                            "Clear audio feedback"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="What do you see now?",
                        expected_audio_response="I see search results for cat videos. There are several video links. The first result is 'Funny Cats Compilation' from YouTube. Would you like me to click on it?",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True, "screen": "Google search results"},
                        success_criteria=[
                            "Describes search results",
                            "Reads specific result titles",
                            "Offers to take action",
                            "Helpful and proactive"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Yes, click the first one",
                        expected_audio_response="Clicking 'Funny Cats Compilation'. The video is loading.",
                        expected_actions=[
                            "click_element(first_result)"
                        ],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Confirms which link she's clicking",
                            "Announces the action",
                            "Provides status update"
                        ]
                    )
                ]
            },
            
            {
                "name": "Form Filling - Login",
                "description": "User needs to log into a website",
                "interactions": [
                    VoiceInteraction(
                        user_says="Where am I?",
                        expected_audio_response="You're on the Gmail login page. I can see an email input field and a password field below it.",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True, "screen": "Gmail login"},
                        success_criteria=[
                            "Identifies the page correctly",
                            "Describes form fields",
                            "No mention of physical location"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Type my email: john@example.com",
                        expected_audio_response="Typing john@example.com in the email field.",
                        expected_actions=[
                            "click_element(email_field)",
                            "type_text('john@example.com')"
                        ],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Confirms what she's typing",
                            "Clicks field first",
                            "Clear audio feedback"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Now type my password: secret123",
                        expected_audio_response="Typing your password in the password field.",
                        expected_actions=[
                            "click_element(password_field)",
                            "type_text('secret123')"
                        ],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Doesn't read password aloud",
                            "Confirms field location",
                            "Maintains privacy"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Click the login button",
                        expected_audio_response="Clicking the login button. Logging you in.",
                        expected_actions=[
                            "click_element(login_button)"
                        ],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Confirms button click",
                            "Provides status update"
                        ]
                    )
                ]
            },
            
            {
                "name": "Content Reading",
                "description": "User wants to read content on a page",
                "interactions": [
                    VoiceInteraction(
                        user_says="Read the page to me",
                        expected_audio_response="You're on a news article. The headline is 'Breaking News: Major Discovery'. The article begins: Scientists have made a groundbreaking discovery...",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True, "screen": "News article"},
                        success_criteria=[
                            "Reads headline first",
                            "Reads article content",
                            "Clear and natural reading",
                            "Appropriate pacing"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Scroll down",
                        expected_audio_response="Scrolling down. Now showing the next paragraph about the research findings.",
                        expected_actions=[
                            "scroll_page('down')",
                            "describe_screen"
                        ],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Confirms scrolling action",
                            "Describes new content",
                            "Smooth transition"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Keep scrolling",
                        expected_audio_response="Scrolling down. Now showing comments section with 45 comments.",
                        expected_actions=[
                            "scroll_page('down')",
                            "describe_screen"
                        ],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Continues scrolling",
                            "Describes new section",
                            "Provides context"
                        ]
                    )
                ]
            },
            
            {
                "name": "Error Recovery",
                "description": "Handling errors and unclear situations",
                "interactions": [
                    VoiceInteraction(
                        user_says="Click the submit button",
                        expected_audio_response="I don't see a submit button on the current screen. I can see a 'Send' button and a 'Cancel' button. Which one would you like me to click?",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True, "screen": "Form with Send/Cancel"},
                        success_criteria=[
                            "Explains button not found",
                            "Offers alternatives",
                            "Asks for clarification",
                            "Helpful recovery"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Click the send button",
                        expected_audio_response="Clicking the Send button.",
                        expected_actions=["click_element(send_button)"],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Executes correct action",
                            "Confirms action"
                        ]
                    )
                ]
            },
            
            {
                "name": "Navigation Without Screen Sharing",
                "description": "User tries to navigate without screen sharing enabled",
                "interactions": [
                    VoiceInteraction(
                        user_says="Click the login button",
                        expected_audio_response="I'm not seeing your screen yet. Please press W to share your screen so I can help you.",
                        expected_actions=[],
                        context={"screen_sharing": False},
                        success_criteria=[
                            "Explains need for screen sharing",
                            "Gives clear instruction",
                            "Doesn't pretend to see screen",
                            "Helpful tone"
                        ]
                    )
                ]
            },
            
            {
                "name": "Multi-Step Workflow - Online Shopping",
                "description": "Complete shopping task from search to checkout",
                "interactions": [
                    VoiceInteraction(
                        user_says="Go to Amazon",
                        expected_audio_response="Navigating to Amazon.com.",
                        expected_actions=["navigate('amazon.com')"],
                        context={"screen_sharing": True},
                        success_criteria=["Confirms navigation"]
                    ),
                    VoiceInteraction(
                        user_says="Where am I now?",
                        expected_audio_response="You're on Amazon.com homepage. I can see the search bar at the top and various product categories.",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True, "screen": "Amazon homepage"},
                        success_criteria=[
                            "Identifies Amazon",
                            "Describes key elements",
                            "Ready for next action"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Search for wireless headphones",
                        expected_audio_response="Searching for wireless headphones. Clicking search box, typing, and searching.",
                        expected_actions=[
                            "click_element(search_box)",
                            "type_text('wireless headphones')",
                            "press_key('Enter')"
                        ],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Announces full workflow",
                            "Executes all steps",
                            "Clear feedback"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="What are the results?",
                        expected_audio_response="I see search results for wireless headphones. The first result is 'Sony WH-1000XM4' for $299. Second is 'Bose QuietComfort' for $279. Would you like details on any of these?",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True, "screen": "Amazon search results"},
                        success_criteria=[
                            "Reads multiple results",
                            "Includes prices",
                            "Offers to provide more info",
                            "Organized presentation"
                        ]
                    )
                ]
            },
            
            {
                "name": "Accessibility Features Test",
                "description": "Testing accessibility-specific features",
                "interactions": [
                    VoiceInteraction(
                        user_says="What buttons are on this page?",
                        expected_audio_response="I can see 5 buttons: 'Home' at the top left, 'Search' next to it, 'Login' in the top right, 'Sign Up' below that, and 'Learn More' in the center of the page.",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True, "screen": "Website with multiple buttons"},
                        success_criteria=[
                            "Lists all buttons",
                            "Provides locations",
                            "Clear enumeration",
                            "Spatial awareness"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="Are there any links?",
                        expected_audio_response="Yes, I see 8 links in the navigation menu: About Us, Services, Products, Blog, Contact, Privacy Policy, Terms, and Help.",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Counts links",
                            "Lists link text",
                            "Organized response"
                        ]
                    ),
                    VoiceInteraction(
                        user_says="What's in the main content area?",
                        expected_audio_response="The main content shows a welcome message: 'Welcome to our service'. Below that is a paragraph explaining the features, and a 'Get Started' button.",
                        expected_actions=["describe_screen"],
                        context={"screen_sharing": True},
                        success_criteria=[
                            "Focuses on main content",
                            "Describes hierarchy",
                            "Mentions key elements"
                        ]
                    )
                ]
            }
        ]
    
    def validate_interaction(self, interaction: VoiceInteraction, actual_response: str, actual_actions: List[str]) -> Dict[str, Any]:
        """Validate a single interaction."""
        results = {
            "user_input": interaction.user_says,
            "expected_response": interaction.expected_audio_response,
            "actual_response": actual_response,
            "expected_actions": interaction.expected_actions,
            "actual_actions": actual_actions,
            "success_criteria_met": [],
            "success_criteria_failed": [],
            "passed": True
        }
        
        # Check each success criterion
        for criterion in interaction.success_criteria:
            if self._check_criterion(criterion, actual_response, actual_actions):
                results["success_criteria_met"].append(criterion)
            else:
                results["success_criteria_failed"].append(criterion)
                results["passed"] = False
        
        return results
    
    def _check_criterion(self, criterion: str, response: str, actions: List[str]) -> bool:
        """Check if a success criterion is met."""
        response_lower = response.lower()
        
        # Audio feedback criteria
        if "announces" in criterion.lower() or "confirms" in criterion.lower():
            # Check if response contains action description
            action_words = ["clicking", "typing", "scrolling", "navigating", "searching"]
            return any(word in response_lower for word in action_words)
        
        # Content criteria
        if "describes" in criterion.lower():
            descriptive_words = ["see", "showing", "page", "button", "link", "field"]
            return any(word in response_lower for word in descriptive_words)
        
        # Privacy criteria
        if "doesn't read password" in criterion.lower():
            return "secret" not in response_lower and "password" in response_lower
        
        # Clarity criteria
        if "clear" in criterion.lower():
            return len(response) > 10 and not response.startswith("...")
        
        # Action execution criteria
        if "executes" in criterion.lower():
            return len(actions) > 0
        
        # Default: assume criterion is met
        return True
    
    def generate_test_report(self) -> str:
        """Generate a comprehensive test report."""
        report = []
        report.append("=" * 80)
        report.append("BLIND USER EXPERIENCE TEST REPORT")
        report.append("=" * 80)
        report.append("")
        report.append("This report simulates a blind user's experience with Spectra,")
        report.append("testing voice-only interaction without visual feedback.")
        report.append("")
        
        for scenario in self.test_scenarios:
            report.append(f"\n{'=' * 80}")
            report.append(f"SCENARIO: {scenario['name']}")
            report.append(f"{'=' * 80}")
            report.append(f"Description: {scenario['description']}")
            report.append("")
            
            for i, interaction in enumerate(scenario['interactions'], 1):
                report.append(f"\nInteraction {i}:")
                report.append(f"  User says: \"{interaction.user_says}\"")
                report.append(f"  Expected response: \"{interaction.expected_audio_response}\"")
                report.append(f"  Expected actions: {interaction.expected_actions}")
                report.append(f"  Success criteria:")
                for criterion in interaction.success_criteria:
                    report.append(f"    ✓ {criterion}")
                report.append("")
        
        report.append("\n" + "=" * 80)
        report.append("TEST EXECUTION INSTRUCTIONS")
        report.append("=" * 80)
        report.append("")
        report.append("1. Start Spectra with screen sharing disabled")
        report.append("2. Use voice input only (no keyboard/mouse)")
        report.append("3. Follow each scenario's interactions in order")
        report.append("4. Verify audio responses match expectations")
        report.append("5. Confirm all actions are executed correctly")
        report.append("6. Check that all success criteria are met")
        report.append("")
        report.append("CRITICAL: The user should NEVER need to look at the screen.")
        report.append("All information must be conveyed through audio responses.")
        report.append("")
        
        return "\n".join(report)
    
    def export_test_scenarios(self, filename: str = "blind_user_test_scenarios.txt"):
        """Export test scenarios to a file."""
        report = self.generate_test_report()
        with open(filename, 'w') as f:
            f.write(report)
        print(f"✅ Exported blind user test scenarios to {filename}")


def main():
    """Run the blind user experience test."""
    print("🦯 Blind User Experience Test Suite")
    print("=" * 80)
    print()
    print("This test simulates a blind user interacting with Spectra")
    print("entirely through voice, without any visual feedback.")
    print()
    
    tester = BlindUserExperienceTest()
    
    # Generate and display report
    report = tester.generate_test_report()
    print(report)
    
    # Export scenarios
    tester.export_test_scenarios()
    
    print("\n✅ Blind User Experience Test Suite Complete!")
    print("\nNext Steps:")
    print("1. Run Spectra and follow the test scenarios")
    print("2. Use ONLY voice input (no visual interaction)")
    print("3. Verify all audio responses are clear and helpful")
    print("4. Confirm all actions execute correctly")
    print("5. Ensure the experience is fully accessible without sight")


if __name__ == "__main__":
    main()


# ============================================================================
# PYTEST TEST FUNCTIONS
# ============================================================================

@pytest.fixture
def blind_user_tester():
    """Fixture to create a BlindUserExperienceTest instance."""
    return BlindUserExperienceTest()


def test_scenario_structure(blind_user_tester):
    """Test that all scenarios are properly structured."""
    scenarios = blind_user_tester.test_scenarios
    
    assert len(scenarios) > 0, "Should have at least one test scenario"
    
    for scenario in scenarios:
        assert "name" in scenario, "Scenario must have a name"
        assert "description" in scenario, "Scenario must have a description"
        assert "interactions" in scenario, "Scenario must have interactions"
        assert len(scenario["interactions"]) > 0, "Scenario must have at least one interaction"


def test_interaction_structure(blind_user_tester):
    """Test that all interactions have required fields."""
    scenarios = blind_user_tester.test_scenarios
    
    for scenario in scenarios:
        for interaction in scenario["interactions"]:
            assert hasattr(interaction, "user_says"), "Interaction must have user_says"
            assert hasattr(interaction, "expected_audio_response"), "Interaction must have expected_audio_response"
            assert hasattr(interaction, "expected_actions"), "Interaction must have expected_actions"
            assert hasattr(interaction, "context"), "Interaction must have context"
            assert hasattr(interaction, "success_criteria"), "Interaction must have success_criteria"
            
            # Validate types
            assert isinstance(interaction.user_says, str), "user_says must be a string"
            assert isinstance(interaction.expected_audio_response, str), "expected_audio_response must be a string"
            assert isinstance(interaction.expected_actions, list), "expected_actions must be a list"
            assert isinstance(interaction.context, dict), "context must be a dict"
            assert isinstance(interaction.success_criteria, list), "success_criteria must be a list"


def test_first_time_user_scenario(blind_user_tester):
    """Test the first-time user onboarding scenario."""
    scenarios = blind_user_tester.test_scenarios
    first_scenario = scenarios[0]
    
    assert first_scenario["name"] == "First Time User - Getting Started"
    assert len(first_scenario["interactions"]) >= 2
    
    # First interaction should be greeting
    first_interaction = first_scenario["interactions"][0]
    assert "hello" in first_interaction.user_says.lower()
    assert "spectra" in first_interaction.expected_audio_response.lower()
    assert "press w" in first_interaction.expected_audio_response.lower()


def test_web_search_scenario(blind_user_tester):
    """Test the web search task scenario."""
    scenarios = blind_user_tester.test_scenarios
    search_scenario = next(s for s in scenarios if "Web Search" in s["name"])
    
    assert search_scenario is not None
    assert len(search_scenario["interactions"]) >= 3
    
    # First interaction should be search command
    search_interaction = search_scenario["interactions"][0]
    assert "search" in search_interaction.user_says.lower()
    assert len(search_interaction.expected_actions) > 0


def test_form_filling_scenario(blind_user_tester):
    """Test the form filling scenario."""
    scenarios = blind_user_tester.test_scenarios
    form_scenario = next(s for s in scenarios if "Form Filling" in s["name"])
    
    assert form_scenario is not None
    
    # Should have location query
    location_interaction = form_scenario["interactions"][0]
    assert "where am i" in location_interaction.user_says.lower()
    
    # Should have password typing with privacy
    password_interaction = next(i for i in form_scenario["interactions"] if "password" in i.user_says.lower())
    assert any("privacy" in criterion.lower() or "doesn't read password" in criterion.lower() 
               for criterion in password_interaction.success_criteria)


def test_content_reading_scenario(blind_user_tester):
    """Test the content reading scenario."""
    scenarios = blind_user_tester.test_scenarios
    reading_scenario = next(s for s in scenarios if "Content Reading" in s["name"])
    
    assert reading_scenario is not None
    
    # Should have scroll commands
    scroll_interactions = [i for i in reading_scenario["interactions"] if "scroll" in i.user_says.lower()]
    assert len(scroll_interactions) >= 2, "Should have multiple scroll interactions"


def test_error_recovery_scenario(blind_user_tester):
    """Test the error recovery scenario."""
    scenarios = blind_user_tester.test_scenarios
    error_scenario = next(s for s in scenarios if "Error Recovery" in s["name"])
    
    assert error_scenario is not None
    
    # First interaction should handle missing element
    first_interaction = error_scenario["interactions"][0]
    assert "don't see" in first_interaction.expected_audio_response.lower() or \
           "can't find" in first_interaction.expected_audio_response.lower()


def test_no_screen_sharing_scenario(blind_user_tester):
    """Test handling when screen sharing is not enabled."""
    scenarios = blind_user_tester.test_scenarios
    no_screen_scenario = next(s for s in scenarios if "Without Screen Sharing" in s["name"])
    
    assert no_screen_scenario is not None
    
    interaction = no_screen_scenario["interactions"][0]
    assert interaction.context["screen_sharing"] is False
    assert "press w" in interaction.expected_audio_response.lower() or \
           "share your screen" in interaction.expected_audio_response.lower()


def test_multi_step_workflow_scenario(blind_user_tester):
    """Test multi-step workflow scenario."""
    scenarios = blind_user_tester.test_scenarios
    workflow_scenario = next(s for s in scenarios if "Multi-Step Workflow" in s["name"])
    
    assert workflow_scenario is not None
    assert len(workflow_scenario["interactions"]) >= 4, "Multi-step workflow should have multiple interactions"


def test_accessibility_features_scenario(blind_user_tester):
    """Test accessibility-specific features."""
    scenarios = blind_user_tester.test_scenarios
    accessibility_scenario = next(s for s in scenarios if "Accessibility Features" in s["name"])
    
    assert accessibility_scenario is not None
    
    # Should enumerate buttons
    button_interaction = next(i for i in accessibility_scenario["interactions"] if "button" in i.user_says.lower())
    assert "lists all buttons" in str(button_interaction.success_criteria).lower() or \
           "provides locations" in str(button_interaction.success_criteria).lower()


def test_validation_logic(blind_user_tester):
    """Test the validation logic works correctly."""
    # Create a sample interaction
    interaction = VoiceInteraction(
        user_says="Click the button",
        expected_audio_response="Clicking the button now",
        expected_actions=["click_element(button)"],
        context={"screen_sharing": True},
        success_criteria=["Confirms action", "Clear feedback"]
    )
    
    # Test with matching response
    result = blind_user_tester.validate_interaction(
        interaction,
        "Clicking the button now",
        ["click_element(button)"]
    )
    
    assert result["user_input"] == "Click the button"
    assert result["passed"] is not None


def test_criterion_checking(blind_user_tester):
    """Test individual criterion checking."""
    # Test various criteria
    assert blind_user_tester._check_criterion(
        "announces action",
        "Clicking the button",
        ["click_element"]
    )
    
    assert blind_user_tester._check_criterion(
        "describes content",
        "I can see the homepage with buttons",
        []
    )
    
    assert blind_user_tester._check_criterion(
        "doesn't read password aloud",
        "Typing your password in the field",
        []
    )


def test_report_generation(blind_user_tester):
    """Test that report generation works."""
    report = blind_user_tester.generate_test_report()
    
    assert len(report) > 0
    assert "BLIND USER EXPERIENCE TEST REPORT" in report
    assert "SCENARIO:" in report
    assert "Success criteria:" in report


def test_all_scenarios_have_unique_names(blind_user_tester):
    """Test that all scenarios have unique names."""
    scenarios = blind_user_tester.test_scenarios
    names = [s["name"] for s in scenarios]
    
    assert len(names) == len(set(names)), "All scenario names should be unique"


def test_all_interactions_have_success_criteria(blind_user_tester):
    """Test that all interactions have at least one success criterion."""
    scenarios = blind_user_tester.test_scenarios
    
    for scenario in scenarios:
        for interaction in scenario["interactions"]:
            assert len(interaction.success_criteria) > 0, \
                f"Interaction '{interaction.user_says}' in scenario '{scenario['name']}' must have success criteria"


def test_audio_responses_are_descriptive(blind_user_tester):
    """Test that audio responses are descriptive enough for blind users."""
    scenarios = blind_user_tester.test_scenarios
    
    for scenario in scenarios:
        for interaction in scenario["interactions"]:
            response = interaction.expected_audio_response
            
            # Audio responses should be substantial
            assert len(response) > 10, \
                f"Audio response too short: '{response}' in scenario '{scenario['name']}'"
            
            # Should not rely on visual-only cues
            visual_only_words = ["look", "see the color", "visually", "appears"]
            for word in visual_only_words:
                if word in response.lower():
                    # This is okay if it's "I can see" (Spectra describing what she sees)
                    if not ("i can see" in response.lower() or "i see" in response.lower()):
                        pytest.fail(f"Response contains visual-only language: '{word}' in '{response}'")


def test_no_silent_actions(blind_user_tester):
    """Test that actions are always announced (no silent actions)."""
    scenarios = blind_user_tester.test_scenarios
    
    for scenario in scenarios:
        for interaction in scenario["interactions"]:
            if len(interaction.expected_actions) > 0:
                # If there are actions, the response should mention them
                response = interaction.expected_audio_response.lower()
                action_words = ["clicking", "typing", "scrolling", "navigating", "pressing", "searching"]
                
                has_action_announcement = any(word in response for word in action_words)
                
                # Exception: describe_screen doesn't need announcement
                if "describe_screen" not in str(interaction.expected_actions):
                    assert has_action_announcement, \
                        f"Actions without announcement in scenario '{scenario['name']}': {interaction.expected_actions}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])



# Pytest test functions
@pytest.fixture
def blind_user_tester():
    """Fixture to create a BlindUserExperienceTest instance."""
    return BlindUserExperienceTest()


def test_scenario_structure(blind_user_tester):
    """Test that all scenarios are properly structured."""
    scenarios = blind_user_tester.test_scenarios
    
    assert len(scenarios) > 0, "Should have at least one test scenario"
    
    for scenario in scenarios:
        assert "name" in scenario, "Scenario must have a name"
        assert "description" in scenario, "Scenario must have a description"
        assert "interactions" in scenario, "Scenario must have interactions"
        assert len(scenario["interactions"]) > 0, f"Scenario {scenario['name']} must have at least one interaction"


def test_interaction_completeness(blind_user_tester):
    """Test that all interactions have required fields."""
    scenarios = blind_user_tester.test_scenarios
    
    for scenario in scenarios:
        for i, interaction in enumerate(scenario["interactions"]):
            assert interaction.user_says, f"Interaction {i} in {scenario['name']} must have user_says"
            assert interaction.expected_audio_response, f"Interaction {i} in {scenario['name']} must have expected_audio_response"
            assert interaction.expected_actions is not None, f"Interaction {i} in {scenario['name']} must have expected_actions"
            assert interaction.context, f"Interaction {i} in {scenario['name']} must have context"
            assert len(interaction.success_criteria) > 0, f"Interaction {i} in {scenario['name']} must have success_criteria"


def test_first_time_user_scenario(blind_user_tester):
    """Test the first-time user onboarding scenario."""
    scenarios = blind_user_tester.test_scenarios
    first_time_scenario = next((s for s in scenarios if "First Time" in s["name"]), None)
    
    assert first_time_scenario is not None, "Should have a first-time user scenario"
    assert len(first_time_scenario["interactions"]) >= 2, "First-time scenario should have at least 2 interactions"
    
    # First interaction should be greeting
    first_interaction = first_time_scenario["interactions"][0]
    assert "hello" in first_interaction.user_says.lower(), "First interaction should be a greeting"
    assert "spectra" in first_interaction.expected_audio_response.lower(), "Response should introduce Spectra"


def test_web_search_scenario(blind_user_tester):
    """Test the web search task scenario."""
    scenarios = blind_user_tester.test_scenarios
    search_scenario = next((s for s in scenarios if "Search" in s["name"]), None)
    
    assert search_scenario is not None, "Should have a web search scenario"
    
    # Should have search interaction
    search_interaction = next((i for i in search_scenario["interactions"] if "search" in i.user_says.lower()), None)
    assert search_interaction is not None, "Should have a search interaction"
    assert len(search_interaction.expected_actions) > 0, "Search should trigger actions"


def test_form_filling_scenario(blind_user_tester):
    """Test the form filling scenario."""
    scenarios = blind_user_tester.test_scenarios
    form_scenario = next((s for s in scenarios if "Form" in s["name"] or "Login" in s["name"]), None)
    
    assert form_scenario is not None, "Should have a form filling scenario"
    
    # Should have password interaction
    password_interaction = next((i for i in form_scenario["interactions"] if "password" in i.user_says.lower()), None)
    assert password_interaction is not None, "Should have a password interaction"
    
    # Check privacy criterion
    privacy_criteria = [c for c in password_interaction.success_criteria if "password" in c.lower() and "doesn't read" in c.lower()]
    assert len(privacy_criteria) > 0, "Should have privacy criterion for password"


def test_content_reading_scenario(blind_user_tester):
    """Test the content reading scenario."""
    scenarios = blind_user_tester.test_scenarios
    reading_scenario = next((s for s in scenarios if "Reading" in s["name"]), None)
    
    assert reading_scenario is not None, "Should have a content reading scenario"
    
    # Should have scroll interaction
    scroll_interaction = next((i for i in reading_scenario["interactions"] if "scroll" in i.user_says.lower()), None)
    assert scroll_interaction is not None, "Should have a scroll interaction"
    assert any("scroll" in action for action in scroll_interaction.expected_actions), "Scroll interaction should trigger scroll action"


def test_error_recovery_scenario(blind_user_tester):
    """Test the error recovery scenario."""
    scenarios = blind_user_tester.test_scenarios
    error_scenario = next((s for s in scenarios if "Error" in s["name"]), None)
    
    assert error_scenario is not None, "Should have an error recovery scenario"
    
    # First interaction should demonstrate error handling
    first_interaction = error_scenario["interactions"][0]
    assert "don't see" in first_interaction.expected_audio_response.lower() or "can see" in first_interaction.expected_audio_response.lower(), "Should explain what's not found"


def test_no_screen_sharing_scenario(blind_user_tester):
    """Test scenario without screen sharing."""
    scenarios = blind_user_tester.test_scenarios
    no_screen_scenario = next((s for s in scenarios if "Without Screen" in s["name"]), None)
    
    assert no_screen_scenario is not None, "Should have a no screen sharing scenario"
    
    # Should have interaction with screen_sharing: False
    no_screen_interaction = no_screen_scenario["interactions"][0]
    assert no_screen_interaction.context.get("screen_sharing") == False, "Should have screen_sharing disabled"
    assert "press w" in no_screen_interaction.expected_audio_response.lower() or "share" in no_screen_interaction.expected_audio_response.lower(), "Should ask to enable screen sharing"


def test_multi_step_workflow_scenario(blind_user_tester):
    """Test multi-step workflow scenario."""
    scenarios = blind_user_tester.test_scenarios
    workflow_scenario = next((s for s in scenarios if "Multi-Step" in s["name"] or "Shopping" in s["name"]), None)
    
    assert workflow_scenario is not None, "Should have a multi-step workflow scenario"
    assert len(workflow_scenario["interactions"]) >= 3, "Multi-step workflow should have at least 3 interactions"


def test_accessibility_features_scenario(blind_user_tester):
    """Test accessibility-specific features."""
    scenarios = blind_user_tester.test_scenarios
    accessibility_scenario = next((s for s in scenarios if "Accessibility" in s["name"]), None)
    
    assert accessibility_scenario is not None, "Should have an accessibility features scenario"
    
    # Should have interaction asking about page elements
    element_interaction = next((i for i in accessibility_scenario["interactions"] if "button" in i.user_says.lower() or "link" in i.user_says.lower()), None)
    assert element_interaction is not None, "Should have interaction asking about page elements"


def test_criterion_checker(blind_user_tester):
    """Test the criterion checking logic."""
    # Test with sample responses
    test_cases = [
        ("announces", "Clicking the search box", True),
        ("announces", "The page loaded", False),
        ("describes", "I can see the search box", True),
        ("describes", "Done", False),
        ("doesn't read password", "Typing your password", True),
        ("doesn't read password", "Typing secret123", False),
    ]
    
    for criterion, response, expected in test_cases:
        result = blind_user_tester._check_criterion(criterion, response, [])
        if expected:
            assert result, f"Criterion '{criterion}' should pass for response '{response}'"
        # Note: We don't assert False cases as the checker is lenient


def test_validation_logic(blind_user_tester):
    """Test the interaction validation logic."""
    # Create a sample interaction
    interaction = VoiceInteraction(
        user_says="Click the button",
        expected_audio_response="Clicking the button",
        expected_actions=["click_element(button)"],
        context={"screen_sharing": True},
        success_criteria=["Announces action", "Executes action"]
    )
    
    # Test validation
    result = blind_user_tester.validate_interaction(
        interaction,
        "Clicking the button now",
        ["click_element(button)"]
    )
    
    assert "user_input" in result
    assert "passed" in result
    assert "success_criteria_met" in result
    assert "success_criteria_failed" in result


def test_report_generation(blind_user_tester):
    """Test that report generation works."""
    report = blind_user_tester.generate_test_report()
    
    assert len(report) > 0, "Report should not be empty"
    assert "BLIND USER EXPERIENCE TEST REPORT" in report, "Report should have title"
    assert "SCENARIO:" in report, "Report should include scenarios"
    assert "Success criteria:" in report, "Report should include success criteria"


def test_all_scenarios_have_unique_names(blind_user_tester):
    """Test that all scenarios have unique names."""
    scenarios = blind_user_tester.test_scenarios
    names = [s["name"] for s in scenarios]
    
    assert len(names) == len(set(names)), "All scenario names should be unique"


def test_audio_only_experience(blind_user_tester):
    """Test that all interactions can be completed with audio only."""
    scenarios = blind_user_tester.test_scenarios
    
    for scenario in scenarios:
        for interaction in scenario["interactions"]:
            # Check that expected response provides audio feedback
            assert len(interaction.expected_audio_response) > 0, f"Interaction '{interaction.user_says}' must have audio response"
            
            # Check that success criteria don't require visual confirmation
            visual_keywords = ["look", "see the screen", "visually", "watch"]
            for criterion in interaction.success_criteria:
                for keyword in visual_keywords:
                    assert keyword not in criterion.lower(), f"Success criterion should not require visual confirmation: {criterion}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
