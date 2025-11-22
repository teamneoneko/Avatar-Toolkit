import logging
import traceback
from typing import Optional, Any
from bpy.types import Context

logger = logging.getLogger('avatar_toolkit')
_original_error = logger.error

def configure_logging(enabled: bool = False, level: str = "WARNING") -> None:
    """Configure logging for Avatar Toolkit """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR
    }
    
    log_level = level_map.get(level, logging.WARNING)
    
    if enabled:
        logger.setLevel(log_level)
    else:
        logger.setLevel(logging.ERROR)  # We should still log errors when logging is disabled so we don't have silent failures
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    if enabled:
        handler = logging.StreamHandler()
        handler.setLevel(log_level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        def error_with_traceback(msg, *args, **kwargs):
            # If exc_info is True, include traceback in the message
            if kwargs.get('exc_info', False):
                full_msg = f"{msg}\n{traceback.format_exc()}"
                _original_error(full_msg, *args, **{k: v for k, v in kwargs.items() if k != 'exc_info'})
            else:
                _original_error(msg, *args, **kwargs)
            
        logger.error = error_with_traceback

def update_logging_state(self: Any, context: Context) -> None:
    """Update logging state based on user preference"""
    from .addon_preferences import save_preference
    enabled = self.enable_logging
    level = self.log_level if hasattr(self, "log_level") else "WARNING"
    save_preference("enable_logging", enabled)
    configure_logging(enabled, level)
