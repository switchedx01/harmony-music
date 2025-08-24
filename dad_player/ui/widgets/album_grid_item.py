# dad_player/ui/widgets/album_grid_item.py

from kivy.properties import StringProperty, ObjectProperty
from kivy.core.window import Window
from kivymd.uix.card import MDCard
from kivymd.app import MDApp
from dad_player.ui.widgets.context_menu import ContextMenu

class AlbumGridItem(MDCard):
    album_name = StringProperty("")
    artist_name = StringProperty("")
    art_path = StringProperty("")
    on_press_callback = ObjectProperty(None)

    # --- functions ---

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            if touch.button == 'right':
                self.show_context_menu(touch)
                return True
        return super().on_touch_down(touch)

    def show_context_menu(self, touch):
        app = MDApp.get_running_app()
        if hasattr(app, 'context_menu') and app.context_menu:
            app.context_menu.dismiss()
        
        context_menu = ContextMenu(target_widget=self)
        context_menu.pos = touch.pos
        Window.add_widget(context_menu)
        app.context_menu = context_menu
