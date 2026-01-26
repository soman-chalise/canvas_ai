from PyQt6.QtGui import QColor

class ToolState:
    def __init__(self):
        self.mode = "idle"     # idle | draw | erase | text
        self.color = QColor(255, 255, 0)
        self.brush_size = 4

        # text-specific
        self.active_textbox = None
