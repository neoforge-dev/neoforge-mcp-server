#!/usr/bin/env python3
"""
Integration Test for MCP Browser

This script tests the integration of the browser pool, error handling,
and authentication components.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger("test_integration")

# Import components
try:
    from browser_pool import BrowserPool
    from error_handler import ErrorCode, MCPBrowserException, with_retry, handle_exceptions
    from integration import BrowserManager, AuthManager, User
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    logger.info("Make sure you are running this script from the correct directory and have installed all dependencies.")
    sys.exit(1)


async def test_browser_pool():
    """Test the browser pool component."""
    logger.info("=== Testing BrowserPool ===")
    
    try:
        # Initialize browser pool
        pool = BrowserPool(max_instances=3, idle_timeout=60)
        await pool.start()
        logger.info("BrowserPool initialized successfully")
        
        # Get browser instance
        instance_id = await pool.get_browser_instance()
        logger.info(f"Got browser instance: {instance_id}")
        
        # Create browser context
        context_id = await pool.create_browser_context(instance_id, {"test": "data"})
        logger.info(f"Created browser context: {context_id}")
        
        # Get context data
        context_data = await pool.get_context_data(instance_id, context_id)
        logger.info(f"Context data: {context_data}")
        assert context_data == {"test": "data"}, "Context data mismatch"
        
        # Get instances info
        instances = await pool.get_all_instances()
        logger.info(f"Browser instances: {instances}")
        assert len(instances) == 1, "Expected 1 browser instance"
        
        # Release and reuse instance
        await pool.close_browser_context(instance_id, context_id)
        await pool.release_browser_instance(instance_id)
        logger.info("Released browser instance")
        
        # Get same instance again
        instance_id2 = await pool.get_browser_instance()
        logger.info(f"Got browser instance again: {instance_id2}")
        assert instance_id == instance_id2, "Expected same instance ID"
        
        # Clean up
        await pool.stop()
        logger.info("Stopped browser pool")
        
        logger.info("✅ BrowserPool test passed")
        
    except Exception as e:
        logger.error(f"BrowserPool test failed: {e}")
        raise


async def test_error_handler():
    """Test the error handling component."""
    logger.info("=== Testing ErrorHandler ===")
    
    try:
        # Test creating exception
        ex = MCPBrowserException(
            error_code=ErrorCode.TIMEOUT,
            message="Operation timed out",
            details={"operation": "test"}
        )
        response = ex.to_error_response()
        logger.info(f"Error response: {response}")
        assert response.error.code == "TIMEOUT", "Error code mismatch"
        assert response.error.message == "Operation timed out", "Error message mismatch"
        
        # Test error code to HTTP status mapping
        http_ex = ex.to_http_exception()
        logger.info(f"HTTP exception: {http_ex}")
        assert http_ex["status_code"] == 504, "Expected HTTP status 504 for TIMEOUT"
        
        # Test retry mechanism
        retry_count = 0
        
        @with_retry()
        async def flaky_function():
            nonlocal retry_count
            retry_count += 1
            if retry_count < 3:
                raise MCPBrowserException(
                    error_code=ErrorCode.NETWORK_ERROR,
                    message=f"Network error (attempt {retry_count})"
                )
            return "Success after retries"
        
        result = await flaky_function()
        logger.info(f"Retry result: {result}")
        assert retry_count == 3, f"Expected 3 attempts, got {retry_count}"
        assert result == "Success after retries", "Retry result mismatch"
        
        # Test exception handling decorator
        @handle_exceptions
        async def handler_test(should_fail: bool):
            if should_fail:
                raise ValueError("Test error")
            return {"success": True, "data": "test"}
        
        success_result = await handler_test(False)
        logger.info(f"Handler success result: {success_result}")
        assert success_result["success"] is True, "Handler success result mismatch"
        
        error_result = await handler_test(True)
        logger.info(f"Handler error result: {error_result}")
        assert error_result.success is False, "Handler error result should indicate failure"
        assert error_result.error.code == "INTERNAL_ERROR", "Handler error code mismatch"
        
        logger.info("✅ ErrorHandler test passed")
        
    except Exception as e:
        logger.error(f"ErrorHandler test failed: {e}")
        raise


async def test_integration():
    """Test the integration component."""
    logger.info("=== Testing Integration ===")
    
    try:
        # Initialize browser manager
        browser_manager = BrowserManager(max_instances=3, idle_timeout=60)
        await browser_manager.initialize()
        logger.info("BrowserManager initialized successfully")
        
        # Create browser context
        context = await browser_manager.create_browser_context("test_user")
        logger.info(f"Created browser context: {context}")
        assert "instance_id" in context, "Missing instance_id in context"
        assert "context_id" in context, "Missing context_id in context"
        
        # Get browser context
        instance_id = context["instance_id"]
        context_id = context["context_id"]
        context_data = await browser_manager.get_browser_context(instance_id, context_id)
        logger.info(f"Context data: {context_data}")
        assert context_data["user_id"] == "test_user", "Context user_id mismatch"
        
        # Close browser context
        await browser_manager.close_browser_context(instance_id, context_id)
        logger.info("Closed browser context")
        
        # Shut down browser manager
        await browser_manager.shutdown()
        logger.info("Shut down browser manager")
        
        # Test auth manager
        # Get user
        user = AuthManager.get_user("admin")
        logger.info(f"Got user: {user}")
        assert user.username == "admin", "User username mismatch"
        assert "admin:read" in user.permissions, "User permissions mismatch"
        
        # Create tokens
        access_token = AuthManager.create_access_token({"sub": user.username})
        refresh_token = AuthManager.create_refresh_token({"sub": user.username})
        logger.info(f"Created tokens: access={access_token[:10]}..., refresh={refresh_token[:10]}...")
        
        # Decode token
        payload = AuthManager.decode_token(access_token)
        logger.info(f"Decoded token payload: {payload}")
        assert payload["sub"] == "admin", "Token subject mismatch"
        assert payload["type"] == "access", "Token type mismatch"
        
        # Test password verification (mock)
        verified = AuthManager.verify_password("secret", user.hashed_password)
        logger.info(f"Password verification result: {verified}")
        assert verified is True, "Password verification failed"
        
        # Test permission check
        admin_has_permission = "admin:read" in user.permissions
        logger.info(f"Admin has admin:read permission: {admin_has_permission}")
        assert admin_has_permission is True, "Permission check failed"
        
        logger.info("✅ Integration test passed")
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        raise


async def main():
    """Run all integration tests."""
    logger.info("Starting integration tests")
    
    try:
        # Test each component
        await test_browser_pool()
        await test_error_handler()
        await test_integration()
        
        logger.info("✅ All tests passed")
        return 0
    except Exception as e:
        logger.error(f"Integration tests failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 