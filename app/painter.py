from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen

class Painter:
    def __init__(self, parent):
        self.parent = parent
        self.points = []      # List of strokes
        self.redo_stack = []
        self.drawing = False

    def undo(self):
        if self.points:
            self.redo_stack.append(self.points.pop())
            self.parent.update()

    def redo(self):
        if self.redo_stack:
            self.points.append(self.redo_stack.pop())
            self.parent.update()

    # --- Mouse Events ---
    def mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drawing = True
            self.redo_stack = []
            self.points.append([event.position().toPoint()])

    def mouse_move(self, event):
        if self.drawing:
            self.points[-1].append(event.position().toPoint())
            self.parent.update()

    def mouse_release(self, event):
        self.drawing = False

    # --- Paint ---
    def paint_event(self, event):
        painter = QPainter(self.parent)
        painter.fillRect(self.parent.rect(), QColor(0, 50, 150, 30))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(255, 255, 0), 3))
        for line in self.points:
            for i in range(len(line) - 1):
                painter.drawLine(line[i], line[i+1])