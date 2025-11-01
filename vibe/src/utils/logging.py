"""
Logging configuration for the CTF solver
"""
import logging
import sys
from pathlib import Path
from loguru import logger as loguru_logger

def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    
    # Remove default handler
    loguru_logger.remove()
    
    # Add console handler
    loguru_logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file handler if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        loguru_logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="7 days"
        )

def get_logger(name: str = None):
    """Get a logger instance"""
    if name:
        return loguru_logger.bind(name=name)
    return loguru_logger