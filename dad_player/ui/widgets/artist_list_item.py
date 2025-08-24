# dad_player/ui/widgets/artist_list_item.py

from kivy.properties import StringProperty, ObjectProperty
from kivymd.uix.list import OneLineListItem

class ArtistListItem(OneLineListItem):

    artist_name = StringProperty("")
    on_press_callback = ObjectProperty(None)

    def on_artist_name(self, instance, value):
        self.text = value

    def on_release(self):
        if self.on_press_callback:
            self.on_press_callback()
