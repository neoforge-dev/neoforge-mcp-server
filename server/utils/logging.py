"""
Shared logging utilities for MCP servers.
"""

import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union
from .error_handling import MCPError

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = '%'
    ):
        """Initialize JSON formatter.
        
        Args:
            fmt: Format string
            datefmt: Date format string
            style: Format style
        """
        super().__init__(fmt, datefmt, style)
        self.validate = True
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Get basic record attributes
        data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
            
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            data.update(record.extra_fields)
            
        try:
            return json.dumps(data)
        except Exception as e:
            return json.dumps({
                'timestamp': datetime.now().isoformat(),
                'level': 'ERROR',
                'message': 'Failed to format log record as JSON',
                'error': str(e)
            })

class LogManager:
    """Manages logging setup and configuration."""
    
    def __init__(
        self,
        name: str,
        log_dir: Union[str, Path] = "logs",
        log_level: Union[str, int] = logging.INFO,
        max_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        json_format: bool = True,
        console_output: bool = True
    ):
        """Initialize log manager.
        
        Args:
            name: Logger name
            log_dir: Directory for log files
            log_level: Logging level
            max_size: Maximum log file size in bytes
            backup_count: Number of backup files to keep
            json_format: Whether to use JSON formatting
            console_output: Whether to output to console
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_level = log_level
        self.max_size = max_size
        self.backup_count = backup_count
        self.json_format = json_format
        self.console_output = console_output
        
        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        
        # Remove existing handlers
        self.logger.handlers = []
        
        # Setup handlers
        self._setup_handlers()
        
    def _setup_handlers(self) -> None:
        """Setup log handlers."""
        # Create formatters
        if self.json_format:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
        # File handler
        if self.log_dir:
            # Create log directory if it doesn't exist
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # Create log file path
            log_file = self.log_dir / f"{self.name}.log"
            
            # Create parent directory if it doesn't exist
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file handler
            file_handler = logging.handlers.RotatingFileHandler(
                str(log_file),  # Convert to string to avoid Path issues
                maxBytes=self.max_size,
                backupCount=self.backup_count,
                encoding='utf-8'  # Explicitly set encoding
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        # Console handler
        if self.console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
    def get_logger(self) -> logging.Logger:
        """Get configured logger.
        
        Returns:
            Configured logging.Logger instance
        """
        return self.logger
        
    def set_level(self, level: Union[str, int]) -> None:
        """Set logging level.
        
        Args:
            level: New logging level
        """
        self.logger.setLevel(level)
        
    def add_context(self, **kwargs: Any) -> None:
        """Add context fields to all log messages.
        
        Args:
            **kwargs: Context fields to add
        """
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args: Any, **kwargs2: Any) -> logging.LogRecord:
            record = old_factory(*args, **kwargs2)
            record.extra_fields = kwargs
            return record
            
        logging.setLogRecordFactory(record_factory)
        
class StructuredLogger:
    """Logger that supports structured logging with context."""
    
    def __init__(self, logger: logging.Logger):
        """Initialize structured logger.
        
        Args:
            logger: Base logger to wrap
        """
        self.logger = logger
        self.context: Dict[str, Any] = {}
        
    def with_context(self, **kwargs: Any) -> 'StructuredLogger':
        """Create new logger with additional context.
        
        Args:
            **kwargs: Context fields to add
            
        Returns:
            New StructuredLogger with updated context
        """
        new_logger = StructuredLogger(self.logger)
        new_logger.context = {**self.context, **kwargs}
        return new_logger
        
    def _log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log message with context.
        
        Args:
            level: Log level
            msg: Message to log
            *args: Format args
            **kwargs: Additional fields
        """
        if args:
            msg = msg % args
            
        extra = {'extra_fields': {**self.context, **kwargs}}
        self.logger.log(level, msg, extra=extra)
        
    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self._log(logging.DEBUG, msg, *args, **kwargs)
        
    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._log(logging.INFO, msg, *args, **kwargs)
        
    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._log(logging.WARNING, msg, *args, **kwargs)
        
    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._log(logging.ERROR, msg, *args, **kwargs)
        
    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message."""
        self._log(logging.CRITICAL, msg, *args, **kwargs)
        
    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception message."""
        kwargs.setdefault('exc_info', True)
        self._log(logging.ERROR, msg, *args, **kwargs) 