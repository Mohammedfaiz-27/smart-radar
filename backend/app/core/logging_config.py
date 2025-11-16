"""
Logging configuration for SMART RADAR MVP
Provides centralized logging setup for all components including collectors
"""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path


def setup_logging(app_name: str = "smart_radar", log_level: str = "DEBUG"):
    """
    Setup comprehensive logging configuration
    
    Args:
        app_name: Name of the application for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.DEBUG)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)-25s | %(levelname)-8s | %(funcName)-20s:%(lineno)-4d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    # Console Handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Main application log file
    main_log_file = log_dir / f"{app_name}.log"
    main_handler = logging.handlers.RotatingFileHandler(
        main_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    main_handler.setLevel(numeric_level)
    main_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(main_handler)
    
    # Collectors-specific log file
    collectors_log_file = log_dir / "collectors.log"
    collectors_handler = logging.handlers.RotatingFileHandler(
        collectors_log_file,
        maxBytes=20*1024*1024,  # 20MB for collectors (more verbose)
        backupCount=10,
        encoding='utf-8'
    )
    collectors_handler.setLevel(logging.DEBUG)
    collectors_handler.setFormatter(detailed_formatter)
    
    # Add filter to only log collector messages to this file
    class CollectorFilter(logging.Filter):
        def filter(self, record):
            return record.name.startswith('collector.')
    
    collectors_handler.addFilter(CollectorFilter())
    root_logger.addHandler(collectors_handler)
    
    # Celery-specific log file
    celery_log_file = log_dir / "celery.log"
    celery_handler = logging.handlers.RotatingFileHandler(
        celery_log_file,
        maxBytes=15*1024*1024,  # 15MB
        backupCount=7,
        encoding='utf-8'
    )
    celery_handler.setLevel(logging.DEBUG)
    celery_handler.setFormatter(detailed_formatter)
    
    # Add filter for Celery-related logs
    class CeleryFilter(logging.Filter):
        def filter(self, record):
            return any(keyword in record.name.lower() for keyword in 
                      ['celery', 'task', 'worker', 'beat', 'schedule'])
    
    celery_handler.addFilter(CeleryFilter())
    root_logger.addHandler(celery_handler)
    
    # API-specific log file
    api_log_file = log_dir / "api.log"
    api_handler = logging.handlers.RotatingFileHandler(
        api_log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    api_handler.setLevel(logging.INFO)
    api_handler.setFormatter(detailed_formatter)
    
    # Add filter for API-related logs
    class APIFilter(logging.Filter):
        def filter(self, record):
            return any(keyword in record.name.lower() for keyword in 
                      ['uvicorn', 'fastapi', 'api', 'endpoint', 'router'])
    
    api_handler.addFilter(APIFilter())
    root_logger.addHandler(api_handler)
    
    # Error-only log file
    error_log_file = log_dir / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    setup_collector_loggers()
    setup_external_library_loggers()
    
    # Log the initialization
    logger = logging.getLogger(__name__)
    logger.info(f"🔧 Logging initialized for {app_name}")
    logger.info(f"📁 Log directory: {log_dir}")
    logger.info(f"📊 Log level: {log_level}")
    logger.debug(f"🗃️ Log files created:")
    logger.debug(f"   • Main: {main_log_file}")
    logger.debug(f"   • Collectors: {collectors_log_file}")
    logger.debug(f"   • Celery: {celery_log_file}")
    logger.debug(f"   • API: {api_log_file}")
    logger.debug(f"   • Errors: {error_log_file}")


def setup_collector_loggers():
    """Configure specific loggers for each collector"""
    collector_names = [
        'collector.basecollector',
        'collector.facebookcollector', 
        'collector.xcollector',
        'collector.youtubecollector',
        'collector.googlenewscollector'
    ]
    
    for collector_name in collector_names:
        logger = logging.getLogger(collector_name)
        logger.setLevel(logging.DEBUG)
        # Don't propagate to avoid duplicate logs
        logger.propagate = True


def setup_external_library_loggers():
    """Configure logging for external libraries"""
    # Reduce noise from external libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Keep important logs from these
    logging.getLogger('celery').setLevel(logging.INFO)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)


def create_daily_log_file(component: str) -> str:
    """
    Create a daily log file path for a specific component
    
    Args:
        component: Name of the component (e.g., 'data_collection', 'threat_monitoring')
        
    Returns:
        Path to the daily log file
    """
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y-%m-%d")
    daily_log_file = log_dir / f"{component}_{today}.log"
    
    return str(daily_log_file)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


# Convenience function for collectors
def get_collector_logger(collector_class_name: str) -> logging.Logger:
    """
    Get a logger specifically for a collector
    
    Args:
        collector_class_name: Name of the collector class
        
    Returns:
        Configured collector logger
    """
    logger_name = f"collector.{collector_class_name.lower()}"
    return logging.getLogger(logger_name)


if __name__ == "__main__":
    # Test the logging setup
    setup_logging("test_app", "DEBUG")
    
    logger = logging.getLogger(__name__)
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test collector logger
    collector_logger = get_collector_logger("TestCollector")
    collector_logger.debug("This is a collector debug message")
    collector_logger.info("This is a collector info message")