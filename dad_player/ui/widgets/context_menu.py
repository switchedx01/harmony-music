# dad_player/ui/widgets/context_menu.py

from kivy.properties import ObjectProperty
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDRaisedButton
from kivymd.app import MDApp
from functools import partial

class ContextMenu(MDCard):
    target_widget = ObjectProperty(None)

    def __init__(self, menu_items, target_widget=None, **kwargs):
        self.target_widget = target_widget
        super().__init__(**kwargs)
        # --- changeable values ---
        self.size_hint = (None, None)
        self.width = "200dp"
        self.adaptive_height = True
        self.md_bg_color = "#2c2c2c"
        self.elevation = 8
        self.padding = "4dp"
        self.radius = [7]
        self.orientation = 'vertical'
        self.spacing = "4dp"

        self.populate_menu(menu_items)

    # --- functions ---

    def populate_menu(self, menu_items):
        for item in menu_items:
            button = MDRaisedButton(
                text=item.get("text", ""),
                md_bg_color="#3e3e3e",
                theme_text_color="Custom",
                text_color="white",
                elevation=0
            )
            callback = item.get("callback")
            if callback:
                button.bind(on_release=partial(self.on_item_press, callback))
            self.add_widget(button)

    def on_item_press(self, callback, instance):
        self.dismiss()
        callback()

    def dismiss(self):
        if self.parent:
            self.parent.remove_widget(self)
            app = MDApp.get_running_app()
            if hasattr(app, 'floating_widget') and app.floating_widget == self:
                app.floating_widget = None
