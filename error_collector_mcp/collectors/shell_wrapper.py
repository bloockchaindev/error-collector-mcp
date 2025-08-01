"""Shell wrapper utilities for terminal error collection."""

import os
import sys
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ShellWrapper:
    """Wrapper for shell commands to capture errors."""
    
    def __init__(self, collector_endpoint: Optional[str] = None):
        self.collector_endpoint = collector_endpoint
        self.log_file = self._get_log_file()
    
    def _get_log_file(self) -> Path:
        """Get the log file path for error collection."""
        # Use a temporary directory for the log file
        temp_dir = Path(tempfile.gettempdir()) / "error-collector-mcp"
        temp_dir.mkdir(exist_ok=True)
        return temp_dir / "terminal_errors.log"
    
    def wrap_command(self, command: str, exit_code: int, stderr: str, stdout: str) -> None:
        """Wrap a command execution and log any errors."""
        if exit_code != 0 or self._has_error_indicators(stderr):
            error_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "command": command,
                "exit_code": exit_code,
                "stderr": stderr,
                "stdout": stdout,
                "working_directory": os.getcwd(),
                "environment": dict(os.environ)
            }
            
            self._log_error(error_data)
    
    def _has_error_indicators(self, stderr: str) -> bool:
        """Check if stderr contains error indicators."""
        error_keywords = [
            "error:", "fatal:", "warning:", "failed", "exception",
            "traceback", "stack trace", "segmentation fault"
        ]
        
        stderr_lower = stderr.lower()
        return any(keyword in stderr_lower for keyword in error_keywords)
    
    def _log_error(self, error_data: Dict[str, Any]) -> None:
        """Log error data to file."""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                json.dump(error_data, f)
                f.write('\n')
        except Exception as e:
            # Fallback to stderr if logging fails
            print(f"Failed to log error: {e}", file=sys.stderr)
    
    def generate_bash_integration(self) -> str:
        """Generate bash integration script."""
        wrapper_script = f'''
# Error Collector MCP - Bash Integration
# Add this to your ~/.bashrc or ~/.bash_profile

export ERROR_COLLECTOR_LOG_FILE="{self.log_file}"

# Function to capture command results
_error_collector_capture() {{
    local exit_code=$?
    local command="${{BASH_COMMAND}}"
    
    if [ $exit_code -ne 0 ]; then
        echo "{{
            \\"timestamp\\": \\"$(date -u +%Y-%m-%dT%H:%M:%S)\\",
            \\"command\\": \\"$command\\",
            \\"exit_code\\": $exit_code,
            \\"working_directory\\": \\"$(pwd)\\",
            \\"shell\\": \\"bash\\"
        }}" >> "$ERROR_COLLECTOR_LOG_FILE"
    fi
    
    return $exit_code
}}

# Set up trap to capture command failures
trap '_error_collector_capture' ERR

# Optional: Function to manually report errors
error_collector_report() {{
    local message="$1"
    echo "{{
        \\"timestamp\\": \\"$(date -u +%Y-%m-%dT%H:%M:%S)\\",
        \\"message\\": \\"$message\\",
        \\"command\\": \\"manual_report\\",
        \\"working_directory\\": \\"$(pwd)\\",
        \\"shell\\": \\"bash\\"
    }}" >> "$ERROR_COLLECTOR_LOG_FILE"
}}
'''
        return wrapper_script
    
    def generate_zsh_integration(self) -> str:
        """Generate zsh integration script."""
        wrapper_script = f'''
# Error Collector MCP - Zsh Integration
# Add this to your ~/.zshrc

export ERROR_COLLECTOR_LOG_FILE="{self.log_file}"

# Function to capture command results
_error_collector_preexec() {{
    _ERROR_COLLECTOR_COMMAND="$1"
}}

_error_collector_precmd() {{
    local exit_code=$?
    
    if [ $exit_code -ne 0 ] && [ -n "$_ERROR_COLLECTOR_COMMAND" ]; then
        echo "{{
            \\"timestamp\\": \\"$(date -u +%Y-%m-%dT%H:%M:%S)\\",
            \\"command\\": \\"$_ERROR_COLLECTOR_COMMAND\\",
            \\"exit_code\\": $exit_code,
            \\"working_directory\\": \\"$(pwd)\\",
            \\"shell\\": \\"zsh\\"
        }}" >> "$ERROR_COLLECTOR_LOG_FILE"
    fi
    
    _ERROR_COLLECTOR_COMMAND=""
}}

# Set up hooks
autoload -Uz add-zsh-hook
add-zsh-hook preexec _error_collector_preexec
add-zsh-hook precmd _error_collector_precmd

# Optional: Function to manually report errors
error_collector_report() {{
    local message="$1"
    echo "{{
        \\"timestamp\\": \\"$(date -u +%Y-%m-%dT%H:%M:%S)\\",
        \\"message\\": \\"$message\\",
        \\"command\\": \\"manual_report\\",
        \\"working_directory\\": \\"$(pwd)\\",
        \\"shell\\": \\"zsh\\"
    }}" >> "$ERROR_COLLECTOR_LOG_FILE"
}}
'''
        return wrapper_script
    
    def generate_fish_integration(self) -> str:
        """Generate fish shell integration script."""
        wrapper_script = f'''
# Error Collector MCP - Fish Integration
# Add this to your ~/.config/fish/config.fish

set -gx ERROR_COLLECTOR_LOG_FILE "{self.log_file}"

# Function to capture command failures
function _error_collector_capture --on-event fish_postexec
    set exit_code $status
    
    if test $exit_code -ne 0
        echo "{{
            \\"timestamp\\": \\"(date -u +%Y-%m-%dT%H:%M:%S)\\",
            \\"command\\": \\"$argv[1]\\",
            \\"exit_code\\": $exit_code,
            \\"working_directory\\": \\"(pwd)\\",
            \\"shell\\": \\"fish\\"
        }}" >> $ERROR_COLLECTOR_LOG_FILE
    end
end

# Optional: Function to manually report errors
function error_collector_report
    set message $argv[1]
    echo "{{
        \\"timestamp\\": \\"(date -u +%Y-%m-%dT%H:%M:%S)\\",
        \\"message\\": \\"$message\\",
        \\"command\\": \\"manual_report\\",
        \\"working_directory\\": \\"(pwd)\\",
        \\"shell\\": \\"fish\\"
    }}" >> $ERROR_COLLECTOR_LOG_FILE
end
'''
        return wrapper_script
    
    def install_shell_integration(self, shell: str = "auto") -> str:
        """Install shell integration for the specified shell."""
        if shell == "auto":
            shell = self._detect_shell()
        
        if shell == "bash":
            script = self.generate_bash_integration()
            install_path = Path.home() / ".error_collector_bash"
        elif shell == "zsh":
            script = self.generate_zsh_integration()
            install_path = Path.home() / ".error_collector_zsh"
        elif shell == "fish":
            script = self.generate_fish_integration()
            install_path = Path.home() / ".config" / "fish" / "conf.d" / "error_collector.fish"
            install_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            raise ValueError(f"Unsupported shell: {shell}")
        
        # Write integration script
        with open(install_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        # Make executable
        install_path.chmod(0o755)
        
        return str(install_path)
    
    def _detect_shell(self) -> str:
        """Detect the current shell."""
        shell_path = os.environ.get('SHELL', '/bin/bash')
        shell_name = Path(shell_path).name
        
        if shell_name in ['bash', 'zsh', 'fish']:
            return shell_name
        
        # Default to bash if unknown
        return 'bash'
    
    def get_integration_instructions(self, shell: str = "auto") -> str:
        """Get instructions for manual shell integration."""
        if shell == "auto":
            shell = self._detect_shell()
        
        instructions = f"""
Error Collector MCP - Shell Integration Instructions

Detected shell: {shell}

To enable automatic error collection, add the following to your shell configuration:

"""
        
        if shell == "bash":
            instructions += f"""
1. Add to ~/.bashrc or ~/.bash_profile:
   source ~/.error_collector_bash

2. Or run the installation command:
   error-collector-mcp install-shell-integration bash

3. Restart your terminal or run:
   source ~/.bashrc
"""
        elif shell == "zsh":
            instructions += f"""
1. Add to ~/.zshrc:
   source ~/.error_collector_zsh

2. Or run the installation command:
   error-collector-mcp install-shell-integration zsh

3. Restart your terminal or run:
   source ~/.zshrc
"""
        elif shell == "fish":
            instructions += f"""
1. The integration will be automatically loaded from:
   ~/.config/fish/conf.d/error_collector.fish

2. Or run the installation command:
   error-collector-mcp install-shell-integration fish

3. Restart your terminal or run:
   source ~/.config/fish/config.fish
"""
        
        instructions += f"""

Log file location: {self.log_file}

Manual error reporting:
You can manually report errors using:
error_collector_report "Your error message here"
"""
        
        return instructions


def main():
    """CLI entry point for shell wrapper utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Error Collector MCP Shell Integration")
    parser.add_argument("command", choices=["install", "instructions", "test"])
    parser.add_argument("--shell", choices=["bash", "zsh", "fish", "auto"], default="auto")
    
    args = parser.parse_args()
    wrapper = ShellWrapper()
    
    if args.command == "install":
        try:
            install_path = wrapper.install_shell_integration(args.shell)
            print(f"Shell integration installed to: {install_path}")
            print("Please restart your terminal or source your shell configuration file.")
        except Exception as e:
            print(f"Installation failed: {e}", file=sys.stderr)
            sys.exit(1)
    
    elif args.command == "instructions":
        print(wrapper.get_integration_instructions(args.shell))
    
    elif args.command == "test":
        # Test the wrapper
        wrapper.wrap_command("test command", 1, "test error", "")
        print(f"Test error logged to: {wrapper.log_file}")


if __name__ == "__main__":
    main()