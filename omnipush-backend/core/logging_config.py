#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Beautiful Logging Configuration for OmniPush Platform

This module provides a centralized logging configuration with:
- Automatic line numbers and function names
- Beautiful colorized output
- Structured formatting with emojis
- File and console handlers
"""

import logging
import sys
from datetime import datetime
from typing import Optional
import os


class ColoredFormatter(logging.Formatter):
    """Custom formatter with beautiful colors and emojis"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',      # Reset
        'BOLD': '\033[1m',       # Bold
        'DIM': '\033[2m',        # Dim
    }

    # Emoji mapping for log levels
    EMOJIS = {
        'DEBUG': '🔍',
        'INFO': '📘',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '💥',
    }

    def __init__(self, use_colors: bool = True, use_emojis: bool = True):
        self.use_colors = use_colors and hasattr(sys.stderr, 'isatty') and sys.stderr.isatty()
        self.use_emojis = use_emojis

        # Format with clickable file paths for VS Code
        # VS Code recognizes filename:line:function format as clickable links
        fmt = (
            "%(asctime)s "
            "{emoji}%(levelname)-8s{reset} "
            "{dim}%(filename)s:%(lineno)d:%(funcName)s{reset} "
            "{bold}%(message)s{reset}"
        )

        if self.use_colors:
            fmt = fmt.format(
                emoji="{emoji}",
                reset=self.COLORS['RESET'],
                dim=self.COLORS['DIM'],
                bold=self.COLORS['BOLD']
            )
        else:
            fmt = fmt.format(
                emoji="{emoji}",
                reset="",
                dim="",
                bold=""
            )

        super().__init__(fmt, datefmt='%H:%M:%S')

    def format(self, record):
        """Format the log record with colors and emojis"""
        # Add emoji to the record
        emoji = ""
        if self.use_emojis:
            emoji = self.EMOJIS.get(record.levelname, '📄') + " "

        # Add color to level name if colors are enabled
        if self.use_colors:
            level_color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{level_color}{record.levelname}{self.COLORS['RESET']}"

        # Format the base message
        formatted = super().format(record)

        # Replace emoji placeholder
        formatted = formatted.replace("{emoji}", emoji)

        return formatted


class FileFormatter(logging.Formatter):
    """Simple formatter for file output without colors"""

    def __init__(self):
        fmt = (
            "%(asctime)s [%(levelname)-8s] "
            "%(filename)s:%(lineno)d:%(funcName)s "
            "%(message)s"
        )
        super().__init__(fmt, datefmt='%Y-%m-%d %H:%M:%S')


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    use_colors: bool = True,
    use_emojis: bool = True,
    max_file_size_mb: int = 50,
    backup_count: int = 5
) -> None:
    """
    Set up beautiful logging configuration for the entire application

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        use_colors: Enable colored console output
        use_emojis: Enable emoji indicators
        max_file_size_mb: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(numeric_level)

    # Console handler with beautiful formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_formatter = ColoredFormatter(use_colors=use_colors, use_emojis=use_emojis)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        from logging.handlers import RotatingFileHandler

        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_formatter = FileFormatter()
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Set specific loggers to appropriate levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)

    # Log the setup
    logger = logging.getLogger(__name__)
    logger.info(f"🎨 Beautiful logging configured - Level: {level}")
    if log_file:
        logger.info(f"📁 Log file: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Environment-based configuration
def configure_from_environment() -> None:
    """Configure logging based on environment variables"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_file = os.getenv("LOG_FILE")
    use_colors = os.getenv("LOG_COLORS", "true").lower() == "true"
    use_emojis = os.getenv("LOG_EMOJIS", "true").lower() == "true"

    # Default log file for production
    if not log_file and os.getenv("ENVIRONMENT") == "production":
        log_file = "logs/omnipush.log"

    setup_logging(
        level=log_level,
        log_file=log_file,
        use_colors=use_colors,
        use_emojis=use_emojis
    )


# Export common logging patterns for convenience
DEBUG = "DEBUG"
INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"
CRITICAL = "CRITICAL"

# Don't auto-configure - let applications choose when to set up logging
# Applications should call setup_logging() or configure_from_environment() explicitly