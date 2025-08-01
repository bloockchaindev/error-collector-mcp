"""Base error model and enums."""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSource(str, Enum):
    """Source of the error."""
    BROWSER = "browser"
    TERMINAL = "terminal"
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Severity level of the error."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Category of the error."""
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    NETWORK = "network"
    PERMISSION = "permission"
    RESOURCE = "resource"
    LOGIC = "logic"
    UNKNOWN = "unknown"


@dataclass
class BaseError:
    """Base error model with common fields."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: ErrorSource = ErrorSource.UNKNOWN
    message: str = ""
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN
    
    def __post_init__(self):
        """Validate and process fields after initialization."""
        if not self.message.strip():
            raise ValueError("Error message cannot be empty")
        
        # Auto-categorize based on message content
        if self.category == ErrorCategory.UNKNOWN:
            self.category = self._auto_categorize()
        
        # Auto-determine severity based on category and content
        if self.severity == ErrorSeverity.MEDIUM:
            self.severity = self._auto_determine_severity()
    
    def _auto_categorize(self) -> ErrorCategory:
        """Automatically categorize error based on message content."""
        message_lower = self.message.lower()
        
        # Syntax errors
        if any(keyword in message_lower for keyword in [
            "syntax error", "syntaxerror", "unexpected token", "parse error"
        ]):
            return ErrorCategory.SYNTAX
        
        # Network errors
        if any(keyword in message_lower for keyword in [
            "network", "fetch", "cors", "connection", "timeout", "404", "500"
        ]):
            return ErrorCategory.NETWORK
        
        # Permission errors
        if any(keyword in message_lower for keyword in [
            "permission", "access denied", "unauthorized", "forbidden"
        ]):
            return ErrorCategory.PERMISSION
        
        # Resource errors
        if any(keyword in message_lower for keyword in [
            "out of memory", "disk space", "resource", "quota"
        ]):
            return ErrorCategory.RESOURCE
        
        # Runtime errors (default for many JS errors)
        if any(keyword in message_lower for keyword in [
            "runtime", "reference", "type", "null", "undefined"
        ]):
            return ErrorCategory.RUNTIME
        
        return ErrorCategory.UNKNOWN
    
    def _auto_determine_severity(self) -> ErrorSeverity:
        """Automatically determine severity based on category and content."""
        message_lower = self.message.lower()
        
        # Critical indicators
        if any(keyword in message_lower for keyword in [
            "critical", "fatal", "crash", "segmentation fault", "out of memory"
        ]):
            return ErrorSeverity.CRITICAL
        
        # High severity indicators
        if any(keyword in message_lower for keyword in [
            "error", "exception", "failed", "cannot", "unable"
        ]) or self.category in [ErrorCategory.SYNTAX, ErrorCategory.PERMISSION]:
            return ErrorSeverity.HIGH
        
        # Low severity indicators
        if any(keyword in message_lower for keyword in [
            "warning", "deprecated", "notice"
        ]):
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source.value,
            "message": self.message,
            "stack_trace": self.stack_trace,
            "context": self.context,
            "severity": self.severity.value,
            "category": self.category.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseError":
        """Create error from dictionary representation."""
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            source=ErrorSource(data["source"]),
            message=data["message"],
            stack_trace=data.get("stack_trace"),
            context=data.get("context", {}),
            severity=ErrorSeverity(data["severity"]),
            category=ErrorCategory(data["category"])
        )