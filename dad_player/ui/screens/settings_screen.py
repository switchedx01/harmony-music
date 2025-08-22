# dad_player/ui/screens/settings_screen.py

from kivymd.uix.screen import MDScreen
from kivy.properties import ObjectProperty

class SettingsScreen(MDScreen):
    """
    A screen designed to host the main settings panel. It receives the core
    application components as properties from the App class.
    """
    player_engine = ObjectProperty(None)
    library_manager = ObjectProperty(None)
    settings_manager = ObjectProperty(None)
