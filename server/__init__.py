"""
MCP Server package for managing LLM and core tools.
"""

__version__ = "0.1.0"

from .core import server, app
from .utils.command_execution import CommandExecutor

# Export command execution functionality
is_command_safe = CommandExecutor()._validate_command
execute_command = CommandExecutor().execute
read_output = CommandExecutor().get_output
force_terminate = CommandExecutor().terminate
block_command = CommandExecutor()._validate_command
unblock_command = lambda _: None  # No-op since validation is done at execution time
blacklisted_commands = CommandExecutor().blacklist

# Remove circular imports
# from .core import (
#     is_command_safe,
#     execute_command,
#     read_output,
#     force_terminate,
#     block_command,
#     unblock_command,
#     blacklisted_commands
# ) 