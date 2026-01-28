from datetime import datetime
from PIL import ImageFont
import sys
import os

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_timestamped_path():
    if not os.path.exists("captures"):
        os.makedirs("captures")
    return os.path.join("captures", f"q_{datetime.now().strftime('%H%M%S')}.png")

def load_font(size):
    """
    Robust font loader for Windows. 
    Prevents crash if 'arial.ttf' is missing from the working directory.
    """
    # 1. Try Windows System Font
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    if os.path.exists(font_path):
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass
            
    # 2. Try generic backup (often present on Windows 10/11)
    try:
        return ImageFont.truetype("seguiemj.ttf", size)
    except OSError:
        pass

    # 3. Last Resort: Pillow default (looks pixelated but works)
    return ImageFont.load_default()