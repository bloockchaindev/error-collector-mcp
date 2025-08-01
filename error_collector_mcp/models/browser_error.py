"""Browser-specific error model."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from .base_error import BaseError, ErrorSource


@dataclass
class BrowserError(BaseError):
    """Browser console error with additional browser-specific context."""
    
    url: str = ""
    user_agent: str = ""
    page_title: str = ""
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    error_type: str = ""
    
    def __post_init__(self):
        """Initialize browser error with proper source."""
        self.source = ErrorSource.BROWSER
        super().__post_init__()
        
        # Extract error type from message if not provided
        if not self.error_type and self.message:
            self.error_type = self._extract_error_type()
        
        # Add browser-specific context
        self.context.update({
            "url": self.url,
            "user_agent": self.user_agent,
            "page_title": self.page_title,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "error_type": self.error_type
        })
    
    def _extract_error_type(self) -> str:
        """Extract JavaScript error type from message."""
        message = self.message.strip()
        
        # Common JavaScript error types
        js_error_types = [
            "TypeError", "ReferenceError", "SyntaxError", "RangeError",
            "EvalError", "URIError", "InternalError", "Error"
        ]
        
        for error_type in js_error_types:
            if message.startswith(error_type):
                return error_type
        
        # Check for uncaught errors
        if "Uncaught" in message:
            parts = message.split(":")
            if len(parts) > 1:
                potential_type = parts[1].strip().split()[0]
                if potential_type in js_error_types:
                    return potential_type
        
        return "Error"
    
    def get_location_string(self) -> str:
        """Get formatted location string for the error."""
        location_parts = []
        
        if self.url:
            location_parts.append(self.url)
        
        if self.line_number is not None:
            if self.column_number is not None:
                location_parts.append(f"line {self.line_number}, column {self.column_number}")
            else:
                location_parts.append(f"line {self.line_number}")
        
        return " at ".join(location_parts) if location_parts else "unknown location"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert browser error to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "url": self.url,
            "user_agent": self.user_agent,
            "page_title": self.page_title,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "error_type": self.error_type,
            "location_string": self.get_location_string()
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrowserError":
        """Create browser error from dictionary representation."""
        base_error = super().from_dict(data)
        return cls(
            id=base_error.id,
            timestamp=base_error.timestamp,
            message=base_error.message,
            stack_trace=base_error.stack_trace,
            context=base_error.context,
            severity=base_error.severity,
            category=base_error.category,
            url=data.get("url", ""),
            user_agent=data.get("user_agent", ""),
            page_title=data.get("page_title", ""),
            line_number=data.get("line_number"),
            column_number=data.get("column_number"),
            error_type=data.get("error_type", "")
        )