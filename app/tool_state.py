from PyQt6.QtGui import QColor
from enum import Enum, auto

class ToolMode(Enum):
    IDLE = auto()
    DRAW = auto()
    ERASE = auto()
    TEXT = auto()
    SHAPE = auto()

class ShapeType(Enum):
    RECTANGLE = auto()
    CIRCLE = auto()
    LINE = auto()
    ARROW = auto()

class ToolState:
    def __init__(self):
        self.mode = ToolMode.IDLE
        self.color = QColor(255, 255, 100) 
        self.brush_size = 4
        self.shape_type = ShapeType.RECTANGLE
        self.active_textbox = None