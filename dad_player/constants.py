# dad_player/constants.py


# =============================================================================
# Application Metadata
# =============================================================================
APP_NAME = "Harmony Music Player"
APP_VERSION = "1.0.2 Beta" 

# =============================================================================
# File and Directory Names
# =============================================================================
DATABASE_NAME = "dad_player_library.sqlite"
SETTINGS_FILE = "dad_player_settings.json"
ART_THUMBNAIL_DIR = "art_thumbnails"
PLACEHOLDER_ALBUM_FILENAME = "placeholder_album.png"

# =============================================================================
# UI Layout
# =============================================================================
LAYOUT_BREAKPOINT = 900 # Width threshold for switching to desktop layout

# =============================================================================
# Image Sizes
# =============================================================================
ALBUM_ART_THUMBNAIL_SIZE = 200  # For library grid view
ALBUM_ART_NOW_PLAYING_SIZE = 400 # For the main now playing art

# =============================================================================
# Supported Formats
# =============================================================================
SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".m4a", "aac",)

# =============================================================================
# Settings Keys
# =============================================================================
CONFIG_KEY_MUSIC_FOLDERS = "music_folders"
CONFIG_KEY_AUTOPLAY = "autoplay"
CONFIG_KEY_SHUFFLE = "shuffle"
CONFIG_KEY_REPEAT = "repeat_mode"
CONFIG_KEY_LAST_VOLUME = "last_volume"
CONFIG_KEY_REPLAYGAIN = "replaygain"
CONFIG_KEY_CONSOLIDATE_ALBUMS = "consolidate_albums"

# =============================================================================
# Playback Modes
# =============================================================================
REPEAT_NONE = 0
REPEAT_SONG = 1
REPEAT_PLAYLIST = 2
REPEAT_MODES_TEXT = {
    REPEAT_NONE: "Repeat: Off",
    REPEAT_SONG: "Repeat: Song",
    REPEAT_PLAYLIST: "Repeat: All",
}

# =============================================================================
# Database Constants
# =============================================================================
DB_TRACKS_TABLE = "tracks"
DB_ALBUMS_TABLE = "albums"
DB_ARTISTS_TABLE = "artists"
