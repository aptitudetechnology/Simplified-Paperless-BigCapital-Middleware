# Add this to the top of config/settings.py to fix the import issue temporarily

import logging

def get_logger(name: str, level: str = 'INFO'):
    """Temporary logger function"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger

# Then replace the problematic import line:
# from utils.logger import get_logger

# With this line instead (since we defined get_logger above):
# (Just use the get_logger function defined above)
