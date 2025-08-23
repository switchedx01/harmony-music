# dad_player/core/exceptions.py

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

# --- Playlist Errors ---
class PlaylistError(DadPlayerError):
    """Base exception for playlist-related operations."""
    pass

class PlaylistExistsError(PlaylistError):
    """Raised when trying to create a playlist that already exists."""
    pass

class PlaylistNotFoundError(PlaylistError):
    """Raised when a specified playlist cannot be found."""
    pass
