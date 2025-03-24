#!/usr/bin/env python3
"""
Integration Module for MCP Browser

This module integrates the BrowserPool, error handling, and authentication
components for the MCP Browser application.
"""

import os
import logging
import asyncio
import time
import uuid
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any
from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel

from browser_pool import BrowserPool
from error_handler import ErrorCode, MCPBrowserException, handle_exceptions, with_retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("integration")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development_secret_key")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# User models
class User(BaseModel):
    """User model for authentication."""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    permissions: List[str] = []


class UserInDB(User):
    """User model with hashed password for storage."""
    hashed_password: str


# Fake user database for demonstration
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "disabled": False,
        "permissions": ["admin:read", "admin:write", "browser:control"]
    },
    "user": {
        "username": "user",
        "full_name": "Regular User",
        "email": "user@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
        "disabled": False,
        "permissions": ["browser:read"]
    }
}


class BrowserManager:
    """
    Manages browser resources using the BrowserPool.
    
    This class provides a high-level interface for browser operations,
    integrating with error handling and resource management.
    """
    
    def __init__(self, max_instances: int = 5, idle_timeout: float = 300):
        """Initialize the browser manager with a browser pool."""
        self.browser_pool = BrowserPool(max_instances=max_instances, idle_timeout=idle_timeout)
        self.initialized = False
        logger.info("BrowserManager initialized")
    
    async def initialize(self) -> None:
        """Initialize the browser manager and start the browser pool."""
        if not self.initialized:
            await self.browser_pool.start()
            self.initialized = True
            logger.info("BrowserManager started")
    
    async def shutdown(self) -> None:
        """Shutdown the browser manager and clean up resources."""
        if self.initialized:
            await self.browser_pool.stop()
            self.initialized = False
            logger.info("BrowserManager stopped")
    
    @with_retry()
    async def create_browser_context(self, user_id: str) -> Dict[str, str]:
        """
        Create a new browser context for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            Dictionary with browser instance and context IDs
        """
        try:
            instance_id = await self.browser_pool.get_browser_instance()
            context_data = {"user_id": user_id, "created_at": time.time()}
            context_id = await self.browser_pool.create_browser_context(instance_id, context_data)
            
            logger.info(f"Created browser context {context_id} for user {user_id}")
            return {
                "instance_id": instance_id,
                "context_id": context_id
            }
        except Exception as e:
            logger.error(f"Failed to create browser context: {str(e)}")
            raise MCPBrowserException(
                error_code=ErrorCode.CONTEXT_CREATION_FAILED,
                message=f"Failed to create browser context: {str(e)}"
            )
    
    async def get_browser_context(self, instance_id: str, context_id: str) -> Optional[Dict]:
        """
        Get data for a browser context.
        
        Args:
            instance_id: The ID of the browser instance
            context_id: The ID of the browser context
            
        Returns:
            Context data or None if not found
        """
        context_data = await self.browser_pool.get_context_data(instance_id, context_id)
        if not context_data:
            logger.warning(f"Browser context {context_id} not found")
            return None
        
        return context_data
    
    async def close_browser_context(self, instance_id: str, context_id: str) -> None:
        """
        Close a browser context.
        
        Args:
            instance_id: The ID of the browser instance
            context_id: The ID of the browser context
        """
        await self.browser_pool.close_browser_context(instance_id, context_id)
        await self.browser_pool.release_browser_instance(instance_id)
        logger.info(f"Closed browser context {context_id}")


class AuthManager:
    """
    Manages authentication and token handling.
    
    This class provides functionality for creating, validating, and
    refreshing JWT tokens for user authentication.
    """
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """
        Get password hash (dummy implementation).
        
        In a real application, this would use a proper password hashing algorithm.
        
        Args:
            password: The password to hash
            
        Returns:
            Hashed password
        """
        return f"$2b$12${password}"
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password (dummy implementation).
        
        In a real application, this would verify the password against the hash.
        
        Args:
            plain_password: The plain text password
            hashed_password: The hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        # This is a dummy implementation for demonstration
        # In a real application, you would use a proper password verification
        return True
    
    @staticmethod
    def get_user(username: str) -> Optional[UserInDB]:
        """
        Get user from database.
        
        Args:
            username: The username to look up
            
        Returns:
            User object or None if not found
        """
        if username in fake_users_db:
            user_dict = fake_users_db[username]
            return UserInDB(**user_dict)
        return None
    
    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User]:
        """
        Authenticate a user.
        
        Args:
            username: The username to authenticate
            password: The password to verify
            
        Returns:
            User object if authentication succeeds, None otherwise
        """
        user = AuthManager.get_user(username)
        if not user:
            return None
        if not AuthManager.verify_password(password, user.hashed_password):
            return None
        return User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            permissions=user.permissions
        )
    
    @staticmethod
    def create_access_token(data: Dict) -> str:
        """
        Create a new access token.
        
        Args:
            data: The data to encode in the token
            
        Returns:
            JWT access token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict) -> str:
        """
        Create a new refresh token.
        
        Args:
            data: The data to encode in the token
            
        Returns:
            JWT refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Dict:
        """
        Decode a JWT token.
        
        Args:
            token: The token to decode
            
        Returns:
            Decoded token data
            
        Raises:
            MCPBrowserException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise MCPBrowserException(
                error_code=ErrorCode.TOKEN_EXPIRED,
                message="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise MCPBrowserException(
                error_code=ErrorCode.INVALID_TOKEN,
                message="Invalid token"
            )
    
    @staticmethod
    async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
        """
        Get the current user from a token.
        
        Args:
            token: The JWT token
            
        Returns:
            User object
            
        Raises:
            HTTPException: If token is invalid or user not found
        """
        try:
            payload = AuthManager.decode_token(token)
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials"
                )
            token_type = payload.get("type")
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        
        user = AuthManager.get_user(username)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            permissions=user.permissions
        )
    
    @staticmethod
    async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
        """
        Check if the current user is active.
        
        Args:
            current_user: The current user
            
        Returns:
            User object if active
            
        Raises:
            HTTPException: If user is disabled
        """
        if current_user.disabled:
            raise HTTPException(status_code=400, detail="Inactive user")
        return current_user
    
    @staticmethod
    def check_permission(required_permission: str):
        """
        Dependency for checking user permissions.
        
        Args:
            required_permission: The permission required for access
            
        Returns:
            Dependency function
        """
        async def check_user_permission(current_user: User = Depends(AuthManager.get_current_active_user)):
            if required_permission not in current_user.permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {required_permission} required"
                )
            return current_user
        return check_user_permission


# FastAPI app configuration
def configure_app(app: FastAPI, browser_manager: BrowserManager) -> None:
    """
    Configure FastAPI app with startup and shutdown events.
    
    Args:
        app: The FastAPI application
        browser_manager: The browser manager instance
    """
    @app.on_event("startup")
    async def startup_event():
        """Initialize resources on startup."""
        logger.info("Starting application")
        await browser_manager.initialize()
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up resources on shutdown."""
        logger.info("Shutting down application")
        await browser_manager.shutdown() 