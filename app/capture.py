import os
import logging
from datetime import datetime
from PIL import ImageGrab, ImageDraw, ImageFont
from PyQt6.QtWidgets import QApplication

def get_timestamped_path():
    if not os.path.exists("captures"):
        os.makedirs("captures")
        logging.info("Created captures directory")
    path = os.path.join("captures", f"q_{datetime.now().strftime('%H%M%S')}.png")
    logging.info(f"Generated path: {path}")
    return path

def capture_screen_with_overlay(overlay_widget):
    """
    Captures the screen using PIL and draws overlay elements on top.
    Uses the approach from backup.py that was working.
    """
    logging.info("Starting screen capture with PIL...")
    
    # Hide the overlay to capture clean screen
    overlay_widget.hide()
    QApplication.processEvents()
    
    # Capture screen with PIL
    screenshot = ImageGrab.grab(all_screens=True)
    logging.info(f"Screenshot captured: {screenshot.size}")
    
    draw = ImageDraw.Draw(screenshot)
    
    # Draw the strokes/lines from the painter
    strokes_drawn = 0
    if hasattr(overlay_widget, 'painter') and hasattr(overlay_widget.painter, 'strokes'):
        for stroke in overlay_widget.painter.strokes:
            if stroke.get("type") == "stroke" and len(stroke.get('points', [])) > 1:
                # Convert QPoint to tuples for PIL
                points = [(p.x(), p.y()) for p in stroke['points']]
                color = stroke['color']
                width = stroke.get('size', 3)
                # Convert QColor to RGB tuple
                rgb_color = (color.red(), color.green(), color.blue())
                draw.line(points, fill=rgb_color, width=width)
                strokes_drawn += 1
            elif stroke.get("type") == "shape":
                # Draw shapes
                color = stroke['color']
                rgb_color = (color.red(), color.green(), color.blue())
                width = stroke.get('size', 3)
                start = stroke.get('start')
                end = stroke.get('end')
                
                if start and end:
                    shape_type = stroke.get('shape')
                    # Draw based on shape type (Rectangle, Circle, Line, Arrow)
                    # For simplicity, drawing as lines for now
                    x1, y1 = start.x(), start.y()
                    x2, y2 = end.x(), end.y()
                    
                    # Rectangle
                    if hasattr(shape_type, 'name') and 'RECTANGLE' in shape_type.name:
                        draw.rectangle([x1, y1, x2, y2], outline=rgb_color, width=width)
                    # Circle  
                    elif hasattr(shape_type, 'name') and 'CIRCLE' in shape_type.name:
                        draw.ellipse([x1, y1, x2, y2], outline=rgb_color, width=width)
                    # Line or Arrow (simplified)
                    else:
                        draw.line([(x1, y1), (x2, y2)], fill=rgb_color, width=width)
                    
                    strokes_drawn += 1
        
        logging.info(f"Drew {strokes_drawn} strokes/shapes")
    
    # Draw text boxes
    textboxes_drawn = 0
    if hasattr(overlay_widget, 'textboxes'):
        for textbox in overlay_widget.textboxes:
            text = textbox.text()
            if text.strip():
                tx, ty = textbox.x(), textbox.y()
                tw, th = textbox.width(), textbox.height()
                
                # Draw background
                draw.rectangle([tx, ty, tx+tw, ty+th], fill=(50, 50, 70, 200))
                
                # Draw text
                font_size = max(12, int(th * 0.5))
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    try:
                        font = ImageFont.truetype("segoeui.ttf", font_size)
                    except:
                        font = ImageFont.load_default()
                
                draw.text((tx+10, ty+(th-font_size)//2), text, fill=(255, 255, 255), font=font)
                textboxes_drawn += 1
        
        logging.info(f"Drew {textboxes_drawn} text boxes")
    
    # Save the screenshot
    path = get_timestamped_path()
    screenshot.save(path)
    
    abs_path = os.path.abspath(path)
    
    if os.path.exists(abs_path):
        size = os.path.getsize(abs_path)
        logging.info(f"Screenshot saved successfully to: {abs_path}")
        logging.info(f"File size: {size} bytes")
    else:
        logging.error(f"Screenshot save failed - file not found at: {abs_path}")
        abs_path = None
    
    return abs_path