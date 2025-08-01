"""Terminal-specific error model."""

from dataclasses import dataclass, field
from typing import Any, Dict
from .base_error import BaseError, ErrorSource, ErrorCategory


@dataclass
class TerminalError(BaseError):
    """Terminal/CLI error with command execution context."""
    
    command: str = ""
    exit_code: int = 0
    working_directory: str = ""
    environment: Dict[str, str] = field(default_factory=dict)
    stderr_output: str = ""
    stdout_output: str = ""
    
    def __post_init__(self):
        """Initialize terminal error with proper source and context."""
        self.source = ErrorSource.TERMINAL
        
        # Use stderr as message if message is empty
        if not self.message.strip() and self.stderr_output:
            self.message = self.stderr_output.strip()
        
        super().__post_init__()
        
        # Override category based on command and error patterns
        self.category = self._categorize_terminal_error()
        
        # Add terminal-specific context
        self.context.update({
            "command": self.command,
            "exit_code": self.exit_code,
            "working_directory": self.working_directory,
            "environment": self.environment,
            "stderr_output": self.stderr_output,
            "stdout_output": self.stdout_output
        })
    
    def _categorize_terminal_error(self) -> ErrorCategory:
        """Categorize terminal error based on command and output."""
        command_lower = self.command.lower()
        error_output = (self.stderr_output + " " + self.message).lower()
        
        # Compilation errors
        if any(cmd in command_lower for cmd in ["gcc", "g++", "clang", "javac", "tsc", "rustc"]):
            if any(keyword in error_output for keyword in ["syntax error", "parse error"]):
                return ErrorCategory.SYNTAX
            return ErrorCategory.RUNTIME
        
        # Package management errors
        if any(cmd in command_lower for cmd in ["npm", "pip", "cargo", "apt", "brew"]):
            if any(keyword in error_output for keyword in ["permission denied", "access"]):
                return ErrorCategory.PERMISSION
            if any(keyword in error_output for keyword in ["network", "connection", "timeout"]):
                return ErrorCategory.NETWORK
            return ErrorCategory.RESOURCE
        
        # Git errors
        if "git" in command_lower:
            if any(keyword in error_output for keyword in ["permission", "access", "authentication"]):
                return ErrorCategory.PERMISSION
            if any(keyword in error_output for keyword in ["network", "connection", "remote"]):
                return ErrorCategory.NETWORK
            return ErrorCategory.LOGIC
        
        # File system errors
        if any(cmd in command_lower for cmd in ["ls", "cd", "mkdir", "rm", "cp", "mv"]):
            if any(keyword in error_output for keyword in ["permission denied", "access"]):
                return ErrorCategory.PERMISSION
            if any(keyword in error_output for keyword in ["no such file", "not found"]):
                return ErrorCategory.RESOURCE
            return ErrorCategory.LOGIC
        
        # Network commands
        if any(cmd in command_lower for cmd in ["curl", "wget", "ping", "ssh"]):
            return ErrorCategory.NETWORK
        
        # Default categorization based on exit code
        if self.exit_code == 126 or self.exit_code == 127:
            return ErrorCategory.PERMISSION
        elif self.exit_code == 130:  # Ctrl+C
            return ErrorCategory.LOGIC
        elif self.exit_code > 128:  # Signal termination
            return ErrorCategory.RUNTIME
        
        return super()._auto_categorize()
    
    def get_command_summary(self) -> str:
        """Get a summary of the failed command."""
        if not self.command:
            return "unknown command"
        
        # Truncate very long commands
        if len(self.command) > 100:
            return self.command[:97] + "..."
        
        return self.command
    
    def is_compilation_error(self) -> bool:
        """Check if this is a compilation error."""
        return self.category == ErrorCategory.SYNTAX or any(
            compiler in self.command.lower() 
            for compiler in ["gcc", "g++", "clang", "javac", "tsc", "rustc", "python", "node"]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert terminal error to dictionary representation."""
        base_dict = super().to_dict()
        base_dict.update({
            "command": self.command,
            "exit_code": self.exit_code,
            "working_directory": self.working_directory,
            "environment": self.environment,
            "stderr_output": self.stderr_output,
            "stdout_output": self.stdout_output,
            "command_summary": self.get_command_summary(),
            "is_compilation_error": self.is_compilation_error()
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TerminalError":
        """Create terminal error from dictionary representation."""
        base_error = super().from_dict(data)
        return cls(
            id=base_error.id,
            timestamp=base_error.timestamp,
            message=base_error.message,
            stack_trace=base_error.stack_trace,
            context=base_error.context,
            severity=base_error.severity,
            category=base_error.category,
            command=data.get("command", ""),
            exit_code=data.get("exit_code", 0),
            working_directory=data.get("working_directory", ""),
            environment=data.get("environment", {}),
            stderr_output=data.get("stderr_output", ""),
            stdout_output=data.get("stdout_output", "")
        )