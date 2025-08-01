"""Terminal error collector for monitoring command execution."""

import asyncio
import logging
import os
import subprocess
import shlex
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass

from .base_collector import BaseCollector
from ..models import TerminalError, ErrorSeverity


logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    """Result of a command execution."""
    command: str
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    working_directory: str
    environment: Dict[str, str]
    timestamp: datetime


class TerminalCollector(BaseCollector):
    """Collector for terminal/CLI errors with command monitoring."""
    
    def __init__(self, name: str = "terminal"):
        super().__init__(name)
        self._collected_errors: List[TerminalError] = []
        self._error_patterns = self._load_error_patterns()
        self._monitoring_active = False
        self._shell_wrapper_active = False
        self._command_history: List[CommandResult] = []
        self._max_history = 1000
        
        # Callbacks for real-time error notification
        self._error_callbacks: List[Callable[[TerminalError], None]] = []
    
    async def start_collection(self) -> None:
        """Start collecting terminal errors."""
        if self._is_collecting:
            logger.warning("Terminal collector is already running")
            return
        
        self._is_collecting = True
        self._monitoring_active = True
        
        # Start background monitoring tasks
        asyncio.create_task(self._monitor_shell_integration())
        
        logger.info("Terminal error collection started")
    
    async def stop_collection(self) -> None:
        """Stop collecting terminal errors."""
        if not self._is_collecting:
            return
        
        self._is_collecting = False
        self._monitoring_active = False
        self._shell_wrapper_active = False
        
        logger.info("Terminal error collection stopped")
    
    async def get_collected_errors(self) -> List[TerminalError]:
        """Get all collected errors since last retrieval."""
        errors = self._collected_errors.copy()
        self._collected_errors.clear()
        return errors
    
    async def execute_command(
        self, 
        command: str, 
        working_dir: Optional[str] = None,
        timeout: Optional[float] = None,
        capture_errors: bool = True
    ) -> CommandResult:
        """Execute a command and capture any errors."""
        start_time = time.time()
        working_directory = working_dir or os.getcwd()
        
        try:
            # Parse command safely
            if isinstance(command, str):
                cmd_args = shlex.split(command)
            else:
                cmd_args = command
            
            # Set up process environment
            env = os.environ.copy()
            
            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_directory,
                env=env
            )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                exit_code = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                stdout_bytes = b""
                stderr_bytes = b"Command timed out"
                exit_code = -1
            
            # Decode output
            stdout = stdout_bytes.decode('utf-8', errors='replace')
            stderr = stderr_bytes.decode('utf-8', errors='replace')
            
            execution_time = time.time() - start_time
            
            # Create command result
            result = CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                execution_time=execution_time,
                working_directory=working_directory,
                environment=env,
                timestamp=datetime.utcnow()
            )
            
            # Add to command history
            self._add_to_history(result)
            
            # Check for errors if capture is enabled
            if capture_errors and (exit_code != 0 or self._has_error_patterns(stderr)):
                error = await self._create_error_from_result(result)
                if error:
                    await self._collect_error(error)
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed to execute command '{command}': {e}")
            
            # Create error result
            result = CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"Execution failed: {str(e)}",
                execution_time=execution_time,
                working_directory=working_directory,
                environment=os.environ.copy(),
                timestamp=datetime.utcnow()
            )
            
            if capture_errors:
                error = await self._create_error_from_result(result)
                if error:
                    await self._collect_error(error)
            
            return result
    
    async def monitor_command_file(self, file_path: str) -> None:
        """Monitor a file for command execution logs."""
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            logger.warning(f"Command log file does not exist: {file_path}")
            return
        
        logger.info(f"Monitoring command log file: {file_path}")
        
        # Get initial file size
        last_size = file_path_obj.stat().st_size
        
        while self._monitoring_active:
            try:
                current_size = file_path_obj.stat().st_size
                
                if current_size > last_size:
                    # Read new content
                    with open(file_path_obj, 'r', encoding='utf-8', errors='replace') as f:
                        f.seek(last_size)
                        new_content = f.read()
                    
                    # Process new log entries
                    await self._process_log_content(new_content)
                    last_size = current_size
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error monitoring command file: {e}")
                await asyncio.sleep(5)  # Wait longer on error
    
    def add_error_callback(self, callback: Callable[[TerminalError], None]) -> None:
        """Add a callback to be notified of new errors."""
        self._error_callbacks.append(callback)
    
    def remove_error_callback(self, callback: Callable[[TerminalError], None]) -> None:
        """Remove an error callback."""
        if callback in self._error_callbacks:
            self._error_callbacks.remove(callback)
    
    async def get_command_history(self, limit: int = 100) -> List[CommandResult]:
        """Get recent command execution history."""
        return self._command_history[-limit:]
    
    async def get_failed_commands(self, limit: int = 50) -> List[CommandResult]:
        """Get recent failed commands."""
        failed_commands = [
            cmd for cmd in self._command_history 
            if cmd.exit_code != 0
        ]
        return failed_commands[-limit:]
    
    async def health_check(self) -> bool:
        """Check if the terminal collector is healthy."""
        try:
            # Test basic command execution
            result = await self.execute_command("echo 'health_check'", timeout=5.0)
            return result.exit_code == 0 and "health_check" in result.stdout
        except Exception as e:
            logger.error(f"Terminal collector health check failed: {e}")
            return False
    
    def _load_error_patterns(self) -> Dict[str, List[str]]:
        """Load common error patterns for different tools."""
        return {
            "compilation": [
                r"error:",
                r"fatal error:",
                r"syntax error",
                r"parse error",
                r"compilation terminated",
                r"undefined reference",
                r"cannot find symbol",
                r"type.*error",
                r"compilation failed"
            ],
            "network": [
                r"connection.*refused",
                r"network.*unreachable",
                r"timeout",
                r"dns.*resolution.*failed",
                r"certificate.*error",
                r"ssl.*error",
                r"tls.*error"
            ],
            "permission": [
                r"permission denied",
                r"access denied",
                r"operation not permitted",
                r"insufficient privileges",
                r"unauthorized",
                r"forbidden"
            ],
            "resource": [
                r"no space left",
                r"disk.*full",
                r"out of memory",
                r"memory.*exhausted",
                r"resource.*unavailable",
                r"quota.*exceeded"
            ],
            "package_management": [
                r"package.*not found",
                r"dependency.*error",
                r"version.*conflict",
                r"installation.*failed",
                r"repository.*error"
            ]
        }
    
    def _has_error_patterns(self, text: str) -> bool:
        """Check if text contains known error patterns."""
        import re
        text_lower = text.lower()
        
        for category, patterns in self._error_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return True
        
        return False
    
    async def _create_error_from_result(self, result: CommandResult) -> Optional[TerminalError]:
        """Create a TerminalError from a CommandResult."""
        if result.exit_code == 0 and not self._has_error_patterns(result.stderr):
            return None
        
        # Determine error message
        error_message = result.stderr.strip()
        if not error_message and result.exit_code != 0:
            error_message = f"Command failed with exit code {result.exit_code}"
        
        if not error_message:
            return None
        
        # Determine severity based on exit code and patterns
        severity = self._determine_error_severity(result)
        
        # Create terminal error
        error = TerminalError(
            message=error_message,
            command=result.command,
            exit_code=result.exit_code,
            working_directory=result.working_directory,
            environment=result.environment,
            stderr_output=result.stderr,
            stdout_output=result.stdout,
            timestamp=result.timestamp,
            severity=severity
        )
        
        return error
    
    def _determine_error_severity(self, result: CommandResult) -> ErrorSeverity:
        """Determine error severity based on command result."""
        stderr_lower = result.stderr.lower()
        
        # Critical errors
        if any(pattern in stderr_lower for pattern in [
            "fatal", "critical", "segmentation fault", "core dumped", "out of memory"
        ]):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if any(pattern in stderr_lower for pattern in [
            "error:", "compilation failed", "build failed", "test failed"
        ]) or result.exit_code in [1, 2]:
            return ErrorSeverity.HIGH
        
        # Medium severity for other non-zero exit codes
        if result.exit_code != 0:
            return ErrorSeverity.MEDIUM
        
        # Low severity for warnings in stderr
        if any(pattern in stderr_lower for pattern in [
            "warning", "deprecated", "notice"
        ]):
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    async def _collect_error(self, error: TerminalError) -> None:
        """Collect a terminal error."""
        self._collected_errors.append(error)
        
        # Notify callbacks
        for callback in self._error_callbacks:
            try:
                callback(error)
            except Exception as e:
                logger.error(f"Error in error callback: {e}")
        
        logger.debug(f"Collected terminal error: {error.message[:100]}...")
    
    def _add_to_history(self, result: CommandResult) -> None:
        """Add command result to history."""
        self._command_history.append(result)
        
        # Maintain history size limit
        if len(self._command_history) > self._max_history:
            self._command_history = self._command_history[-self._max_history:]
    
    async def _monitor_shell_integration(self) -> None:
        """Monitor for shell integration opportunities."""
        # This is a placeholder for future shell integration features
        # Could include monitoring bash history, zsh hooks, etc.
        while self._monitoring_active:
            try:
                # Check for shell integration opportunities
                await self._check_shell_hooks()
                await asyncio.sleep(10)  # Check every 10 seconds
            except Exception as e:
                logger.error(f"Error in shell integration monitoring: {e}")
                await asyncio.sleep(30)
    
    async def _check_shell_hooks(self) -> None:
        """Check for available shell integration hooks."""
        # Future implementation could include:
        # - Bash PROMPT_COMMAND integration
        # - Zsh preexec/precmd hooks
        # - Fish shell event handlers
        # - PowerShell profile integration
        pass
    
    async def _process_log_content(self, content: str) -> None:
        """Process new log file content for errors."""
        lines = content.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            # Try to parse log line for command information
            # This is a simple implementation - could be enhanced for specific log formats
            if self._has_error_patterns(line):
                # Create a simple error from log line
                error = TerminalError(
                    message=line.strip(),
                    command="unknown",
                    exit_code=1,
                    working_directory=os.getcwd(),
                    environment={},
                    stderr_output=line,
                    stdout_output="",
                    timestamp=datetime.utcnow()
                )
                
                await self._collect_error(error)