# dad_player/ui/widgets/settings_panel.py

import logging
from kivymd.uix.gridlayout import MDGridLayout
from kivy.properties import ObjectProperty, BooleanProperty, StringProperty
from kivy.clock import Clock

from dad_player.constants import REPEAT_MODES_TEXT

log = logging.getLogger(__name__)

class CustomSettingsPanel(MDGridLayout):
    settings_manager = ObjectProperty(None)
    library_manager = ObjectProperty(None)

    autoplay_active = BooleanProperty(False)
    shuffle_active = BooleanProperty(False)
    repeat_mode_text = StringProperty("Repeat: Off")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.load_settings_values)
        # Add footnote label
        from kivymd.uix.label import MDLabel
        from kivy.metrics import dp
        footnote = MDLabel(
            text="made by SwitchX01 with love",
            font_style="Caption",
            halign="center",
            size_hint_y=None,
            height=dp(30)
        )
        self.add_widget(footnote)

    def load_settings_values(self, *args):
        """Load initial values from the SettingsManager."""
        if self.settings_manager:
            self.autoplay_active = self.settings_manager.get_autoplay()
            self.shuffle_active = self.settings_manager.get_shuffle()
            self.update_repeat_mode_text()

    def update_repeat_mode_text(self):
        mode = self.settings_manager.get_repeat_mode()
        self.repeat_mode_text = REPEAT_MODES_TEXT.get(mode, "Repeat: Off")

    def on_autoplay_active(self, instance, value):
        if self.settings_manager:
            self.settings_manager.set_autoplay(value)

    def on_shuffle_active(self, instance, value):
        if self.settings_manager:
            self.settings_manager.set_shuffle(value)

    def cycle_repeat_mode(self):
        if self.settings_manager:
            current_mode = self.settings_manager.get_repeat_mode()
            new_mode = (current_mode + 1) % 3
            self.settings_manager.set_repeat_mode(new_mode)
            self.update_repeat_mode_text()

    def open_manage_folders_popup(self):
        from dad_player.ui.popups.manage_folders_popup import ManageFoldersPopup
        popup = ManageFoldersPopup(
            settings_manager=self.settings_manager,
            library_manager=self.library_manager
        )
        popup.open()

    def start_library_scan(self, full_rescan=False):
        if self.library_manager:
            self.library_manager.start_scan_music_library(full_rescan=full_rescan)