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
        key_length: int = 32,
        hash_iterations: int = 100000,
        rate_limit: int = 100,
        rate_limit_window: int = 60
    ):
        """Initialize security manager.
        
        Args:
            secret_key: Secret key for signing
            key_length: Length of generated keys
            hash_iterations: Number of hash iterations
            rate_limit: Maximum requests per window
            rate_limit_window: Time window in seconds
        """
        self.secret_key = secret_key or os.urandom(32)
        self.key_length = key_length
        self.hash_iterations = hash_iterations
        
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
        """Validate API key.
        
        Args:
            key: API key to validate
            
        Returns:
            ApiKey if valid
            
        Raises:
            SecurityError if invalid
        """
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
            
            # Look up key
            api_key = self.api_keys.get(key_id)
            if not api_key:
                raise SecurityError(
                    "Invalid API key",
                    details={"key_id": key_id}
                )
                
            # Check if expired
            if api_key.is_expired():
                raise SecurityError(
                    "Expired API key",
                    details={"key_id": key_id}
                )
                
            # Verify hash
            if not hmac.compare_digest(api_key.key_hash, key_hash):
                raise SecurityError(
                    "Invalid API key",
                    details={"key_id": key_id}
                )
                
            return api_key
            
        except Exception as e:
            raise SecurityError(
                "Failed to validate API key",
                details={"error": str(e)}
            )
            
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