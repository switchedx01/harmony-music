# dad_player/utils/file_utils.py

import hashlib
import logging
import os
import re
import sys
from dad_player.constants import APP_NAME

log = logging.getLogger(__name__)

def get_user_data_dir_for_app() -> str:
    """Gets the platform-specific user data directory for the application."""
    user_data_dir = ""
    if os.name == "nt": # Windows
        user_data_dir = os.path.join(os.environ.get("APPDATA", ""), APP_NAME)
    elif sys.platform == "darwin": # macOS
        user_data_dir = os.path.join(os.path.expanduser("~/Library/Application Support"), APP_NAME)
    else: # Linux and other POSIX
        user_data_dir = os.path.join(os.path.expanduser("~/.local/share"), APP_NAME)

    try:
        os.makedirs(user_data_dir, exist_ok=True)
    except OSError as e:
        log.critical(f"Could not create user data directory at {user_data_dir}: {e}")
    return user_data_dir

def generate_file_hash(filepath: str, block_size: int = 65536) -> str | None:
    """Generates an MD5 hash for a file."""
    if not os.path.exists(filepath):
        log.warning(f"File not found for hashing: {filepath}")
        return None
    
    hasher = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(block_size)
        return hasher.hexdigest()
    except IOError as e:
        log.error(f"Could not read file for hashing {filepath}: {e}")
        return None
    except Exception as e:
        log.error(f"Unexpected error hashing file {filepath}: {e}")
        return None

def sanitize_filename_for_cache(filename: str) -> str:
    """Creates a safe filename string for caching purposes."""
    if not filename:
        return "unknown_file"
    
    # Remove invalid characters and replace spaces
    sanitized = re.sub(r'[.\\/:*?"<>|]+', "", filename)
    sanitized = re.sub(r'\s+', "_", sanitized)
    
    max_len = 100
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len]
        
    return sanitized if sanitized else "sanitized_empty"