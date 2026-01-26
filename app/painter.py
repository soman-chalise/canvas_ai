from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QPen


class Painter:
    def __init__(self, parent, tool_state):
        self.parent = parent
        self.tool_state = tool_state

        self.strokes = []   # list of dicts
        self.redo_stack = []
        self.drawing = False
        self.current_stroke = None

    # -----------------
    # Undo / Redo
    # -----------------
    def undo(self):
        if self.strokes:
            self.redo_stack.append(self.strokes.pop())
            self.parent.update()

    def redo(self):
        if self.redo_stack:
            self.strokes.append(self.redo_stack.pop())
            self.parent.update()

    # -----------------
    # Mouse Events
    # -----------------
    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        # Eraser
        if self.tool_state.mode == "erase":
            click = event.position().toPoint()

            for i, stroke in enumerate(self.strokes):
                for p in stroke["points"]:
                    if (p - click).manhattanLength() < max(12, stroke["size"] * 2):
                        self.strokes.pop(i)
                        self.parent.update()
                        return
            return

        # Draw
        if self.tool_state.mode == "draw":
            self.drawing = True
            self.redo_stack.clear()

            self.current_stroke = {
                "points": [event.position().toPoint()],
                "color": QColor(self.tool_state.color),
                "size": self.tool_state.brush_size
            }
            self.strokes.append(self.current_stroke)

    def mouse_move(self, event):
        if self.drawing and self.current_stroke:
            self.current_stroke["points"].append(event.position().toPoint())
            self.parent.update()

    def mouse_release(self, event):
        self.drawing = False
        self.current_stroke = None

    # -----------------
    # Paint
    # -----------------
    def paint_event(self, event):
        painter = QPainter(self.parent)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(
            self.parent.rect(),
            QColor(0, 50, 150, 20)
        )

        for stroke in self.strokes:
            painter.setPen(QPen(
                stroke["color"],
                stroke["size"],
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.RoundCap,
                Qt.PenJoinStyle.RoundJoin
            ))

            pts = stroke["points"]
            for i in range(len(pts) - 1):
                painter.drawLine(pts[i], pts[i + 1])
