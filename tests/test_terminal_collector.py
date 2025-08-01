"""Tests for terminal error collector."""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from error_collector_mcp.collectors.terminal_collector import TerminalCollector, CommandResult
from error_collector_mcp.collectors.shell_wrapper import ShellWrapper
from error_collector_mcp.models import TerminalError, ErrorSeverity


class TestTerminalCollector:
    """Test TerminalCollector functionality."""
    
    @pytest.fixture
    def terminal_collector(self):
        """Create a terminal collector instance."""
        return TerminalCollector()
    
    @pytest.mark.asyncio
    async def test_start_stop_collection(self, terminal_collector):
        """Test starting and stopping collection."""
        assert not terminal_collector.is_collecting
        
        await terminal_collector.start_collection()
        assert terminal_collector.is_collecting
        
        await terminal_collector.stop_collection()
        assert not terminal_collector.is_collecting
    
    @pytest.mark.asyncio
    async def test_execute_successful_command(self, terminal_collector):
        """Test executing a successful command."""
        result = await terminal_collector.execute_command("echo 'hello world'")
        
        assert isinstance(result, CommandResult)
        assert result.exit_code == 0
        assert "hello world" in result.stdout
        assert result.stderr == ""
        assert result.command == "echo 'hello world'"
    
    @pytest.mark.asyncio
    async def test_execute_failing_command(self, terminal_collector):
        """Test executing a command that fails."""
        await terminal_collector.start_collection()
        
        # Execute a command that should fail
        result = await terminal_collector.execute_command("ls /nonexistent/directory")
        
        assert result.exit_code != 0
        assert len(result.stderr) > 0
        
        # Should have collected an error
        errors = await terminal_collector.get_collected_errors()
        assert len(errors) == 1
        assert isinstance(errors[0], TerminalError)
        assert errors[0].exit_code != 0
    
    @pytest.mark.asyncio
    async def test_command_timeout(self, terminal_collector):
        """Test command timeout handling."""
        # Use a command that would run indefinitely
        result = await terminal_collector.execute_command("sleep 10", timeout=0.1)
        
        assert result.exit_code == -1
        assert "timed out" in result.stderr.lower()
    
    @pytest.mark.asyncio
    async def test_error_pattern_detection(self, terminal_collector):
        """Test detection of error patterns in output."""
        await terminal_collector.start_collection()
        
        # Simulate a compilation error
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = MagicMock()
            mock_process.communicate.return_value = asyncio.coroutine(
                lambda: (b"", b"error: syntax error at line 5")
            )()
            mock_process.returncode = 0  # Even with exit code 0, should detect error
            mock_subprocess.return_value = mock_process
            
            result = await terminal_collector.execute_command("gcc test.c")
            
            # Should detect error pattern even with exit code 0
            errors = await terminal_collector.get_collected_errors()
            assert len(errors) == 1
            assert "syntax error" in errors[0].message
    
    @pytest.mark.asyncio
    async def test_error_severity_determination(self, terminal_collector):
        """Test error severity determination."""
        await terminal_collector.start_collection()
        
        test_cases = [
            ("fatal error: compilation terminated", ErrorSeverity.CRITICAL),
            ("error: undefined reference", ErrorSeverity.HIGH),
            ("warning: deprecated function", ErrorSeverity.LOW),
            ("build failed", ErrorSeverity.HIGH)
        ]
        
        for stderr_output, expected_severity in test_cases:
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = MagicMock()
                mock_process.communicate.return_value = asyncio.coroutine(
                    lambda: (b"", stderr_output.encode())
                )()
                mock_process.returncode = 1
                mock_subprocess.return_value = mock_process
                
                await terminal_collector.execute_command("test command")
                
                errors = await terminal_collector.get_collected_errors()
                if errors:  # Some patterns might not trigger error collection
                    assert errors[-1].severity == expected_severity
    
    @pytest.mark.asyncio
    async def test_command_history(self, terminal_collector):
        """Test command history tracking."""
        # Execute several commands
        commands = ["echo 'test1'", "echo 'test2'", "ls /tmp"]
        
        for cmd in commands:
            await terminal_collector.execute_command(cmd)
        
        # Check history
        history = await terminal_collector.get_command_history()
        assert len(history) >= len(commands)
        
        # Check that commands are in history
        history_commands = [result.command for result in history]
        for cmd in commands:
            assert cmd in history_commands
    
    @pytest.mark.asyncio
    async def test_failed_commands_tracking(self, terminal_collector):
        """Test tracking of failed commands."""
        # Execute some successful and failed commands
        await terminal_collector.execute_command("echo 'success'")
        await terminal_collector.execute_command("ls /nonexistent")
        await terminal_collector.execute_command("echo 'another success'")
        
        # Get failed commands
        failed_commands = await terminal_collector.get_failed_commands()
        
        # Should have at least one failed command
        assert len(failed_commands) >= 1
        assert all(cmd.exit_code != 0 for cmd in failed_commands)
    
    @pytest.mark.asyncio
    async def test_error_callbacks(self, terminal_collector):
        """Test error callback functionality."""
        callback_errors = []
        
        def error_callback(error: TerminalError):
            callback_errors.append(error)
        
        terminal_collector.add_error_callback(error_callback)
        await terminal_collector.start_collection()
        
        # Execute a failing command
        await terminal_collector.execute_command("ls /nonexistent")
        
        # Should have called the callback
        assert len(callback_errors) == 1
        assert isinstance(callback_errors[0], TerminalError)
        
        # Remove callback and test
        terminal_collector.remove_error_callback(error_callback)
        await terminal_collector.execute_command("ls /another_nonexistent")
        
        # Should not have added another error to callback list
        assert len(callback_errors) == 1
    
    @pytest.mark.asyncio
    async def test_health_check(self, terminal_collector):
        """Test health check functionality."""
        health_status = await terminal_collector.health_check()
        assert health_status is True
    
    @pytest.mark.asyncio
    async def test_monitor_command_file(self, terminal_collector):
        """Test monitoring a command log file."""
        # Create a temporary log file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            log_file_path = f.name
            f.write("Initial content\n")
        
        try:
            await terminal_collector.start_collection()
            
            # Start monitoring in background
            monitor_task = asyncio.create_task(
                terminal_collector.monitor_command_file(log_file_path)
            )
            
            # Give it a moment to start
            await asyncio.sleep(0.1)
            
            # Append error content to file
            with open(log_file_path, 'a') as f:
                f.write("error: something went wrong\n")
                f.write("fatal: critical failure\n")
            
            # Give it time to process
            await asyncio.sleep(0.2)
            
            # Cancel monitoring
            monitor_task.cancel()
            
            # Check if errors were collected
            errors = await terminal_collector.get_collected_errors()
            assert len(errors) >= 1
            
        finally:
            # Cleanup
            os.unlink(log_file_path)
    
    @pytest.mark.asyncio
    async def test_working_directory_handling(self, terminal_collector):
        """Test handling of working directory in commands."""
        temp_dir = tempfile.mkdtemp()
        
        try:
            result = await terminal_collector.execute_command("pwd", working_dir=temp_dir)
            
            assert result.exit_code == 0
            assert temp_dir in result.stdout
            assert result.working_directory == temp_dir
            
        finally:
            os.rmdir(temp_dir)


class TestShellWrapper:
    """Test ShellWrapper functionality."""
    
    @pytest.fixture
    def shell_wrapper(self):
        """Create a shell wrapper instance."""
        return ShellWrapper()
    
    def test_log_file_creation(self, shell_wrapper):
        """Test that log file path is created properly."""
        log_file = shell_wrapper.log_file
        assert isinstance(log_file, Path)
        assert log_file.parent.exists()
    
    def test_error_detection(self, shell_wrapper):
        """Test error detection in stderr."""
        # Test cases with expected results
        test_cases = [
            ("error: compilation failed", True),
            ("warning: deprecated function", True),
            ("fatal: system crash", True),
            ("info: process completed", False),
            ("success: operation completed", False),
            ("", False)
        ]
        
        for stderr, should_detect in test_cases:
            result = shell_wrapper._has_error_indicators(stderr)
            assert result == should_detect, f"Failed for: {stderr}"
    
    def test_wrap_command_with_error(self, shell_wrapper):
        """Test wrapping a command that has an error."""
        # Mock the log file to capture output
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_log:
            shell_wrapper.log_file = Path(temp_log.name)
            
            # Wrap a failing command
            shell_wrapper.wrap_command(
                command="test command",
                exit_code=1,
                stderr="error: something went wrong",
                stdout=""
            )
            
            # Check that error was logged
            temp_log.seek(0)
            log_content = temp_log.read()
            assert "test command" in log_content
            assert "error: something went wrong" in log_content
            assert '"exit_code": 1' in log_content
        
        # Cleanup
        os.unlink(temp_log.name)
    
    def test_wrap_command_success(self, shell_wrapper):
        """Test wrapping a successful command."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_log:
            shell_wrapper.log_file = Path(temp_log.name)
            
            # Wrap a successful command
            shell_wrapper.wrap_command(
                command="echo hello",
                exit_code=0,
                stderr="",
                stdout="hello"
            )
            
            # Check that nothing was logged (no error)
            temp_log.seek(0)
            log_content = temp_log.read()
            assert log_content.strip() == ""
        
        # Cleanup
        os.unlink(temp_log.name)
    
    def test_bash_integration_generation(self, shell_wrapper):
        """Test bash integration script generation."""
        script = shell_wrapper.generate_bash_integration()
        
        assert "bash" in script.lower()
        assert "trap" in script
        assert "_error_collector_capture" in script
        assert "ERROR_COLLECTOR_LOG_FILE" in script
    
    def test_zsh_integration_generation(self, shell_wrapper):
        """Test zsh integration script generation."""
        script = shell_wrapper.generate_zsh_integration()
        
        assert "zsh" in script.lower()
        assert "preexec" in script
        assert "precmd" in script
        assert "add-zsh-hook" in script
    
    def test_fish_integration_generation(self, shell_wrapper):
        """Test fish integration script generation."""
        script = shell_wrapper.generate_fish_integration()
        
        assert "fish" in script.lower()
        assert "fish_postexec" in script
        assert "function" in script
    
    def test_shell_detection(self, shell_wrapper):
        """Test shell detection."""
        # Test with different SHELL environment variables
        test_cases = [
            ("/bin/bash", "bash"),
            ("/usr/bin/zsh", "zsh"),
            ("/usr/local/bin/fish", "fish"),
            ("/bin/sh", "bash"),  # Default fallback
            ("/unknown/shell", "bash")  # Default fallback
        ]
        
        for shell_path, expected in test_cases:
            with patch.dict(os.environ, {'SHELL': shell_path}):
                detected = shell_wrapper._detect_shell()
                assert detected == expected
    
    def test_integration_instructions(self, shell_wrapper):
        """Test integration instructions generation."""
        for shell in ["bash", "zsh", "fish"]:
            instructions = shell_wrapper.get_integration_instructions(shell)
            
            assert shell in instructions.lower()
            assert "integration" in instructions.lower()
            assert str(shell_wrapper.log_file) in instructions
    
    @pytest.mark.asyncio
    async def test_install_shell_integration(self, shell_wrapper):
        """Test shell integration installation."""
        # Test bash installation
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock home directory
            with patch('pathlib.Path.home', return_value=Path(temp_dir)):
                install_path = shell_wrapper.install_shell_integration("bash")
                
                assert os.path.exists(install_path)
                
                # Check file content
                with open(install_path, 'r') as f:
                    content = f.read()
                    assert "bash" in content.lower()
                    assert "_error_collector_capture" in content