from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QPixmap
import math

class Painter:
    def __init__(self, parent, tool_state):
        self.parent = parent
        self.tool_state = tool_state

        self.strokes = []   
        self.redo_stack = []
        self.drawing = False
        self.current_stroke = None
        
        self.shape_start = None
        self.shape_preview = None

        self.canvas_pixmap = None 

    def _ensure_canvas_size(self):
        parent_size = self.parent.size()
        if self.canvas_pixmap is None or self.canvas_pixmap.size() != parent_size:
            new_pixmap = QPixmap(parent_size)
            new_pixmap.fill(Qt.GlobalColor.transparent)
            
            if self.strokes:
                painter = QPainter(new_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                self._redraw_all_strokes(painter)
                painter.end()
                
            self.canvas_pixmap = new_pixmap

    # --- NEW: Explicit Clear Method ---
    def clear(self):
        """Clears both the data history and the visual cache layer."""
        self.strokes.clear()
        self.redo_stack.clear()
        
        # Clear the visual cache
        if self.canvas_pixmap:
            self.canvas_pixmap.fill(Qt.GlobalColor.transparent)
            
        self.parent.update()

    def undo(self):
        if self.strokes:
            self.redo_stack.append(self.strokes.pop())
            self._refresh_canvas_layer()
            self.parent.update()

    def redo(self):
        if self.redo_stack:
            self.strokes.append(self.redo_stack.pop())
            self._refresh_canvas_layer()
            self.parent.update()

    def _refresh_canvas_layer(self):
        if self.canvas_pixmap:
            self.canvas_pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(self.canvas_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._redraw_all_strokes(painter)
            painter.end()

    def _redraw_all_strokes(self, painter):
        for item in self.strokes:
            self._draw_item(painter, item)

    def _draw_item(self, painter, item):
        pen = QPen(item["color"], item["size"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if item["type"] == "stroke":
            painter.drawPath(item["path"])
        elif item["type"] == "shape":
            self._draw_shape(painter, item)

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self._ensure_canvas_size()

        if self.tool_state.mode == "erase":
            self.drawing = True
            self._erase_at_point(event.position().toPoint())
            return

        if self.tool_state.mode == "draw":
            self.drawing = True
            self.redo_stack.clear()
            
            start_pt = event.position().toPoint()
            path = QPainterPath()
            path.moveTo(QPointF(start_pt))
            
            self.current_stroke = {
                "type": "stroke",
                "path": path, 
                "points": [start_pt],
                "color": QColor(self.tool_state.color),
                "size": self.tool_state.brush_size
            }

        elif self.tool_state.mode == "shape":
            self.drawing = True
            self.redo_stack.clear()
            self.shape_start = event.position().toPoint()
            self.shape_preview = None

    def mouse_move(self, event):
        if not self.drawing:
            return

        pos = event.position().toPoint()

        if self.tool_state.mode == "erase":
            self._erase_at_point(pos)

        elif self.tool_state.mode == "draw" and self.current_stroke:
            self.current_stroke["points"].append(pos)
            self.current_stroke["path"].lineTo(QPointF(pos))
            self.parent.update()

        elif self.tool_state.mode == "shape" and self.shape_start:
            self.shape_preview = pos
            self.parent.update()

    def mouse_release(self, event):
        if not self.drawing:
            return

        self.drawing = False

        if self.tool_state.mode == "erase":
            pass

        elif self.tool_state.mode == "draw" and self.current_stroke:
            self.strokes.append(self.current_stroke)
            
            painter = QPainter(self.canvas_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self._draw_item(painter, self.current_stroke)
            painter.end()
            
            self.current_stroke = None
            self.parent.update()

        elif self.tool_state.mode == "shape" and self.shape_start:
            end_point = event.position().toPoint()
            if (end_point - self.shape_start).manhattanLength() > 5:
                shape_data = {
                    "type": "shape",
                    "shape": self.tool_state.shape_type,
                    "start": self.shape_start,
                    "end": end_point,
                    "color": QColor(self.tool_state.color),
                    "size": self.tool_state.brush_size
                }
                self.strokes.append(shape_data)
                
                painter = QPainter(self.canvas_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                self._draw_item(painter, shape_data)
                painter.end()
            
            self.shape_start = None
            self.shape_preview = None
            self.parent.update()

    def _erase_at_point(self, erase_point):
        erase_radius = self.tool_state.brush_size * 4
        indices_to_remove = []
        erase_rect_f = QRectF(
            erase_point.x() - erase_radius, 
            erase_point.y() - erase_radius, 
            erase_radius * 2, 
            erase_radius * 2
        )

        stroke_removed = False

        for i, item in enumerate(self.strokes):
            hit = False
            if item["type"] == "stroke":
                if item["path"].controlPointRect().intersects(erase_rect_f):
                    for point in item["points"]:
                        if (point - erase_point).manhattanLength() < erase_radius:
                            hit = True
                            break
            elif item["type"] == "shape":
                rect = QRect(item["start"], item["end"]).normalized()
                expanded = rect.adjusted(-erase_radius, -erase_radius, erase_radius, erase_radius)
                if expanded.contains(erase_point):
                    hit = True

            if hit:
                indices_to_remove.append(i)
                stroke_removed = True

        for i in reversed(indices_to_remove):
            self.strokes.pop(i)
        
        if stroke_removed:
            self._refresh_canvas_layer()
            self.parent.update()

    def paint_event(self, event):
        painter = QPainter(self.parent)
        painter.fillRect(self.parent.rect(), QColor(0, 50, 150, 20))

        self._ensure_canvas_size()

        if self.canvas_pixmap:
            painter.drawPixmap(0, 0, self.canvas_pixmap)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        if self.current_stroke:
            self._draw_item(painter, self.current_stroke)
            
        if self.tool_state.mode == "shape" and self.shape_start and self.shape_preview:
            preview_item = {
                "shape": self.tool_state.shape_type,
                "start": self.shape_start,
                "end": self.shape_preview,
                "color": QColor(self.tool_state.color),
                "size": self.tool_state.brush_size,
                "type": "shape"
            }
            preview_item["color"].setAlpha(150)
            self._draw_item(painter, preview_item)
        
        if self.tool_state.mode == "erase" and hasattr(self.parent, 'last_mouse_pos'):
            r = self.tool_state.brush_size * 4
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(255, 100, 100, 50))
            painter.drawEllipse(self.parent.last_mouse_pos, r, r)

    def _draw_shape(self, painter, shape):
        pen = QPen(shape["color"], shape["size"], Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        start, end = shape["start"], shape["end"]
        
        if shape["shape"] == "rectangle":
            painter.drawRect(QRect(start, end))
        elif shape["shape"] == "circle":
            painter.drawEllipse(QRect(start, end))
        elif shape["shape"] == "line":
            painter.drawLine(start, end)
        elif shape["shape"] == "arrow":
            self._draw_arrow(painter, start, end, shape["size"])

    def _draw_arrow(self, painter, start, end, size):
        painter.drawLine(start, end)
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = max(12, size * 3)
        p1 = QPoint(int(end.x() - arrow_size * math.cos(angle - math.pi / 6)), int(end.y() - arrow_size * math.sin(angle - math.pi / 6)))
        p2 = QPoint(int(end.x() - arrow_size * math.cos(angle + math.pi / 6)), int(end.y() - arrow_size * math.sin(angle + math.pi / 6)))
        painter.setBrush(painter.pen().color())
        painter.drawPolygon([end, p1, p2])