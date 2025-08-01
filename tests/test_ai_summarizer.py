"""Tests for AI summarization service."""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from error_collector_mcp.services.ai_summarizer import AISummarizer, RateLimiter, SummarizationRequest
from error_collector_mcp.models import BaseError, BrowserError, TerminalError, ErrorSummary, ErrorSource, ErrorSeverity, ErrorCategory
from error_collector_mcp.config import OpenRouterConfig


class TestRateLimiter:
    """Test RateLimiter functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter with low limits for testing."""
        return RateLimiter(max_requests_per_minute=3)
    
    @pytest.mark.asyncio
    async def test_acquire_within_limit(self, rate_limiter):
        """Test acquiring requests within the rate limit."""
        # Should be able to make requests up to the limit
        for i in range(3):
            result = await rate_limiter.acquire()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_acquire_exceeds_limit(self, rate_limiter):
        """Test acquiring requests that exceed the rate limit."""
        # Fill up the limit
        for i in range(3):
            await rate_limiter.acquire()
        
        # Next request should be rate limited
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await rate_limiter.acquire()
            assert result is False
            mock_sleep.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_backoff_mechanism(self, rate_limiter):
        """Test backoff mechanism."""
        # Set backoff
        rate_limiter.set_backoff(1.0)
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await rate_limiter.acquire()
            assert result is False
            mock_sleep.assert_called_once()
        
        # Reset backoff
        rate_limiter.reset_backoff()
        result = await rate_limiter.acquire()
        assert result is True


class TestAISummarizer:
    """Test AISummarizer functionality."""
    
    @pytest.fixture
    def openrouter_config(self):
        """Create OpenRouter configuration for testing."""
        return OpenRouterConfig(
            api_key="test-api-key",
            model="meta-llama/llama-3.1-8b-instruct:free",
            max_tokens=1000,
            temperature=0.7,
            timeout=30
        )
    
    @pytest.fixture
    def ai_summarizer(self, openrouter_config):
        """Create AI summarizer instance."""
        return AISummarizer(openrouter_config)
    
    @pytest.fixture
    def sample_errors(self):
        """Create sample errors for testing."""
        return [
            BrowserError(
                message="TypeError: Cannot read property 'foo' of null",
                url="https://example.com/page.html",
                error_type="TypeError",
                line_number=42
            ),
            TerminalError(
                message="Command failed with exit code 1",
                command="npm install",
                exit_code=1,
                stderr_output="Permission denied"
            ),
            BaseError(
                message="Generic error occurred",
                source=ErrorSource.UNKNOWN,
                category=ErrorCategory.RUNTIME
            )
        ]
    
    @pytest.mark.asyncio
    async def test_start_stop_service(self, ai_summarizer):
        """Test starting and stopping the AI summarizer service."""
        assert not ai_summarizer._is_running
        
        await ai_summarizer.start()
        assert ai_summarizer._is_running
        assert ai_summarizer._processing_task is not None
        
        await ai_summarizer.stop()
        assert not ai_summarizer._is_running
    
    @pytest.mark.asyncio
    async def test_summarize_single_error(self, ai_summarizer, sample_errors):
        """Test summarizing a single error."""
        # Mock the OpenAI client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "root_cause": "Null pointer access",
            "impact_assessment": "Application crash",
            "suggested_solutions": ["Add null check", "Use optional chaining"],
            "confidence_score": 0.9
        })
        
        with patch.object(ai_summarizer.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            # Start the service
            await ai_summarizer.start()
            
            try:
                # Summarize error
                summary = await ai_summarizer.summarize_error(sample_errors[0])
                
                assert isinstance(summary, ErrorSummary)
                assert summary.root_cause == "Null pointer access"
                assert summary.impact_assessment == "Application crash"
                assert len(summary.suggested_solutions) == 2
                assert summary.confidence_score == 0.9
                assert len(summary.error_ids) == 1
                
            finally:
                await ai_summarizer.stop()
    
    @pytest.mark.asyncio
    async def test_summarize_error_group(self, ai_summarizer, sample_errors):
        """Test summarizing a group of errors."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "root_cause": "Multiple system failures",
            "impact_assessment": "System instability",
            "suggested_solutions": ["Fix null checks", "Improve error handling", "Update dependencies"],
            "confidence_score": 0.8
        })
        
        with patch.object(ai_summarizer.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            await ai_summarizer.start()
            
            try:
                # Summarize multiple errors
                summary = await ai_summarizer.summarize_error_group(sample_errors)
                
                assert isinstance(summary, ErrorSummary)
                assert summary.root_cause == "Multiple system failures"
                assert len(summary.error_ids) == len(sample_errors)
                assert len(summary.suggested_solutions) == 3
                
            finally:
                await ai_summarizer.stop()
    
    @pytest.mark.asyncio
    async def test_group_similar_errors(self, ai_summarizer):
        """Test grouping similar errors."""
        # Create similar errors
        similar_errors = [
            BrowserError(
                message="TypeError: Cannot read property 'foo' of null",
                url="https://example.com/page1.html",
                error_type="TypeError"
            ),
            BrowserError(
                message="TypeError: Cannot read property 'bar' of null",
                url="https://example.com/page2.html",
                error_type="TypeError"
            ),
            TerminalError(
                message="Command failed",
                command="npm install",
                exit_code=1
            )
        ]
        
        groups = await ai_summarizer.group_similar_errors(similar_errors)
        
        # Should group the two similar browser errors together
        assert len(groups) == 2
        
        # Find the browser error group
        browser_group = None
        terminal_group = None
        
        for group in groups:
            if isinstance(group[0], BrowserError):
                browser_group = group
            elif isinstance(group[0], TerminalError):
                terminal_group = group
        
        assert browser_group is not None
        assert terminal_group is not None
        assert len(browser_group) == 2
        assert len(terminal_group) == 1
    
    def test_error_similarity_detection(self, ai_summarizer):
        """Test error similarity detection."""
        # Similar browser errors
        error1 = BrowserError(
            message="TypeError: Cannot read property 'foo' of null",
            url="https://example.com/page.html",
            error_type="TypeError"
        )
        error2 = BrowserError(
            message="TypeError: Cannot read property 'bar' of null",
            url="https://example.com/page.html",
            error_type="TypeError"
        )
        
        # Should be similar
        assert ai_summarizer._are_errors_similar(error1, error2)
        
        # Different error types should not be similar
        error3 = BrowserError(
            message="ReferenceError: x is not defined",
            url="https://example.com/page.html",
            error_type="ReferenceError"
        )
        
        assert not ai_summarizer._are_errors_similar(error1, error3)
        
        # Different sources should not be similar
        error4 = TerminalError(
            message="TypeError: Cannot read property 'foo' of null",
            command="node script.js",
            exit_code=1
        )
        
        assert not ai_summarizer._are_errors_similar(error1, error4)
    
    def test_message_similarity_calculation(self, ai_summarizer):
        """Test message similarity calculation."""
        # Identical messages
        similarity = ai_summarizer._calculate_message_similarity(
            "TypeError: Cannot read property 'foo' of null",
            "TypeError: Cannot read property 'foo' of null"
        )
        assert similarity == 1.0
        
        # Similar messages
        similarity = ai_summarizer._calculate_message_similarity(
            "TypeError: Cannot read property 'foo' of null",
            "TypeError: Cannot read property 'bar' of null"
        )
        assert 0.5 < similarity < 1.0
        
        # Completely different messages
        similarity = ai_summarizer._calculate_message_similarity(
            "TypeError: Cannot read property 'foo' of null",
            "Network connection failed"
        )
        assert similarity < 0.5
        
        # Empty messages
        similarity = ai_summarizer._calculate_message_similarity("", "test")
        assert similarity == 0.0
    
    def test_priority_calculation(self, ai_summarizer, sample_errors):
        """Test priority calculation for summarization requests."""
        # Single error
        priority1 = ai_summarizer._calculate_priority([sample_errors[0]])
        
        # Multiple errors
        priority2 = ai_summarizer._calculate_priority(sample_errors)
        
        # More errors should have higher priority
        assert priority2 > priority1
        
        # Critical errors should have higher priority
        critical_error = BaseError(
            message="Critical system failure",
            severity=ErrorSeverity.CRITICAL
        )
        priority3 = ai_summarizer._calculate_priority([critical_error])
        priority4 = ai_summarizer._calculate_priority([sample_errors[0]])
        
        assert priority3 > priority4
    
    def test_request_id_generation(self, ai_summarizer, sample_errors):
        """Test request ID generation."""
        # Same errors should generate same ID
        id1 = ai_summarizer._generate_request_id(sample_errors)
        id2 = ai_summarizer._generate_request_id(sample_errors)
        assert id1 == id2
        
        # Different errors should generate different IDs
        id3 = ai_summarizer._generate_request_id([sample_errors[0]])
        assert id1 != id3
        
        # Order shouldn't matter
        reversed_errors = list(reversed(sample_errors))
        id4 = ai_summarizer._generate_request_id(reversed_errors)
        assert id1 == id4
    
    def test_prompt_creation(self, ai_summarizer, sample_errors):
        """Test prompt creation for different error types."""
        # Single browser error
        browser_prompt = ai_summarizer._create_summarization_prompt([sample_errors[0]])
        assert "Error Type: browser" in browser_prompt
        assert "URL:" in browser_prompt
        assert "Error Type: TypeError" in browser_prompt
        
        # Single terminal error
        terminal_prompt = ai_summarizer._create_summarization_prompt([sample_errors[1]])
        assert "Error Type: terminal" in terminal_prompt
        assert "Command:" in terminal_prompt
        assert "Exit Code:" in terminal_prompt
        
        # Multiple errors
        multi_prompt = ai_summarizer._create_summarization_prompt(sample_errors)
        assert f"these {len(sample_errors)} related errors" in multi_prompt
        assert "Error 1:" in multi_prompt
        assert "Error 2:" in multi_prompt
    
    def test_response_parsing(self, ai_summarizer):
        """Test parsing of AI responses."""
        # Valid JSON response
        json_response = json.dumps({
            "root_cause": "Null pointer access",
            "impact_assessment": "Application crash",
            "suggested_solutions": ["Add null check", "Use optional chaining"],
            "confidence_score": 0.9
        })
        
        parsed = ai_summarizer._parse_summary_response(json_response)
        assert parsed["root_cause"] == "Null pointer access"
        assert len(parsed["suggested_solutions"]) == 2
        assert parsed["confidence_score"] == 0.9
        
        # Text response (fallback)
        text_response = """
        Root Cause: The error occurs due to null pointer access
        Impact: This causes the application to crash
        Solutions:
        - Add null checks before property access
        - Use optional chaining operator
        - Implement proper error handling
        """
        
        parsed = ai_summarizer._parse_summary_response(text_response)
        assert "null pointer access" in parsed["root_cause"].lower()
        assert len(parsed["suggested_solutions"]) >= 1
    
    def test_solution_parsing(self, ai_summarizer):
        """Test parsing of solution responses."""
        solution_response = """
        Here are additional solutions:
        - Implement input validation
        - Add comprehensive error logging
        - Use defensive programming techniques
        - Set up automated testing
        - Review code for similar patterns
        """
        
        solutions = ai_summarizer._parse_solutions_from_response(solution_response)
        assert len(solutions) == 5
        assert "Implement input validation" in solutions
        assert "Add comprehensive error logging" in solutions
    
    @pytest.mark.asyncio
    async def test_get_solution_suggestions(self, ai_summarizer):
        """Test getting additional solution suggestions."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """
        - Implement comprehensive input validation
        - Add error boundary components
        - Use TypeScript for better type safety
        - Set up automated testing
        """
        
        with patch.object(ai_summarizer.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            # Create a sample summary
            summary = ErrorSummary(
                error_ids=["test-error"],
                root_cause="Null pointer access",
                impact_assessment="Application crash",
                suggested_solutions=["Add null check"],
                confidence_score=0.8
            )
            
            solutions = await ai_summarizer.get_solution_suggestions(summary)
            
            assert len(solutions) == 4
            assert "Implement comprehensive input validation" in solutions
            assert "Add error boundary components" in solutions
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, ai_summarizer, sample_errors):
        """Test handling of API errors."""
        # Mock API failure
        with patch.object(ai_summarizer.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API Error")
            
            await ai_summarizer.start()
            
            try:
                # Should handle the error gracefully
                with pytest.raises(Exception):
                    await ai_summarizer.summarize_error(sample_errors[0])
                
                # Rate limiter should be in backoff state
                assert ai_summarizer.rate_limiter.backoff_until is not None
                
            finally:
                await ai_summarizer.stop()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, ai_summarizer, sample_errors):
        """Test handling of request timeouts."""
        # Mock very slow API response
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(2)  # Longer than our test timeout
            return MagicMock()
        
        with patch.object(ai_summarizer.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = slow_response
            
            await ai_summarizer.start()
            
            try:
                # Reduce timeout for testing
                original_timeout = ai_summarizer.config.timeout
                ai_summarizer.config.timeout = 0.1
                
                with pytest.raises(Exception):  # Should timeout
                    await ai_summarizer.summarize_error(sample_errors[0])
                
                # Restore timeout
                ai_summarizer.config.timeout = original_timeout
                
            finally:
                await ai_summarizer.stop()
    
    def test_summarization_request_creation(self):
        """Test SummarizationRequest creation."""
        errors = [BaseError(message="Test error")]
        request = SummarizationRequest(
            errors=errors,
            request_id="test-request",
            priority=5
        )
        
        assert request.errors == errors
        assert request.request_id == "test-request"
        assert request.priority == 5
        assert isinstance(request.created_at, datetime)