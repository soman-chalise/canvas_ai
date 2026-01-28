import os
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPainter, QPixmap, QColor
from PyQt6.QtCore import Qt

def get_timestamped_path():
    if not os.path.exists("captures"):
        os.makedirs("captures")
    return os.path.join("captures", f"q_{datetime.now().strftime('%H%M%S')}.jpg")

def capture_screen_with_overlay(overlay_widget):
    """
    Captures the physical screen and composites the overlay widget on top.
    This guarantees WYSIWYG (What You See Is What You Get).
    """
    screen = QApplication.primaryScreen()
    
    # 1. Grab the Clean Desktop (Background)
    # We grab the specific geometry of the screen where the widget is
    screen_geo = overlay_widget.screen().geometry()
    background_pixmap = screen.grabWindow(0, screen_geo.x(), screen_geo.y(), screen_geo.width(), screen_geo.height())
    
    # 2. Grab the Overlay (Drawings + Text)
    # render() or grab() handles the transparency and child widgets (textboxes)
    overlay_pixmap = overlay_widget.grab()

    # 3. Composite them
    final_pixmap = QPixmap(background_pixmap.size())
    final_pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(final_pixmap)
    painter.drawPixmap(0, 0, background_pixmap)
    painter.drawPixmap(0, 0, overlay_pixmap)
    painter.end()

    # 4. Save (Qt handles compression)
    path = get_timestamped_path()
    # Save as JPEG with 85% quality
    final_pixmap.save(path, "JPEG", 85)
    
    return path