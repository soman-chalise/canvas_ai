from PyQt6.QtGui import QColor

class ToolState:
    def __init__(self):
        self.mode = "idle"     # idle | draw | erase | text | shape
        self.color = QColor(255, 255, 100)  # Softer yellow
        self.brush_size = 4
        
        # Shape-specific
        self.shape_type = "rectangle"  # rectangle | circle | line | arrow
        
        # Text-specific
        self.active_textbox = None