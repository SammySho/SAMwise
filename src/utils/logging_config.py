"""
Logging Configuration for Organoid Segmentation Application

This module sets up centralized logging for the entire application,
providing structured error reporting and debugging capabilities.
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime


def setup_logging(log_level=logging.INFO, log_to_file=True):
    """
    Set up application-wide logging configuration.
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file in addition to console
    
    Returns:
        logging.Logger: Configured root logger
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Create formatter for log messages
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console handler - only show WARNING and above to keep console clean
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    if log_to_file:
        # File handler for all log levels
        log_filename = f"organoid_segmentation_{datetime.now().strftime('%Y%m%d')}.log"
        log_filepath = log_dir / log_filename
        
        # Use RotatingFileHandler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_filepath,
            maxBytes=10*1024*1024,  # 10MB max size
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log startup message
    logger = logging.getLogger("organoid_segmentation")
    logger.info("Logging system initialized")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info(f"Log to file: {log_to_file}")
    
    return root_logger


def get_logger(name):
    """
    Get a logger instance for a specific module.
    
    Args:
        name (str): Logger name (typically __name__)
    
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)


# Default setup - can be overridden by calling setup_logging() again
setup_logging()
