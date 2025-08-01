"""Data models for error collection and summarization."""

from .base_error import BaseError, ErrorSource, ErrorSeverity, ErrorCategory
from .browser_error import BrowserError
from .terminal_error import TerminalError
from .error_summary import ErrorSummary

__all__ = [
    "BaseError",
    "ErrorSource", 
    "ErrorSeverity",
    "ErrorCategory",
    "BrowserError",
    "TerminalError", 
    "ErrorSummary"
]