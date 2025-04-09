"""
Shared security utilities for MCP servers.
"""

import os
import time
import hmac
import hashlib
import secrets
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from .error_handling import SecurityError, AuthenticationError, AuthorizationError
import logging
from fastapi import HTTPException

@dataclass
class ApiKey:
    """API key with metadata."""
    
    # Key details
    key_id: str
    key_hash: str
    
    # Key metadata
    name: str
    created_at: float
    expires_at: Optional[float] = None
    
    # Permissions
    roles: Set[str] = field(default_factory=set)
    scopes: Set[str] = field(default_factory=set)
    
    def is_expired(self) -> bool:
        """Check if key is expired."""
        return (
            self.expires_at is not None
            and time.time() > self.expires_at
        )
        
    def has_role(self, role: str) -> bool:
        """Check if key has role."""
        return role in self.roles
        
    def has_scope(self, scope: str) -> bool:
        """Check if key has scope."""
        return scope in self.scopes

class RateLimiter:
    """Rate limiter implementation."""
    
    def __init__(self, limit: int, window: int):
        """Initialize rate limiter.
        
        Args:
            limit: Maximum requests per window
            window: Time window in seconds
        """
        self.limit = limit
        self.window = window
        self.requests = defaultdict(list)
        
    def check_limit(self, key: str) -> bool:
        """Check if key has exceeded rate limit.
        
        Args:
            key: Rate limit key (e.g. IP address)
            
        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        
        # Remove old requests
        self.requests[key] = [
            ts for ts in self.requests[key]
            if now - ts < self.window
        ]
        
        # Check limit
        if len(self.requests[key]) >= self.limit:
            return False
            
        # Add request
        self.requests[key].append(now)
        return True
        
    def clear_old_requests(self) -> None:
        """Clear expired request records."""
        now = time.time()
        for key in list(self.requests.keys()):
            self.requests[key] = [
                ts for ts in self.requests[key]
                if now - ts < self.window
            ]
            if not self.requests[key]:
                del self.requests[key]

class SecurityManager:
    """Manages authentication and authorization."""
    
    def __init__(
        self,
        api_keys: Dict[str, Dict[str, Any]],
        enable_auth: bool = True,
        auth_token: Optional[str] = None
    ):
        """Initialize security manager.
        
        Args:
            api_keys: Dictionary of API keys and their permissions
            enable_auth: Whether to enable authentication
            auth_token: Optional auth token for server-to-server communication
        """
        self.enable_auth = enable_auth
        self.auth_token = auth_token
        self.logger = logging.getLogger(__name__)
        
        # Initialize API keys
        self.api_keys: Dict[str, ApiKey] = {}
        for key, info in api_keys.items():
            self.api_keys[key] = ApiKey(
                key_id=key,
                key_hash=hashlib.sha256(key.encode()).hexdigest(),
                name=key,
                created_at=info.get("created_at", time.time()),
                expires_at=info.get("expires_at"),
                roles=set(info.get("roles", [])),
                scopes=set(info.get("scopes", []))
            )
            
        # Role definitions
        self.roles: Dict[str, Set[str]] = {
            'admin': {'*'},  # Admin has all permissions
            'user': {
                'read:*',
                'write:own'
            }
        }
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(100, 60)
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
    def _start_cleanup_thread(self) -> None:
        """Start thread to clean up expired rate limit records."""
        import threading
        
        def cleanup():
            while True:
                time.sleep(60)  # Run every minute
                self.rate_limiter.clear_old_requests()
                
        thread = threading.Thread(target=cleanup, daemon=True)
        thread.start()
        
    def check_rate_limit(self, key: str) -> bool:
        """Check if key has exceeded rate limit.
        
        Args:
            key: Rate limit key (e.g. IP address)
            
        Returns:
            True if within limit, False if exceeded
        """
        return self.rate_limiter.check_limit(key)
        
    def _generate_key(self) -> Tuple[str, str]:
        """Generate new API key and hash.
        
        Returns:
            Tuple of (key, hash)
        """
        # Generate random key
        key = secrets.token_urlsafe(32)
        
        # Hash key
        key_hash = hashlib.pbkdf2_hmac(
            'sha256',
            key.encode(),
            os.urandom(32),
            100000
        ).hex()
        
        return key, key_hash
        
    def create_api_key(
        self,
        name: str,
        roles: Optional[Set[str]] = None,
        scopes: Optional[Set[str]] = None,
        expires_in: Optional[float] = None
    ) -> Tuple[str, ApiKey]:
        """Create new API key.
        
        Args:
            name: Key name
            roles: Assigned roles
            scopes: Assigned scopes
            expires_in: Expiration time in seconds
            
        Returns:
            Tuple of (key, ApiKey)
        """
        # Generate key
        key, key_hash = self._generate_key()
        key_id = hashlib.sha256(key_hash.encode()).hexdigest()[:8]
        
        # Create API key
        api_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            created_at=time.time(),
            expires_at=time.time() + expires_in if expires_in else None,
            roles=set(roles or []),
            scopes=set(scopes or [])
        )
        
        # Store key
        self.api_keys[key_id] = api_key
        
        return key, api_key
        
    def validate_api_key(self, api_key: str) -> ApiKey:
        """Validate an API key.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            ApiKey object if valid
            
        Raises:
            AuthenticationError if key is invalid
        """
        if not self.enable_auth:
            return ApiKey(key="anonymous", roles=set(), scopes=set("*:*"[:-1]))
            
        if not api_key:
            raise AuthenticationError(
                message="API key is required",
                details={"error": "missing_api_key"}
            )
            
        # Check if key exists
        if api_key not in self.api_keys:
            raise AuthenticationError(
                message="Invalid API key",
                details={"error": "invalid_api_key"}
            )
            
        key_info = self.api_keys[api_key]
        
        # Check if key is expired
        if key_info.expires_at and time.time() > key_info.expires_at:
            raise AuthenticationError(
                message="API key has expired",
                details={"error": "expired_api_key"}
            )
            
        return key_info
        
    def check_permission(self, api_key: ApiKey, permission: str) -> bool:
        """Check if an API key has a specific permission.
        
        Args:
            api_key: The API key to check
            permission: The permission to check for
            
        Returns:
            True if the key has the permission, False otherwise
        """
        # Anonymous access
        if not self.enable_auth:
            return True
            
        # Check for wildcard permission
        if "*:*" in api_key.scopes:
            return True
            
        # Check for specific permission
        if permission in api_key.scopes:
            return True
            
        # Check for wildcard namespace
        namespace = permission.split(":")[0]
        if f"{namespace}:*" in api_key.scopes:
            return True
            
        return False
        
    def require_scope(self, required_scope: str):
        """Decorator to require scope permission.
        
        Args:
            required_scope: Required permission scope
            
        Returns:
            Decorator function
        """
        def decorator(func):
            def wrapper(api_key: ApiKey, *args, **kwargs):
                if not self.check_permission(api_key, required_scope):
                    raise SecurityError(
                        "Insufficient permissions",
                        details={
                            "required_scope": required_scope,
                            "key_id": api_key.key_id
                        }
                    )
                return func(api_key, *args, **kwargs)
            return wrapper
        return decorator
        
    def revoke_api_key(self, api_key: str) -> None:
        """Revoke an API key.
        
        Args:
            api_key: The API key to revoke
        """
        if api_key in self.api_keys:
            del self.api_keys[api_key]
        
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys.
        
        Returns:
            List of API key information
        """
        keys = []
        for key_id, api_key in self.api_keys.items():
            keys.append({
                'key_id': key_id,
                'name': api_key.name,
                'created_at': api_key.created_at,
                'expires_at': api_key.expires_at,
                'roles': list(api_key.roles),
                'scopes': list(api_key.scopes),
                'expired': api_key.is_expired()
            })
        return keys
        
    def add_role(self, role: str, scopes: Set[str]) -> None:
        """Add or update role definition.
        
        Args:
            role: Role name
            scopes: Permission scopes
        """
        self.roles[role] = set(scopes)
        
    def remove_role(self, role: str) -> None:
        """Remove role definition.
        
        Args:
            role: Role to remove
        """
        self.roles.pop(role, None)
        
    def list_roles(self) -> Dict[str, List[str]]:
        """List all roles and their scopes.
        
        Returns:
            Dictionary of role definitions
        """
        return {
            role: list(scopes)
            for role, scopes in self.roles.items()
        }
        
    def validate_auth_token(self, token: str) -> bool:
        """Validate an auth token.
        
        Args:
            token: The token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        if not self.enable_auth or not self.auth_token:
            return True
            
        return hmac.compare_digest(token, self.auth_token)
        
    def get_api_key_info(self, api_key: str) -> Optional[ApiKey]:
        """Get information about an API key.
        
        Args:
            api_key: The API key to get info for
            
        Returns:
            ApiKey object if key exists, None otherwise
        """
        return self.api_keys.get(api_key)

# --- Command Security --- 

# Default blacklisted commands (moved from server/core.py)
DEFAULT_BLACKLIST = {
    'rm -rf /',
    'mkfs',
    'dd if=/dev/zero',
    'chmod -R 777',
    'shutdown',
    'reboot',
    '> /dev/sda',
    'fork bomb',
    ':(){:|:&};:',
    'eval',
    'exec',
}

# Global set for dynamically blocked commands (moved from server/core.py)
# This might be better managed within a class or specific module if state becomes complex
blacklisted_commands: Set[str] = set(DEFAULT_BLACKLIST) # Initialize with defaults

def is_command_safe(command: str) -> bool:
    """Validate if a command is safe to execute against defaults and dynamic list.
    
    Args:
        command: The command string to validate
        
    Returns:
        bool: True if the command is safe to execute, False otherwise
    """
    # 1. Check for empty command
    if not command or not command.strip():
        return False
        
    # 2. Check against exact blacklisted commands (case-sensitive)
    # Checks the combined set of defaults and dynamically added commands
    if command.strip() in blacklisted_commands:
        return False
        
    # 3. Check for dangerous patterns using regex (case-insensitive)
    # Note: Moved regex import here
    import re 
    dangerous_patterns = [
        r"rm\s+-rf\s+/",  # Remove root
        r"mkfs",          # Format filesystem
        r"dd\s+if=",      # Direct disk access
        r">\s*/dev/",     # Write to device files
        r";\s*rm\s+",     # Chained remove commands
        r"&\s*rm\s+",     # Background remove commands
        r"\|\s*rm\s+",    # Piped remove commands
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False
            
    # 4. If none of the above checks failed, the command is considered safe.
    return True

def block_command(command: str) -> None:
    """Add a command to the dynamic blacklist."""
    global blacklisted_commands
    blacklisted_commands.add(command.strip())

def unblock_command(command: str) -> None:
    """Remove a command from the dynamic blacklist."""
    global blacklisted_commands
    blacklisted_commands.discard(command.strip()) # Use discard to avoid KeyError

# --- End Command Security --- 