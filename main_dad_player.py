# dad_player/main_dad_player.py

# =============================================================================
# Imports
# =============================================================================
import os
import sys


from logging_config import setup_logging

os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Debug prints for diagnosis (remove after fixing)
print("sys.path:", sys.path)
print("Contents of project_root:", os.listdir(project_root))
print("Contents of dad_player subdirectory:", os.listdir(os.path.join(project_root, 'dad_player')))
print("Contents of dad_player/core:", os.listdir(os.path.join(project_root, 'dad_player', 'core')))
print("Contents of dad_player/ui:", os.listdir(os.path.join(project_root, 'dad_player', 'ui')))
print("Contents of dad_player/kv:", os.listdir(os.path.join(project_root, 'dad_player', 'kv')))

# =============================================================================
# Application Mode Functions
# =============================================================================
def run_gui_app():
    from dad_player.app import DadPlayerApp
    DadPlayerApp().run()

# =============================================================================
# Main Entry Point
# =============================================================================
def main():
    run_gui_app()

if __name__ == "__main__":
    main()