import logging
import traceback
from typing import Optional, Any
from bpy.types import Context

logger = logging.getLogger('avatar_toolkit')
_original_error = logger.error

def configure_logging(enabled: bool = False) -> None:
    """Configure logging for Avatar Toolkit"""
    logger.setLevel(logging.DEBUG if enabled else logging.WARNING)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    if enabled:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        def error_with_traceback(msg, *args, **kwargs):
            if kwargs.get('exc_info', False) or isinstance(msg, Exception):
                full_msg = f"{msg}\n{traceback.format_exc()}"
                _original_error(full_msg, *args, **{**kwargs, 'exc_info': False})
            else:
                _original_error(msg, *args, **kwargs)
            
        logger.error = error_with_traceback

def update_logging_state(self: Any, context: Context) -> None:
    """Update logging state based on user preference"""
    from .addon_preferences import save_preference
    enabled = self.enable_logging
    save_preference("enable_logging", enabled)
    configure_logging(enabled)