"""
Core MCP Server package.
"""

from .server import create_app

# Import and re-export command execution utils (excluding security functions)
from ..utils.command_execution import CommandExecutor
execute_command = CommandExecutor().execute
read_output = CommandExecutor().get_output
force_terminate = CommandExecutor().terminate
list_sessions = CommandExecutor().list_processes

# Import and re-export security-related functions and variables directly
from ..utils.security import (
    is_command_safe,
    block_command,
    unblock_command,
    blacklisted_commands,
    DEFAULT_BLACKLIST
)

# Session management
import threading
session_lock = threading.Lock()
active_sessions = {}

__all__ = [
    "create_app",
    # Security functions/vars
    "is_command_safe",
    "block_command",
    "unblock_command",
    "blacklisted_commands",
    "DEFAULT_BLACKLIST",
    # Command execution functions
    "execute_command",
    "read_output",
    "force_terminate",
    "list_sessions",
    # Session state (consider if these should be exported)
    # "session_lock",
    # "active_sessions"
] 