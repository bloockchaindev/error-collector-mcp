"""Error summary model for AI-generated analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List
import uuid


@dataclass
class ErrorSummary:
    """AI-generated summary and analysis of errors."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    error_ids: List[str] = field(default_factory=list)
    root_cause: str = ""
    impact_assessment: str = ""
    suggested_solutions: List[str] = field(default_factory=list)
    related_errors: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    generated_at: datetime = field(default_factory=datetime.utcnow)
    model_used: str = ""
    processing_time_ms: int = 0
    
    def __post_init__(self):
        """Validate summary fields after initialization."""
        if not self.error_ids:
            raise ValueError("Error summary must reference at least one error")
        
        if not self.root_cause.strip():
            raise ValueError("Root cause cannot be empty")
        
        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        
        # Ensure suggested solutions are non-empty strings
        self.suggested_solutions = [
            solution.strip() for solution in self.suggested_solutions 
            if solution.strip()
        ]
    
    def add_error_id(self, error_id: str) -> None:
        """Add an error ID to this summary."""
        if error_id not in self.error_ids:
            self.error_ids.append(error_id)
    
    def add_suggested_solution(self, solution: str) -> None:
        """Add a suggested solution."""
        solution = solution.strip()
        if solution and solution not in self.suggested_solutions:
            self.suggested_solutions.append(solution)
    
    def add_related_error(self, error_id: str) -> None:
        """Add a related error ID."""
        if error_id not in self.related_errors and error_id not in self.error_ids:
            self.related_errors.append(error_id)
    
    def get_error_count(self) -> int:
        """Get the number of errors this summary covers."""
        return len(self.error_ids)
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this summary has high confidence."""
        return self.confidence_score >= threshold
    
    def get_priority_score(self) -> float:
        """Calculate priority score based on error count and confidence."""
        # More errors and higher confidence = higher priority
        error_weight = min(len(self.error_ids) / 10.0, 1.0)  # Cap at 10 errors
        confidence_weight = self.confidence_score
        return (error_weight + confidence_weight) / 2.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert summary to dictionary representation."""
        return {
            "id": self.id,
            "error_ids": self.error_ids,
            "root_cause": self.root_cause,
            "impact_assessment": self.impact_assessment,
            "suggested_solutions": self.suggested_solutions,
            "related_errors": self.related_errors,
            "confidence_score": self.confidence_score,
            "generated_at": self.generated_at.isoformat(),
            "model_used": self.model_used,
            "processing_time_ms": self.processing_time_ms,
            "error_count": self.get_error_count(),
            "is_high_confidence": self.is_high_confidence(),
            "priority_score": self.get_priority_score()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorSummary":
        """Create summary from dictionary representation."""
        return cls(
            id=data["id"],
            error_ids=data["error_ids"],
            root_cause=data["root_cause"],
            impact_assessment=data["impact_assessment"],
            suggested_solutions=data["suggested_solutions"],
            related_errors=data.get("related_errors", []),
            confidence_score=data["confidence_score"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            model_used=data.get("model_used", ""),
            processing_time_ms=data.get("processing_time_ms", 0)
        )
    
    def format_for_display(self) -> str:
        """Format summary for human-readable display."""
        lines = [
            f"Error Summary (ID: {self.id[:8]}...)",
            f"Errors Analyzed: {len(self.error_ids)}",
            f"Confidence: {self.confidence_score:.1%}",
            "",
            "Root Cause:",
            f"  {self.root_cause}",
            "",
            "Impact Assessment:",
            f"  {self.impact_assessment}",
            ""
        ]
        
        if self.suggested_solutions:
            lines.append("Suggested Solutions:")
            for i, solution in enumerate(self.suggested_solutions, 1):
                lines.append(f"  {i}. {solution}")
            lines.append("")
        
        if self.related_errors:
            lines.append(f"Related Errors: {len(self.related_errors)}")
            lines.append("")
        
        lines.append(f"Generated: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if self.model_used:
            lines.append(f"Model: {self.model_used}")
        
        return "\n".join(lines)