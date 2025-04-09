"""
Main package for the MCP server application.
"""

# flake8: noqa
# Ignore F401: Imported but unused

__version__ = "0.1.0"

# Core server components (app, server object)
from .core import server, app

# Utils (Import specific necessary utils if needed, or rely on sub-package access)
# Example: from .utils.error_handling import SecurityError

# Command execution functions (Re-export from core)
from .core import (
    execute_command,
    read_output,
    force_terminate,
    list_sessions,
)

# Security functions/variables (Re-export from core)
from .core import (
    is_command_safe,
    block_command,
    unblock_command,
    blacklisted_commands, # The actual set from security.py
    DEFAULT_BLACKLIST # The default set from security.py
)

# LLM Server (if needed directly)
# from .llm import server as llm_server

# Other sub-servers (if needed directly)
# from .neodo import server as neodo_server
# from .neolocal import server as neolocal_server
# from .neoo import server as neoo_server
# from .neod import server as neod_server
# from .neollm import server as neollm_server

__all__ = [
    # Core Server
    "server", 
    "app", 
    
    # Command Execution
    "execute_command",
    "read_output",
    "force_terminate",
    "list_sessions",
    
    # Security
    "is_command_safe",
    "block_command",
    "unblock_command",
    "blacklisted_commands",
    "DEFAULT_BLACKLIST",
    
    # Sub-servers (uncomment if needed)
    # "llm_server",
    # "neodo_server",
    # "neolocal_server",
    # "neoo_server",
    # "neod_server",
    # "neollm_server",
] 