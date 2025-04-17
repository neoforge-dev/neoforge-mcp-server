import pytest
from server.utils.config import ServerConfig

def test_server_config_creation():
    """Test that ServerConfig can be created with proper parameters."""
    config = ServerConfig(
        name="test_server",
        port=8001,
        api_prefix="/api/v2",  # Custom API prefix
        enable_rate_limiting=False  # Using the correct parameter name
    )
    
    # Check that the API prefix is properly set
    assert config.api_prefix == "/api/v2"
    
    # Check that rate limiting is disabled
    assert config.enable_rate_limiting is False
    
    # Check default values
    assert config.version == "1.0.0"  # Default value
    assert config.log_level == "info"  # Default value

def test_server_config_default_api_prefix():
    """Test that ServerConfig uses the default API prefix when not specified."""
    config = ServerConfig(
        name="test_server",
        port=8001
    )
    
    # Check that the API prefix uses the default value
    assert config.api_prefix == "/api/v1" 