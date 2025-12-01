import time
import logging
from functools import wraps

# Configure logging (this might be re-configured in main, but good to have here)
logger = logging.getLogger(__name__)

def timing_decorator(func):
    """Decorator to add timing and logging to functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        func_name = func.__name__
        logger.info(f"🚀 Starting {func_name}")
        logger.debug(f"📋 {func_name} args: {args[1:] if args else 'None'}, kwargs: {kwargs}")
        
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"✅ {func_name} completed in {duration:.3f}s")
            logger.debug(f"📤 {func_name} result length: {len(str(result)) if result else 0} chars")
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error(f"❌ {func_name} failed after {duration:.3f}s: {str(e)}")
            raise
    return wrapper
