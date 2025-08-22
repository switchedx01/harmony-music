# dad_player/ui/utils/layouts.py

from kivy.properties import NumericProperty
from kivy.uix.floatlayout import FloatLayout

class AspectRatioLayout(FloatLayout):
    ratio = NumericProperty(16 / 9)

    def on_size(self, *args):

        layout_width = self.width
        layout_height = self.height
        target_width = layout_height * self.ratio
        target_height = layout_width / self.ratio

        if target_width > layout_width:
            final_width = layout_width
            final_height = target_height
            
        else:
            final_width = target_width
            final_height = layout_height

        for child in self.children:
            child.size_hint = (None, None)
            child.width = final_width
            child.height = final_height
            child.pos_hint = {"center_x": 0.5, "center_y": 0.5}

