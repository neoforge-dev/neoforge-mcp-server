"""
Core MCP Server package.
"""

from .server import server, app
from ..utils.command_execution import CommandExecutor

# Export command execution functionality
is_command_safe = CommandExecutor()._validate_command
execute_command = CommandExecutor().execute
read_output = CommandExecutor().get_output
force_terminate = CommandExecutor().terminate
block_command = CommandExecutor()._validate_command
unblock_command = lambda _: None  # No-op since validation is done at execution time
blacklisted_commands = CommandExecutor().blacklist

# Session management
import threading
session_lock = threading.Lock()
active_sessions = {}

def list_sessions():
    """List all active command sessions."""
    with session_lock:
        return {
            "sessions": [
                {
                    "pid": pid,
                    "command": session["command"],
                    "start_time": session["start_time"],
                    "status": session["status"]
                }
                for pid, session in active_sessions.items()
            ]
        }

__all__ = [
    "server",
    "app",
    "is_command_safe",
    "execute_command",
    "read_output",
    "force_terminate",
    "block_command",
    "unblock_command",
    "blacklisted_commands",
    "list_sessions",
    "session_lock",
    "active_sessions"
] 