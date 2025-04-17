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
from datetime import datetime, timedelta
from jose import jwt
import uuid
import redis
from fastapi.security import APIKeyHeader

@dataclass
class ApiKey:
    """API key with metadata."""
    
    # Key details
    key_id: str
    hashed_key: str
    name: str
    roles: List[str]
    rate_limit: str
    
    # Key metadata
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    
    def is_expired(self) -> bool:
        """Check if key is expired."""
        return (
            self.expires_at is not None
            and datetime.utcnow() > self.expires_at
        )
        
    def has_role(self, role: str) -> bool:
        """Check if key has role."""
        return role in self.roles
        
    def has_scope(self, scope: str) -> bool:
        """Check if key has scope."""
        return scope in self.roles

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
        redis_url: str = "redis://localhost:6379/0",
        jwt_secret: str = None,
        api_keys: Optional[Dict[str, Dict[str, Any]]] = None,
        enable_auth: bool = True,
        auth_token: Optional[str] = None,
        rate_limit_window: int = 60,  # 1 minute
        rate_limit_max_requests: int = 100,  # 100 requests per minute
        blocked_ips: Optional[Set[str]] = None
    ):
        """Initialize security manager."""
        self.redis = redis.from_url(redis_url)
        self.jwt_secret = jwt_secret or secrets.token_hex(32)
        self.enable_auth = enable_auth
        self.auth_token = auth_token
        self.rate_limit_window = rate_limit_window
        self.rate_limit_max_requests = rate_limit_max_requests
        self.blocked_ips = blocked_ips or set()
        
        # Initialize API keys
        self._init_api_keys(api_keys or {})
        
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
        
    def check_rate_limit(self, api_key: str, client_ip: str) -> bool:
        """Check if request is within rate limits."""
        if client_ip in self.blocked_ips:
            raise SecurityError(
                message="IP address is blocked",
                details={"code": ErrorCode.SECURITY_ERROR}
            )
            
        # Validate key and get rate limit
        key_data = self.validate_api_key(api_key)
        rate_limit = key_data.rate_limit
        
        # Parse rate limit
        try:
            limit, period = rate_limit.split("/")
            limit = int(limit)
            if period == "second":
                window = 1
            elif period == "minute":
                window = 60
            elif period == "hour":
                window = 3600
            else:
                window = 86400  # day
        except (ValueError, KeyError):
            # Default to global rate limit
            limit = self.rate_limit_max_requests
            window = self.rate_limit_window
            
        # Check rate limit in Redis
        key = f"ratelimit:{key_data.key_id}:{int(datetime.utcnow().timestamp() / window)}"
        current = self.redis.incr(key)
        if current == 1:
            self.redis.expire(key, window)
            
        return current <= limit
        
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
        
    def _init_api_keys(self, api_keys: Dict[str, Dict[str, Any]]) -> None:
        """Initialize API keys in Redis."""
        for key_id, key_data in api_keys.items():
            # Hash the API key
            api_key = key_data.get("key")
            if not api_key:
                continue
                
            hashed_key = self._hash_key(api_key)
            
            # Create API key object
            key_obj = ApiKey(
                key_id=key_id,
                hashed_key=hashed_key,
                name=key_data.get("name", ""),
                roles=key_data.get("roles", []),
                rate_limit=key_data.get("rate_limit", f"{self.rate_limit_max_requests}/minute"),
                created_at=datetime.utcnow(),
                expires_at=None if key_data.get("never_expires", False) else 
                    datetime.utcnow() + timedelta(days=key_data.get("expires_in_days", 365)),
                is_active=key_data.get("is_active", True)
            )
            
            # Store in Redis
            self.redis.hset(
                f"api_key:{key_id}",
                mapping={
                    "hashed_key": key_obj.hashed_key,
                    "name": key_obj.name,
                    "roles": ",".join(key_obj.roles),
                    "rate_limit": key_obj.rate_limit,
                    "created_at": key_obj.created_at.isoformat(),
                    "expires_at": key_obj.expires_at.isoformat() if key_obj.expires_at else "",
                    "is_active": "1" if key_obj.is_active else "0"
                }
            )
    
    def _hash_key(self, key: str) -> str:
        """Hash an API key."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def create_api_key(
        self,
        name: str,
        roles: List[str],
        rate_limit: Optional[str] = None,
        expires_in_days: Optional[int] = 365,
        never_expires: bool = False
    ) -> Dict[str, str]:
        """Create a new API key."""
        # Generate key ID and key
        key_id = str(uuid.uuid4())
        api_key = secrets.token_urlsafe(32)
        
        # Create and store key object
        key_obj = ApiKey(
            key_id=key_id,
            hashed_key=self._hash_key(api_key),
            name=name,
            roles=roles,
            rate_limit=rate_limit or f"{self.rate_limit_max_requests}/minute",
            created_at=datetime.utcnow(),
            expires_at=None if never_expires else datetime.utcnow() + timedelta(days=expires_in_days),
            is_active=True
        )
        
        # Store in Redis
        self.redis.hset(
            f"api_key:{key_id}",
            mapping={
                "hashed_key": key_obj.hashed_key,
                "name": key_obj.name,
                "roles": ",".join(key_obj.roles),
                "rate_limit": key_obj.rate_limit,
                "created_at": key_obj.created_at.isoformat(),
                "expires_at": key_obj.expires_at.isoformat() if key_obj.expires_at else "",
                "is_active": "1"
            }
        )
        
        return {
            "key_id": key_id,
            "api_key": api_key
        }
    
    def validate_api_key(self, api_key: str) -> ApiKey:
        """Validate an API key and return key data."""
        if not api_key:
            raise SecurityError(
                message="API key is required",
                details={"code": ErrorCode.API_KEY_ERROR}
            )
            
        # Hash the provided key
        hashed_key = self._hash_key(api_key)
        
        # Search for matching key in Redis
        for key in self.redis.scan_iter("api_key:*"):
            key_data = self.redis.hgetall(key)
            if key_data.get("hashed_key") == hashed_key:
                # Check if key is active
                if key_data.get("is_active") != "1":
                    raise SecurityError(
                        message="API key is inactive",
                        details={"code": ErrorCode.API_KEY_ERROR}
                    )
                
                # Check expiration
                expires_at = key_data.get("expires_at")
                if expires_at and expires_at != "":
                    expiry = datetime.fromisoformat(expires_at)
                    if expiry < datetime.utcnow():
                        raise SecurityError(
                            message="API key has expired",
                            details={"code": ErrorCode.API_KEY_ERROR}
                        )
                
                # Return key data
                return ApiKey(
                    key_id=key.decode().split(":")[1],
                    hashed_key=key_data["hashed_key"],
                    name=key_data["name"],
                    roles=key_data["roles"].split(","),
                    rate_limit=key_data["rate_limit"],
                    created_at=datetime.fromisoformat(key_data["created_at"]),
                    expires_at=datetime.fromisoformat(key_data["expires_at"]) if key_data["expires_at"] else None,
                    is_active=key_data["is_active"] == "1"
                )
        
        raise SecurityError(
            message="Invalid API key",
            details={"code": ErrorCode.API_KEY_ERROR}
        )
        
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
        if "*:*" in api_key.roles:
            return True
            
        # Check for specific permission
        if permission in api_key.roles:
            return True
            
        # Check for wildcard namespace
        namespace = permission.split(":")[0]
        if f"{namespace}:*" in api_key.roles:
            return True

        # Check permissions granted by the key's roles
        for role_name in api_key.roles:
            if role_name in self.roles:  # Check if the role exists in the manager's config
                role_scopes = self.roles[role_name]
                # Check for wildcard scope in the role definition
                if "*" in role_scopes or "*:*" in role_scopes: # Check role's global wildcard
                     return True
                # Check for exact scope match in the role definition
                if permission in role_scopes:
                    return True
                # Check for namespace wildcard scope in the role definition
                if f"{namespace}:*" in role_scopes:
                    return True

        # No matching scope found directly or via roles
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
        """Revoke an API key."""
        key = f"api_key:{key_id}"
        if not self.redis.exists(key):
            raise SecurityError(
                message="API key not found",
                details={"code": ErrorCode.API_KEY_ERROR}
            )
            
        self.redis.hset(key, "is_active", "0")
        
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List all API keys.
        
        Returns:
            List of API key information
        """
        keys = []
        for key_id, api_key in self.redis.hscan_iter("api_key:*"):
            key_data = self.redis.hgetall(key_id)
            keys.append({
                'key_id': key_id.decode(),
                'name': key_data["name"].decode(),
                'created_at': datetime.fromisoformat(key_data["created_at"].decode()),
                'expires_at': datetime.fromisoformat(key_data["expires_at"].decode()) if key_data["expires_at"] else None,
                'roles': [role.decode() for role in key_data["roles"].split(",")],
                'rate_limit': key_data["rate_limit"].decode(),
                'expired': api_key.decode() == "0" or self.check_rate_limit(key_id.decode(), "")
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
        return self.validate_api_key(api_key)

    def block_ip(self, ip: str) -> None:
        """Block an IP address."""
        self.blocked_ips.add(ip)
        self.redis.sadd("blocked_ips", ip)
    
    def unblock_ip(self, ip: str) -> None:
        """Unblock an IP address."""
        self.blocked_ips.discard(ip)
        self.redis.srem("blocked_ips", ip)
    
    def create_jwt_token(self, key_id: str, expires_in: int = 3600) -> str:
        """Create a JWT token for an API key."""
        key_data = self.redis.hgetall(f"api_key:{key_id}")
        if not key_data:
            raise SecurityError(
                message="API key not found",
                details={"code": ErrorCode.API_KEY_ERROR}
            )
            
        payload = {
            "sub": key_id,
            "name": key_data["name"],
            "roles": key_data["roles"].split(","),
            "exp": datetime.utcnow() + timedelta(seconds=expires_in)
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def validate_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate a JWT token."""
        try:
            return jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        except jwt.InvalidTokenError as e:
            raise SecurityError(
                message="Invalid JWT token",
                details={"code": ErrorCode.TOKEN_ERROR, "error": str(e)}
            )

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