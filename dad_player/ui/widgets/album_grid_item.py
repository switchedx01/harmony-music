# dad_player/ui/widgets/album_grid_item.py

from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.card import MDCard

class AlbumGridItem(MDCard):
    """
    A card-based widget to display album art, album name, and artist name.
    The layout for this widget is defined in common_widgets.kv.
    """
    album_name = StringProperty("")
    artist_name = StringProperty("")
    art_path = StringProperty("")
    on_press_callback = ObjectProperty(None)
