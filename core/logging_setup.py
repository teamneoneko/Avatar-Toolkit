import logging
from typing import Optional

logger = logging.getLogger('avatar_toolkit')

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

def update_logging_state(self, context) -> None:
    """Update logging state based on user preference"""
    from .addon_preferences import save_preference
    enabled = self.enable_logging
    save_preference("enable_logging", enabled)
    configure_logging(enabled)
