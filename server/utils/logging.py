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
import structlog
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # Add process/thread info
        log_record['process'] = record.process
        log_record['process_name'] = record.processName
        log_record['thread'] = record.thread
        log_record['thread_name'] = record.threadName
        
        # Add file info
        log_record['file'] = record.filename
        log_record['line'] = record.lineno
        log_record['function'] = record.funcName

def setup_structlog():
    """Configure structlog for structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

class LogManager:
    """Manager for logging configuration."""
    
    def __init__(
        self,
        name: str,
        log_level: str = "INFO",
        log_dir: Optional[str] = None,
        log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        log_rotation: str = "D",
        log_retention: int = 7,
        enable_json: bool = True,
        enable_console: bool = True,
        enable_file: bool = True,
        enable_syslog: bool = False,
        syslog_address: Optional[str] = None,
        enable_structlog: bool = True
    ):
        """Initialize logging manager.
        
        Args:
            name: Logger name
            log_level: Logging level
            log_dir: Directory for log files
            log_format: Log format string
            log_rotation: Log rotation interval
            log_retention: Number of days to retain logs
            enable_json: Enable JSON formatting
            enable_console: Enable console logging
            enable_file: Enable file logging
            enable_syslog: Enable syslog logging
            syslog_address: Syslog server address
            enable_structlog: Enable structured logging
        """
        self.name = name
        self.log_level = getattr(logging, log_level.upper())
        self.log_dir = Path(log_dir) if log_dir else Path("logs")
        self.log_format = log_format
        self.log_rotation = log_rotation
        self.log_retention = log_retention
        self.enable_json = enable_json
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.enable_syslog = enable_syslog
        self.syslog_address = syslog_address
        self.enable_structlog = enable_structlog
        
        # Create logger
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Set up the logger with handlers."""
        # Create logger
        logger = logging.getLogger(self.name)
        logger.setLevel(self.log_level)
        
        # Remove existing handlers
        logger.handlers = []
        
        # Create formatters
        if self.enable_json:
            json_formatter = CustomJsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s'
            )
        plain_formatter = logging.Formatter(self.log_format)
        
        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(
                json_formatter if self.enable_json else plain_formatter
            )
            logger.addHandler(console_handler)
        
        # File handler
        if self.enable_file:
            # Create log directory
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            # Regular log file
            file_handler = logging.handlers.TimedRotatingFileHandler(
                self.log_dir / f"{self.name}.log",
                when=self.log_rotation,
                backupCount=self.log_retention
            )
            file_handler.setFormatter(
                json_formatter if self.enable_json else plain_formatter
            )
            logger.addHandler(file_handler)
            
            # Error log file
            error_handler = logging.handlers.TimedRotatingFileHandler(
                self.log_dir / f"{self.name}.error.log",
                when=self.log_rotation,
                backupCount=self.log_retention
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(
                json_formatter if self.enable_json else plain_formatter
            )
            logger.addHandler(error_handler)
        
        # Syslog handler
        if self.enable_syslog and self.syslog_address:
            syslog_handler = logging.handlers.SysLogHandler(
                address=self.syslog_address
            )
            syslog_handler.setFormatter(
                json_formatter if self.enable_json else plain_formatter
            )
            logger.addHandler(syslog_handler)
        
        # Configure structlog if enabled
        if self.enable_structlog:
            setup_structlog()
        
        return logger
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger."""
        return self.logger
    
    def set_level(self, level: str) -> None:
        """Set the logging level."""
        self.log_level = getattr(logging, level.upper())
        self.logger.setLevel(self.log_level)
    
    def add_handler(self, handler: logging.Handler) -> None:
        """Add a custom handler to the logger."""
        if self.enable_json:
            handler.setFormatter(CustomJsonFormatter(
                '%(timestamp)s %(level)s %(name)s %(message)s'
            ))
        else:
            handler.setFormatter(logging.Formatter(self.log_format))
        self.logger.addHandler(handler)
    
    def remove_handler(self, handler: logging.Handler) -> None:
        """Remove a handler from the logger."""
        self.logger.removeHandler(handler)
    
    def cleanup_old_logs(self) -> None:
        """Clean up old log files."""
        if not self.enable_file:
            return
            
        try:
            # Get all log files
            log_files = list(self.log_dir.glob("*.log*"))
            
            # Get current time
            now = datetime.utcnow()
            
            # Remove files older than retention period
            for log_file in log_files:
                if log_file.stat().st_mtime < (now - datetime.timedelta(days=self.log_retention)).timestamp():
                    log_file.unlink()
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up logs: {e}")
    
    def rotate_logs(self) -> None:
        """Force log rotation."""
        if not self.enable_file:
            return
            
        for handler in self.logger.handlers:
            if isinstance(handler, logging.handlers.TimedRotatingFileHandler):
                handler.doRollover()

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
            **kwargs: Additional fields for structured logging context
        """
        if args:
            msg = msg % args
            
        # Combine context and kwargs for the extra dict
        log_extra = {**self.context, **kwargs}
        
        # Pass the combined dict directly as the 'extra' argument
        # This is the standard way to add custom data to log records
        self.logger.log(level, msg, extra=log_extra)
        
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