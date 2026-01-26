import os
from datetime import datetime
from PIL import ImageGrab, ImageDraw, ImageFont

from .utils import get_timestamped_path, load_font

def capture_screen_with_overlay(points, textboxes):
    screenshot = ImageGrab.grab(all_screens=True)
    draw = ImageDraw.Draw(screenshot)

    # Draw strokes
    for stroke in points:
        pts = stroke["points"]
        color = stroke["color"]
        size = stroke["size"]

        if len(pts) > 1:
            draw.line(
                [(p.x(), p.y()) for p in pts],
                fill=(color.red(), color.green(), color.blue()),
                width=size
            )


    # Draw textboxes
    for msg, tx, ty, tw, th in textboxes:
        if msg:
            draw.rectangle([tx, ty, tx+tw, ty+th], fill=(30, 30, 30))
            font_size = int(th * 0.6)
            font = load_font(font_size)
            draw.text((tx+10, ty+(th-font_size)//2-2), msg, fill=(255, 255, 0), font=font)

    if not os.path.exists("captures"):
        os.makedirs("captures")
    path = get_timestamped_path()
    screenshot.save(path)
    return path