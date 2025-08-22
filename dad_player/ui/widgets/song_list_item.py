# dad_player/ui/widgets/song_list_item.py

from kivy.properties import StringProperty, ObjectProperty, BooleanProperty
from kivymd.uix.list import ThreeLineAvatarListItem
from kivymd.uix.boxlayout import MDBoxLayout

class SongListItem(ThreeLineAvatarListItem):
    art_path = StringProperty("")
    is_playing = BooleanProperty(False)
    on_press_callback = ObjectProperty(None)

class SongRowItem(MDBoxLayout):
    art_path = StringProperty("")
    text = StringProperty("")
    secondary_text = StringProperty("")
    tertiary_text = StringProperty("")
    is_playing = BooleanProperty(False)
    on_press_callback = ObjectProperty(None)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if self.on_press_callback:
                self.on_press_callback()
            return True
        return super().on_touch_down(touch)