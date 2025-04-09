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
from .error_handling import SecurityError

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
        secret_key: Optional[str] = None,
        config_api_keys: Optional[Dict[str, Any]] = None,
        key_length: int = 32,
        hash_iterations: int = 100000,
        rate_limit: int = 100,
        rate_limit_window: int = 60
    ):
        """Initialize security manager.
        
        Args:
            secret_key: Secret key for signing
            config_api_keys: API keys loaded from configuration files
            key_length: Length of generated keys
            hash_iterations: Number of hash iterations
            rate_limit: Maximum requests per window
            rate_limit_window: Time window in seconds
        """
        self.secret_key = secret_key or os.urandom(32)
        self.key_length = key_length
        self.hash_iterations = hash_iterations
        self.config_api_keys = config_api_keys or {}
        
        # Store API keys
        self.api_keys: Dict[str, ApiKey] = {}
        
        # Role definitions
        self.roles: Dict[str, Set[str]] = {
            'admin': {'*'},  # Admin has all permissions
            'user': {
                'read:*',
                'write:own'
            }
        }
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(rate_limit, rate_limit_window)
        
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
        key = secrets.token_urlsafe(self.key_length)
        
        # Hash key
        key_hash = hashlib.pbkdf2_hmac(
            'sha256',
            key.encode(),
            self.secret_key,
            self.hash_iterations
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
        
    def validate_api_key(self, key: str) -> ApiKey:
        """Validate API key against internal and config keys.
        
        Args:
            key: API key to validate
            
        Returns:
            ApiKey if valid
            
        Raises:
            SecurityError if invalid
        """
        # 1. Try validating against internally generated/hashed keys
        try:
            # Hash key
            key_hash = hashlib.pbkdf2_hmac(
                'sha256',
                key.encode(),
                self.secret_key,
                self.hash_iterations
            ).hex()
            
            # Get key ID
            key_id = hashlib.sha256(key_hash.encode()).hexdigest()[:8]
            
            # Look up key in internal store
            api_key = self.api_keys.get(key_id)
            if not api_key:
                 # Key not found in internal store, will proceed to check config keys
                 raise SecurityError("Key not found in internal store", details={"key_id": key_id})

            # Check hash match
            if not hmac.compare_digest(api_key.key_hash, key_hash):
                 raise SecurityError("Invalid API key hash", details={"key_id": key_id})
                 
            # Check expiration
            if api_key.is_expired():
                 raise SecurityError("API key expired", details={"key_id": key_id})
                 
            return api_key # Valid internal key found

        except SecurityError as internal_error:
            # 2. If not found/invalid in internal store, check config keys
            if key in self.config_api_keys:
                config_key_data = self.config_api_keys[key]
                if isinstance(config_key_data, dict):
                    permissions = config_key_data.get('permissions', [])
                    # Assuming permissions in config are equivalent to scopes for now
                    # Create a temporary ApiKey object for this request
                    # Note: No proper hash or expiration check possible here
                    return ApiKey(
                        key_id=key, # Use the key itself as ID
                        key_hash="config_key", # Placeholder hash
                        name=f"Config Key: {key}",
                        created_at=time.time(),
                        scopes=set(permissions)
                    )
                else:
                     # Handle cases where the config value isn't a dictionary (unexpected)
                     pass # Or log a warning

            # If key not found in internal keys OR config keys, raise error
            # Raise the original internal error if it occurred, otherwise a generic invalid key error
            # raise internal_error # Option 1: Re-raise original
            raise SecurityError(f"Invalid API key: {key}") # Option 2: Generic error
            
    def check_permission(
        self,
        api_key: ApiKey,
        required_scope: str
    ) -> bool:
        """Check if API key has required permission.
        
        Args:
            api_key: API key to check
            required_scope: Required permission scope
            
        Returns:
            True if permitted
        """
        # Check for universal scope first
        if api_key.has_scope("*:*") or api_key.has_scope("*"):
             return True
             
        # Check direct scope
        if api_key.has_scope(required_scope):
            return True
            
        # Check wildcard scopes
        parts = required_scope.split(':')
        for i in range(len(parts)):
            wildcard = ':'.join(parts[:i] + ['*'])
            if api_key.has_scope(wildcard):
                return True
                
        # Check role permissions
        for role in api_key.roles:
            role_scopes = self.roles.get(role, set())
            if '*' in role_scopes:
                return True
            if required_scope in role_scopes:
                return True
            # Check role wildcard scopes
            for scope in role_scopes:
                if scope.endswith('*') and required_scope.startswith(scope[:-1]):
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
        
    def revoke_api_key(self, key_id: str) -> None:
        """Revoke API key.
        
        Args:
            key_id: ID of key to revoke
        """
        self.api_keys.pop(key_id, None)
        
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