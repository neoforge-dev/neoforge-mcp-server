import pytest_asyncio
from unittest.mock import MagicMock, patch

@pytest_asyncio.fixture
@patch("server.neod.server.NeoDevServer.load_config")
@patch("server.utils.logging.LogManager")
@patch("server.utils.security.SecurityManager")
# Patch the logger where the middleware imports it
@patch("server.utils.logging.logger")
def test_neod_server(
    mock_error_logger: MagicMock,
    mock_security_manager: MagicMock,
    mock_log_manager: MagicMock,
    mock_logger_instance: MagicMock,
    mock_config: MagicMock
):
    mock_log_manager.return_value.get_logger.return_value = mock_logger_instance

    # Mock the logger used by the ErrorHandlerMiddleware
    mock_error_logger.bind = MagicMock(return_value=mock_error_logger)  # Add mock bind method

    mock_config.return_value = neod_test_config 