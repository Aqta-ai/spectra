"""
Unit tests for LocationContextHandler

Tests the location query detection, screen content analysis, and response formatting
for the Spectra accessibility enhancement.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from app.location_context_handler import LocationContextHandler, LocationInfo


class TestLocationContextHandler:
    """Test suite for LocationContextHandler functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.handler = LocationContextHandler()
    
    def test_is_location_query_basic_patterns(self):
        """Test detection of basic location query patterns."""
        # Positive cases
        location_queries = [
            "where am i",
            "Where am I?",
            "WHERE AM I",
            "what site am i on",
            "what website is this",
            "what app am i in",
            "what page is this",
            "where are we",
            "what application is this",
            "what program is this",
            "what browser tab is this"
        ]
        
        for query in location_queries:
            assert self.handler.is_location_query(query), f"Failed to detect location query: '{query}'"
    
    def test_is_location_query_negative_cases(self):
        """Test that non-location queries are not detected as location queries."""
        non_location_queries = [
            "what time is it",
            "how are you",
            "read the screen",
            "click the button",
            "scroll down",
            "what does this say",
            "help me navigate",
            "where is the nearest store",  # Physical location
            "where can I find",
            ""
        ]
        
        for query in non_location_queries:
            assert not self.handler.is_location_query(query), f"Incorrectly detected location query: '{query}'"
    
    def test_is_location_query_edge_cases(self):
        """Test edge cases for location query detection."""
        # Empty and None cases
        assert not self.handler.is_location_query("")
        assert not self.handler.is_location_query(None)
        
        # Partial matches that shouldn't trigger
        assert not self.handler.is_location_query("I am where I want to be")
        assert not self.handler.is_location_query("somewhere am I going")
    
    def test_extract_location_info_google(self):
        """Test location extraction for Google."""
        description = "Google search homepage with search bar and Google logo visible"
        location_info = self.handler.extract_location_info(description)
        
        assert location_info.site_name == "Google"
        assert location_info.confidence >= 0.7
        # Context should be determined from the description - "homepage" is valid
        assert location_info.context in ['search engine', 'homepage', 'search results']
    
    def test_extract_location_info_gmail(self):
        """Test location extraction for Gmail."""
        description = "Gmail inbox showing email list with compose button"
        location_info = self.handler.extract_location_info(description)
        
        assert location_info.site_name == "Gmail"
        assert location_info.confidence >= 0.7
    
    def test_extract_location_info_with_url(self):
        """Test location extraction when URL is present."""
        description = "Page showing https://github.com/user/repo with code repository"
        location_info = self.handler.extract_location_info(description)
        
        assert location_info.url == "https://github.com/user/repo"
        assert location_info.site_name == "GitHub"
        assert location_info.confidence >= 0.8
    
    def test_extract_location_info_application(self):
        """Test location extraction for desktop applications."""
        description = "Visual Studio Code editor with file explorer and code editing area"
        location_info = self.handler.extract_location_info(description)
        
        assert location_info.app_name == "Visual Studio Code"
        assert location_info.confidence >= 0.7
    
    def test_extract_location_info_page_title(self):
        """Test location extraction using page title."""
        description = "Page title: Welcome to Stack Overflow - Developer Community"
        location_info = self.handler.extract_location_info(description)
        
        assert location_info.page_title is not None
        assert "Stack Overflow" in location_info.page_title
        assert location_info.confidence >= 0.5
    
    def test_extract_location_info_empty_description(self):
        """Test location extraction with empty description."""
        location_info = self.handler.extract_location_info("")
        
        assert location_info.site_name is None
        assert location_info.url is None
        assert location_info.app_name is None
        assert location_info.confidence == 0.0
    
    def test_format_location_response_high_confidence(self):
        """Test response formatting for high-confidence location info."""
        location_info = LocationInfo(
            site_name="Google",
            context="search engine",
            confidence=0.9
        )
        
        response = self.handler.format_location_response(location_info)
        assert "You're on Google" in response
        assert "search engine" in response
    
    def test_format_location_response_with_url(self):
        """Test response formatting when URL is available."""
        location_info = LocationInfo(
            site_name="GitHub",
            url="https://github.com/user/repo",
            context="code repository",
            confidence=0.8
        )
        
        response = self.handler.format_location_response(location_info)
        assert "You're on GitHub" in response
        assert "code repository" in response
    
    def test_format_location_response_application(self):
        """Test response formatting for applications."""
        location_info = LocationInfo(
            app_name="Visual Studio Code",
            confidence=0.8
        )
        
        response = self.handler.format_location_response(location_info)
        assert "You're in Visual Studio Code" in response
    
    def test_format_location_response_medium_confidence(self):
        """Test response formatting for medium-confidence info."""
        location_info = LocationInfo(
            page_title="Welcome to Example Site",
            confidence=0.6
        )
        
        response = self.handler.format_location_response(location_info)
        assert "page titled" in response
        assert "Welcome to Example Site" in response
    
    def test_format_location_response_fallback(self):
        """Test fallback response when location cannot be determined."""
        location_info = LocationInfo(confidence=0.1)
        
        response = self.handler.format_location_response(location_info)
        assert "cannot determine the specific website or application" in response
    
    def test_format_location_response_with_fallback_description(self):
        """Test response formatting with fallback description."""
        location_info = LocationInfo(confidence=0.1)
        fallback_description = "This appears to be a shopping website with product listings and a shopping cart"
        
        response = self.handler.format_location_response(location_info, fallback_description)
        assert "shopping" in response.lower()
    
    def test_domain_from_url(self):
        """Test domain extraction from URLs."""
        test_cases = [
            ("https://www.google.com/search", "google.com"),
            ("http://github.com/user/repo", "github.com"),
            ("www.example.com/page", "example.com"),
            ("facebook.com", "facebook.com"),
            ("https://subdomain.example.com/path", "subdomain.example.com")
        ]
        
        for url, expected_domain in test_cases:
            domain = self.handler._domain_from_url(url)
            assert domain == expected_domain, f"Expected {expected_domain}, got {domain} for URL {url}"
    
    def test_extract_url_info(self):
        """Test URL extraction from descriptions."""
        test_cases = [
            ("Visit https://www.google.com for search", "https://www.google.com"),
            ("Go to github.com/user/repo", "github.com/user/repo"),
            ("Check out www.example.com/page", "www.example.com/page"),
            ("No URL in this text", None)
        ]
        
        for description, expected_url in test_cases:
            url = self.handler._extract_url_info(description)
            assert url == expected_url, f"Expected {expected_url}, got {url} for description '{description}'"
    
    def test_extract_basic_info(self):
        """Test basic information extraction."""
        test_cases = [
            ("This page shows search results for your query", "search results"),
            ("Welcome to our shopping portal", "a shopping page"),
            ("Latest news and updates", "a news page"),
            ("User login required", "a login page"),
            ("Dashboard overview", "a dashboard"),
            ("Random content without patterns", None)
        ]
        
        for description, expected_info in test_cases:
            info = self.handler._extract_basic_info(description)
            assert info == expected_info, f"Expected {expected_info}, got {info} for description '{description}'"
    
    @pytest.mark.asyncio
    async def test_handle_location_query_success(self):
        """Test successful handling of location query."""
        query = "where am i"
        screen_description = "Google search homepage with search bar visible"
        
        response = await self.handler.handle_location_query(query, screen_description)
        
        assert response is not None
        assert "Google" in response
        assert "You're on" in response
    
    @pytest.mark.asyncio
    async def test_handle_location_query_not_location(self):
        """Test handling of non-location query."""
        query = "what time is it"
        screen_description = "Some screen content"
        
        response = await self.handler.handle_location_query(query, screen_description)
        
        assert response is None
    
    @pytest.mark.asyncio
    async def test_handle_location_query_unknown_site(self):
        """Test handling of location query for unknown site."""
        query = "where am i"
        screen_description = "Some unknown website with various content"
        
        response = await self.handler.handle_location_query(query, screen_description)
        
        assert response is not None
        assert "cannot determine" in response
    
    def test_website_indicators_coverage(self):
        """Test that all major websites are covered in indicators."""
        expected_sites = [
            'google', 'gmail', 'youtube', 'facebook', 'twitter', 
            'linkedin', 'amazon', 'github', 'stackoverflow', 'wikipedia'
        ]
        
        for site in expected_sites:
            assert site in self.handler.website_indicators, f"Missing website indicator for {site}"
            assert 'patterns' in self.handler.website_indicators[site]
            assert 'name' in self.handler.website_indicators[site]
            assert len(self.handler.website_indicators[site]['patterns']) > 0
    
    def test_app_indicators_coverage(self):
        """Test that common applications are covered in indicators."""
        expected_apps = [
            'chrome', 'firefox', 'safari', 'edge', 'vscode',
            'word', 'excel', 'powerpoint', 'outlook', 'teams'
        ]
        
        for app in expected_apps:
            assert app in self.handler.app_indicators, f"Missing app indicator for {app}"
            assert 'patterns' in self.handler.app_indicators[app]
            assert 'name' in self.handler.app_indicators[app]
            assert len(self.handler.app_indicators[app]['patterns']) > 0
    
    def test_multiple_pattern_matching(self):
        """Test that multiple patterns can match and boost confidence."""
        description = "Google.com search engine with Google logo and search functionality"
        location_info = self.handler.extract_location_info(description)
        
        # Should have high confidence due to multiple pattern matches
        assert location_info.confidence >= 0.9
        assert location_info.site_name == "Google"
    
    def test_case_insensitive_matching(self):
        """Test that pattern matching is case insensitive."""
        descriptions = [
            "GOOGLE.COM SEARCH",
            "google.com search",
            "Google.com Search",
            "GoOgLe.CoM sEaRcH"
        ]
        
        for description in descriptions:
            location_info = self.handler.extract_location_info(description)
            assert location_info.site_name == "Google", f"Failed case insensitive match for: {description}"
    
    def test_context_determination(self):
        """Test context determination from available options."""
        # Test with search context
        contexts = ['search engine', 'homepage', 'search results']
        description_lower = "search results for your query"
        context = self.handler._determine_context(description_lower, contexts)
        assert context == 'search results'
        
        # Test with default context when no match
        contexts = ['email', 'inbox', 'compose']
        description_lower = "some other content"
        context = self.handler._determine_context(description_lower, contexts)
        assert context == 'email'  # First context as default
    
    def test_title_extraction_patterns(self):
        """Test various title extraction patterns."""
        test_cases = [
            ("title: Welcome to Example Site", "Welcome to Example Site"),
            ("page title: User Dashboard", "User Dashboard"),
            ("heading: Latest News", "Latest News"),
            ("Example Page - Site Name", "Example Page"),
            ("No title here", None)
        ]
        
        for description, expected_title in test_cases:
            title = self.handler._extract_title_info(description)
            assert title == expected_title, f"Expected {expected_title}, got {title} for '{description}'"


class TestLocationInfoDataclass:
    """Test the LocationInfo dataclass."""
    
    def test_location_info_defaults(self):
        """Test LocationInfo default values."""
        info = LocationInfo()
        
        assert info.site_name is None
        assert info.url is None
        assert info.app_name is None
        assert info.page_title is None
        assert info.context is None
        assert info.confidence == 0.0
    
    def test_location_info_with_values(self):
        """Test LocationInfo with provided values."""
        info = LocationInfo(
            site_name="Google",
            url="https://google.com",
            context="search engine",
            confidence=0.9
        )
        
        assert info.site_name == "Google"
        assert info.url == "https://google.com"
        assert info.context == "search engine"
        assert info.confidence == 0.9
        assert info.app_name is None  # Not provided
        assert info.page_title is None  # Not provided


if __name__ == "__main__":
    pytest.main([__file__])