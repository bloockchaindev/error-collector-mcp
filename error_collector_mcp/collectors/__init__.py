"""Error collectors for different sources."""

from .base_collector import BaseCollector
from .browser_collector import BrowserConsoleCollector, BrowserErrorData
from .terminal_collector import TerminalCollector, CommandResult
from .shell_wrapper import ShellWrapper
from .browser_extension import BrowserExtensionBuilder

__all__ = [
    "BaseCollector",
    "BrowserConsoleCollector",
    "BrowserErrorData",
    "TerminalCollector",
    "CommandResult",
    "ShellWrapper",
    "BrowserExtensionBuilder"
]