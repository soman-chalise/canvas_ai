# capture.py
import os
import io
from datetime import datetime
from PIL import Image, ImageDraw

from .utils import get_timestamped_path, load_font

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QScreen
from PyQt6.QtCore import QBuffer, QIODevice

def capture_screen_with_overlay(points, textboxes):
    # 1. Grab screen using Qt (High DPI aware)
    screen = QApplication.primaryScreen()
    screenshot = screen.grabWindow(0)
    
    # 2. Convert to PIL
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.ReadWrite)
    screenshot.save(buffer, "PNG")
    screenshot_pil = Image.open(io.BytesIO(buffer.data()))
    draw = ImageDraw.Draw(screenshot_pil)
    
    # 3. Draw your annotations (Lines/Shapes)
    for stroke in points:
        color = stroke["color"]
        rgb = (color.red(), color.green(), color.blue())
        if stroke.get("type") == "stroke":
            pts = [(p.x(), p.y()) for p in stroke["points"]]
            if len(pts) > 1:
                draw.line(pts, fill=rgb, width=stroke["size"])
        elif stroke.get("type") == "shape":
            start, end = stroke["start"], stroke["end"]
            draw.rectangle([start.x(), start.y(), end.x(), end.y()], outline=rgb, width=stroke["size"])

    # 4. Draw Textboxes
    for msg, tx, ty, tw, th in textboxes:
        if msg:
            draw.rectangle([tx, ty, tx+tw, ty+th], fill=(30, 30, 30))
            font = load_font(int(th * 0.6))
            draw.text((tx+10, ty+5), msg, fill=(255, 255, 0), font=font)

    # --- PRODUCTION FIX: RESIZE IMAGE ---
    # This prevents the 429 error by reducing payload size
    max_dim = 1600 
    if screenshot_pil.width > max_dim or screenshot_pil.height > max_dim:
        screenshot_pil.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    path = get_timestamped_path()
    # Save as JPEG with 85% quality to further reduce token usage
    if path.endswith(".png"): path = path.replace(".png", ".jpg")
    screenshot_pil.convert("RGB").save(path, "JPEG", quality=85, optimize=True)
    return path