# logging_config.py

import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configures logging to write to a rotating file and, if available, the console.
    """
    log_format = (
        "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
    )
    formatter = logging.Formatter(log_format)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    try:
        log_dir = os.path.join(os.environ.get('APPDATA'), 'HarmonyPlayer')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'app.log')
        # FIX: Specify UTF-8 encoding to handle special characters in file paths
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error setting up file logger: {e}")

    if sys.stdout:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
    
    logging.info("Logging configured successfully.")