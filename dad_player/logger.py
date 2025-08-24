# dad_player/logging_config.py

import logging
import sys

def setup_logging():
    log_format = (
        "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(log_format)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)
    
    logging.info("Logging configured successfully.")