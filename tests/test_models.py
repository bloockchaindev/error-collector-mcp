"""Tests for data models."""

import pytest
from datetime import datetime
from error_collector_mcp.models import (
    BaseError, BrowserError, TerminalError, ErrorSummary,
    ErrorSource, ErrorSeverity, ErrorCategory
)


class TestBaseError:
    """Test BaseError model."""
    
    def test_create_basic_error(self):
        """Test creating a basic error."""
        error = BaseError(message="Test error")
        assert error.message == "Test error"
        assert error.source == ErrorSource.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert isinstance(error.timestamp, datetime)
        assert len(error.id) > 0
    
    def test_empty_message_raises_error(self):
        """Test that empty message raises ValueError."""
        with pytest.raises(ValueError, match="Error message cannot be empty"):
            BaseError(message="")
    
    def test_auto_categorization(self):
        """Test automatic error categorization."""
        # Syntax error
        syntax_error = BaseError(message="SyntaxError: Unexpected token")
        assert syntax_error.category == ErrorCategory.SYNTAX
        
        # Network error
        network_error = BaseError(message="Network request failed with 404")
        assert network_error.category == ErrorCategory.NETWORK
        
        # Permission error
        perm_error = BaseError(message="Access denied to resource")
        assert perm_error.category == ErrorCategory.PERMISSION
        
        # Runtime error
        runtime_error = BaseError(message="TypeError: Cannot read property")
        assert runtime_error.category == ErrorCategory.RUNTIME
    
    def test_auto_severity_determination(self):
        """Test automatic severity determination."""
        # Critical error
        critical_error = BaseError(message="Fatal error: System crash")
        assert critical_error.severity == ErrorSeverity.CRITICAL
        
        # High severity error
        high_error = BaseError(message="Error: Failed to execute")
        assert high_error.severity == ErrorSeverity.HIGH
        
        # Low severity warning
        low_error = BaseError(message="Warning: Deprecated function used")
        assert low_error.severity == ErrorSeverity.LOW
    
    def test_to_dict_conversion(self):
        """Test converting error to dictionary."""
        error = BaseError(
            message="Test error",
            source=ErrorSource.BROWSER,
            severity=ErrorSeverity.HIGH
        )
        error_dict = error.to_dict()
        
        assert error_dict["message"] == "Test error"
        assert error_dict["source"] == "browser"
        assert error_dict["severity"] == "high"
        assert "timestamp" in error_dict
        assert "id" in error_dict
    
    def test_from_dict_creation(self):
        """Test creating error from dictionary."""
        error_data = {
            "id": "test-id",
            "timestamp": "2024-01-01T12:00:00",
            "source": "browser",
            "message": "Test error",
            "stack_trace": None,
            "context": {},
            "severity": "high",
            "category": "runtime"
        }
        
        error = BaseError.from_dict(error_data)
        assert error.id == "test-id"
        assert error.message == "Test error"
        assert error.source == ErrorSource.BROWSER
        assert error.severity == ErrorSeverity.HIGH


class TestBrowserError:
    """Test BrowserError model."""
    
    def test_create_browser_error(self):
        """Test creating a browser error."""
        error = BrowserError(
            message="TypeError: Cannot read property 'foo' of null",
            url="https://example.com/page.html",
            line_number=42,
            column_number=15
        )
        
        assert error.source == ErrorSource.BROWSER
        assert error.url == "https://example.com/page.html"
        assert error.line_number == 42
        assert error.column_number == 15
        assert error.error_type == "TypeError"
    
    def test_error_type_extraction(self):
        """Test automatic error type extraction."""
        # Standard JavaScript error
        error1 = BrowserError(message="ReferenceError: x is not defined")
        assert error1.error_type == "ReferenceError"
        
        # Uncaught error
        error2 = BrowserError(message="Uncaught SyntaxError: Unexpected token")
        assert error2.error_type == "SyntaxError"
        
        # Generic error
        error3 = BrowserError(message="Something went wrong")
        assert error3.error_type == "Error"
    
    def test_location_string(self):
        """Test location string formatting."""
        error = BrowserError(
            message="Test error",
            url="https://example.com/script.js",
            line_number=10,
            column_number=5
        )
        
        location = error.get_location_string()
        assert "https://example.com/script.js" in location
        assert "line 10, column 5" in location
    
    def test_context_population(self):
        """Test that browser-specific context is populated."""
        error = BrowserError(
            message="Test error",
            url="https://example.com",
            user_agent="Mozilla/5.0...",
            page_title="Test Page"
        )
        
        assert error.context["url"] == "https://example.com"
        assert error.context["user_agent"] == "Mozilla/5.0..."
        assert error.context["page_title"] == "Test Page"


class TestTerminalError:
    """Test TerminalError model."""
    
    def test_create_terminal_error(self):
        """Test creating a terminal error."""
        error = TerminalError(
            command="gcc -o test test.c",
            exit_code=1,
            stderr_output="test.c:5:1: error: syntax error"
        )
        
        assert error.source == ErrorSource.TERMINAL
        assert error.command == "gcc -o test test.c"
        assert error.exit_code == 1
        assert "syntax error" in error.message
    
    def test_message_from_stderr(self):
        """Test using stderr as message when message is empty."""
        error = TerminalError(
            command="test command",
            stderr_output="Error: Command failed"
        )
        
        assert error.message == "Error: Command failed"
    
    def test_compilation_error_detection(self):
        """Test compilation error detection."""
        # GCC compilation error
        gcc_error = TerminalError(
            command="gcc -o test test.c",
            stderr_output="syntax error"
        )
        assert gcc_error.is_compilation_error()
        assert gcc_error.category == ErrorCategory.SYNTAX
        
        # TypeScript compilation error
        tsc_error = TerminalError(
            command="tsc src/main.ts",
            stderr_output="Type error"
        )
        assert tsc_error.is_compilation_error()
    
    def test_command_categorization(self):
        """Test command-based error categorization."""
        # Git permission error
        git_error = TerminalError(
            command="git push origin main",
            stderr_output="Permission denied (publickey)"
        )
        assert git_error.category == ErrorCategory.PERMISSION
        
        # NPM network error
        npm_error = TerminalError(
            command="npm install package",
            stderr_output="Network timeout"
        )
        assert npm_error.category == ErrorCategory.NETWORK
        
        # File system error
        fs_error = TerminalError(
            command="ls /nonexistent",
            stderr_output="No such file or directory"
        )
        assert fs_error.category == ErrorCategory.RESOURCE
    
    def test_command_summary(self):
        """Test command summary generation."""
        # Short command
        short_error = TerminalError(command="ls -la")
        assert short_error.get_command_summary() == "ls -la"
        
        # Long command (should be truncated)
        long_command = "very " * 30 + "long command"
        long_error = TerminalError(command=long_command)
        summary = long_error.get_command_summary()
        assert len(summary) <= 100
        assert summary.endswith("...")


class TestErrorSummary:
    """Test ErrorSummary model."""
    
    def test_create_error_summary(self):
        """Test creating an error summary."""
        summary = ErrorSummary(
            error_ids=["error1", "error2"],
            root_cause="Null pointer dereference",
            impact_assessment="Application crash",
            suggested_solutions=["Add null check", "Use optional chaining"],
            confidence_score=0.9
        )
        
        assert len(summary.error_ids) == 2
        assert summary.root_cause == "Null pointer dereference"
        assert summary.confidence_score == 0.9
        assert len(summary.suggested_solutions) == 2
    
    def test_empty_error_ids_raises_error(self):
        """Test that empty error_ids raises ValueError."""
        with pytest.raises(ValueError, match="must reference at least one error"):
            ErrorSummary(
                error_ids=[],
                root_cause="Test cause"
            )
    
    def test_empty_root_cause_raises_error(self):
        """Test that empty root cause raises ValueError."""
        with pytest.raises(ValueError, match="Root cause cannot be empty"):
            ErrorSummary(
                error_ids=["error1"],
                root_cause=""
            )
    
    def test_invalid_confidence_score_raises_error(self):
        """Test that invalid confidence score raises ValueError."""
        with pytest.raises(ValueError, match="Confidence score must be between"):
            ErrorSummary(
                error_ids=["error1"],
                root_cause="Test cause",
                confidence_score=1.5
            )
    
    def test_add_methods(self):
        """Test methods for adding data to summary."""
        summary = ErrorSummary(
            error_ids=["error1"],
            root_cause="Test cause"
        )
        
        # Add error ID
        summary.add_error_id("error2")
        assert "error2" in summary.error_ids
        
        # Add duplicate error ID (should not duplicate)
        summary.add_error_id("error1")
        assert summary.error_ids.count("error1") == 1
        
        # Add suggested solution
        summary.add_suggested_solution("Fix the bug")
        assert "Fix the bug" in summary.suggested_solutions
        
        # Add related error
        summary.add_related_error("related1")
        assert "related1" in summary.related_errors
    
    def test_confidence_and_priority_scoring(self):
        """Test confidence and priority scoring methods."""
        # High confidence summary
        high_conf_summary = ErrorSummary(
            error_ids=["error1"],
            root_cause="Test cause",
            confidence_score=0.9
        )
        assert high_conf_summary.is_high_confidence()
        
        # Low confidence summary
        low_conf_summary = ErrorSummary(
            error_ids=["error1"],
            root_cause="Test cause",
            confidence_score=0.5
        )
        assert not low_conf_summary.is_high_confidence()
        
        # Priority score should be higher for more errors and higher confidence
        multi_error_summary = ErrorSummary(
            error_ids=["error1", "error2", "error3"],
            root_cause="Test cause",
            confidence_score=0.9
        )
        single_error_summary = ErrorSummary(
            error_ids=["error1"],
            root_cause="Test cause",
            confidence_score=0.5
        )
        
        assert multi_error_summary.get_priority_score() > single_error_summary.get_priority_score()
    
    def test_format_for_display(self):
        """Test display formatting."""
        summary = ErrorSummary(
            error_ids=["error1", "error2"],
            root_cause="Null pointer dereference",
            impact_assessment="Application may crash",
            suggested_solutions=["Add null check", "Use defensive programming"],
            confidence_score=0.85
        )
        
        display_text = summary.format_for_display()
        assert "Null pointer dereference" in display_text
        assert "Application may crash" in display_text
        assert "Add null check" in display_text
        assert "85.0%" in display_text