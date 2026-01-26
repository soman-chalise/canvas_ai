import os
from datetime import datetime
from PIL import ImageFont

def get_timestamped_path():
    return os.path.join("captures", f"q_{datetime.now().strftime('%H%M%S')}.png")

def load_font(size):
    try:
        return ImageFont.truetype("arial.ttf", size)
    except:
        return ImageFont.load_default()
