# logging_config.py

import logging
import sys
import os
from logging.handlers import RotatingFileHandler

# =============================================================================
# ANSI Color Codes
# =============================================================================
class LogColors:
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"

# =============================================================================
# Custom Color Formatter
# =============================================================================
class ColorFormatter(logging.Formatter):
    def __init__(self, fmt):
        super().__init__()
        self.fmt = fmt
        self.FORMATS = {
            logging.DEBUG: LogColors.GREY + self.fmt + LogColors.RESET,
            logging.INFO: LogColors.GREY + self.fmt + LogColors.RESET,
            logging.WARNING: LogColors.YELLOW + self.fmt + LogColors.RESET,
            logging.ERROR: LogColors.RED + self.fmt + LogColors.RESET,
            logging.CRITICAL: LogColors.BOLD_RED + self.fmt + LogColors.RESET,
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)

        # Special overrides for library scan messages
        if "ADDED/UPDATED" in record.getMessage():
            log_fmt = LogColors.GREEN + self.fmt + LogColors.RESET
        elif "FAILED:" in record.getMessage():
             log_fmt = LogColors.RED + self.fmt + LogColors.RESET

        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

# =============================================================================
# Main Setup Function
# =============================================================================
def setup_logging():
    """Configures logging for the entire application."""
    
    # === Silence Noisy Libraries ===
    # This will hide the PIL/Pillow debug messages by only showing their warnings and errors.
    logging.getLogger('PIL').setLevel(logging.WARNING)

    # === Configure Root Logger ===
    # We configure the main logger for your application namespace.
    app_logger = logging.getLogger("dad_player")
    app_logger.setLevel(logging.DEBUG)

    # Prevent duplicate logs if this function is called more than once
    if app_logger.hasHandlers():
        app_logger.handlers.clear()

    # === File Handler (No Color) ===
    try:
        # Use the same APPDATA directory as before
        log_dir = os.path.join(os.environ.get('APPDATA'), 'HarmonyPlayer')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        log_file = os.path.join(log_dir, 'app.log')
        file_handler = RotatingFileHandler(
            log_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
        )
        file_format = "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s"
        file_handler.setFormatter(logging.Formatter(file_format))
        app_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Error setting up file logger: {e}")

    # === Console Handler (With Color) ===
    if sys.stdout:
        console_handler = logging.StreamHandler(sys.stdout)
        console_format = "[%(levelname)-7s] %(message)s"
        console_handler.setFormatter(ColorFormatter(console_format))
        app_logger.addHandler(console_handler)
    
    # This is the key change to prevent duplicate logs in the console
    app_logger.propagate = False
    
    app_logger.info("Logging configured successfully with color support.")

