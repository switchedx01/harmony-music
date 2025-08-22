# dad_player/core/exceptions.py

"""
Custom exceptions for the DaD Player application.
"""

class DadPlayerError(Exception):
    """Base exception class for all application-specific errors."""
    pass

# --- File and Folder Errors ---
class FolderExistsError(DadPlayerError):
    """Raised when trying to add a music folder that already exists."""
    pass

class InvalidFolderPathError(DadPlayerError):
    """Raised when a provided path is not a valid folder."""
    pass

# --- Player Engine Errors ---
class VlcInitializationError(DadPlayerError):
    """Raised when the VLC instance or player fails to initialize."""
    pass

class MediaLoadError(DadPlayerError):
    """Raised when a media file fails to load."""
    pass

class VlcInitializationError(Exception):
    def __init__(self, message="VLC initialization failed"):
        super().__init__(message)
