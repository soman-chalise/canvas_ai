from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QPolygon
import math


class Painter:
    def __init__(self, parent, tool_state):
        self.parent = parent
        self.tool_state = tool_state

        self.strokes = []   # list of dicts with type: "stroke" or "shape"
        self.redo_stack = []
        self.drawing = False
        self.current_stroke = None
        
        # For shape drawing
        self.shape_start = None
        self.shape_preview = None

    def undo(self):
        if self.strokes:
            self.redo_stack.append(self.strokes.pop())
            self.parent.update()

    def redo(self):
        if self.redo_stack:
            self.strokes.append(self.redo_stack.pop())
            self.parent.update()

    def mouse_press(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        # Eraser - now works like a brush
        if self.tool_state.mode == "erase":
            self.drawing = True
            self.redo_stack.clear()
            self.current_stroke = {
                "type": "erase_stroke",
                "points": [event.position().toPoint()],
                "size": self.tool_state.brush_size * 3  # Eraser is bigger
            }
            self._erase_at_point(event.position().toPoint())
            return

        # Drawing
        if self.tool_state.mode == "draw":
            self.drawing = True
            self.redo_stack.clear()
            self.current_stroke = {
                "type": "stroke",
                "points": [event.position().toPoint()],
                "color": QColor(self.tool_state.color),
                "size": self.tool_state.brush_size
            }
            self.strokes.append(self.current_stroke)

        # Shape drawing
        elif self.tool_state.mode == "shape":
            self.drawing = True
            self.redo_stack.clear()
            self.shape_start = event.position().toPoint()
            self.shape_preview = None

    def mouse_move(self, event):
        if not self.drawing:
            return

        if self.tool_state.mode == "erase":
            # Continuously erase as mouse moves
            point = event.position().toPoint()
            self.current_stroke["points"].append(point)
            self._erase_at_point(point)
            self.parent.update()

        elif self.tool_state.mode == "draw" and self.current_stroke:
            self.current_stroke["points"].append(event.position().toPoint())
            self.parent.update()

        elif self.tool_state.mode == "shape" and self.shape_start:
            self.shape_preview = event.position().toPoint()
            self.parent.update()

    def mouse_release(self, event):
        if not self.drawing:
            return

        if self.tool_state.mode == "erase":
            self.drawing = False
            self.current_stroke = None

        elif self.tool_state.mode == "draw":
            self.drawing = False
            self.current_stroke = None

        elif self.tool_state.mode == "shape" and self.shape_start:
            self.drawing = False
            end_point = event.position().toPoint()
            
            # Only add shape if there's meaningful size
            if (end_point - self.shape_start).manhattanLength() > 10:
                shape_data = {
                    "type": "shape",
                    "shape": self.tool_state.shape_type,
                    "start": self.shape_start,
                    "end": end_point,
                    "color": QColor(self.tool_state.color),
                    "size": self.tool_state.brush_size
                }
                self.strokes.append(shape_data)
            
            self.shape_start = None
            self.shape_preview = None
            self.parent.update()

    def _erase_at_point(self, erase_point):
        """Erase portions of strokes that intersect with the eraser point"""
        erase_radius = self.tool_state.brush_size * 3
        strokes_to_remove = []
        strokes_to_add = []
        
        for i, item in enumerate(self.strokes):
            if item["type"] == "stroke":
                # Check each point in the stroke
                new_segments = []
                current_segment = []
                
                for point in item["points"]:
                    distance = math.sqrt((point.x() - erase_point.x())**2 + 
                                       (point.y() - erase_point.y())**2)
                    
                    if distance > erase_radius:
                        # Point is outside eraser radius, keep it
                        current_segment.append(point)
                    else:
                        # Point is inside eraser radius, break the stroke
                        if len(current_segment) > 1:
                            new_segments.append(current_segment)
                        current_segment = []
                
                # Add the last segment if it exists
                if len(current_segment) > 1:
                    new_segments.append(current_segment)
                
                # If stroke was broken into segments, replace it
                if len(new_segments) == 0:
                    strokes_to_remove.append(i)
                elif len(new_segments) > 1 or len(new_segments[0]) < len(item["points"]):
                    strokes_to_remove.append(i)
                    for segment in new_segments:
                        if len(segment) > 1:
                            strokes_to_add.append({
                                "type": "stroke",
                                "points": segment,
                                "color": QColor(item["color"]),
                                "size": item["size"]
                            })
            
            elif item["type"] == "shape":
                # Check if erase point is near the shape
                rect = QRect(item["start"], item["end"]).normalized()
                # Expand rect by erase radius for hit detection
                expanded_rect = rect.adjusted(-erase_radius, -erase_radius, 
                                             erase_radius, erase_radius)
                if expanded_rect.contains(erase_point):
                    strokes_to_remove.append(i)
        
        # Remove strokes in reverse order to maintain indices
        for i in reversed(strokes_to_remove):
            self.strokes.pop(i)
        
        # Add new segments
        self.strokes.extend(strokes_to_add)

    def paint_event(self, event):
        painter = QPainter(self.parent)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background with subtle gradient
        painter.fillRect(self.parent.rect(), QColor(0, 50, 150, 20))

        # Draw all strokes and shapes
        for item in self.strokes:
            if item["type"] == "stroke":
                self._draw_stroke(painter, item)
            elif item["type"] == "shape":
                self._draw_shape(painter, item)

        # Draw shape preview
        if self.tool_state.mode == "shape" and self.shape_start and self.shape_preview:
            preview_item = {
                "type": "shape",
                "shape": self.tool_state.shape_type,
                "start": self.shape_start,
                "end": self.shape_preview,
                "color": QColor(self.tool_state.color),
                "size": self.tool_state.brush_size
            }
            # Draw preview with transparency
            preview_item["color"].setAlpha(150)
            self._draw_shape(painter, preview_item)
        
        # Draw eraser cursor preview
        if self.tool_state.mode == "erase" and hasattr(self.parent, 'last_mouse_pos'):
            erase_radius = self.tool_state.brush_size * 3
            painter.setPen(QPen(QColor(255, 100, 100, 150), 2, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(255, 255, 255, 30))
            painter.drawEllipse(self.parent.last_mouse_pos, erase_radius, erase_radius)

    def _draw_stroke(self, painter, stroke):
        """Draw a freehand stroke"""
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

    def _draw_shape(self, painter, shape):
        """Draw a geometric shape"""
        pen = QPen(
            shape["color"],
            shape["size"],
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin
        )
        painter.setPen(pen)

        start = shape["start"]
        end = shape["end"]
        shape_type = shape["shape"]

        if shape_type == "rectangle":
            rect = QRect(start, end)
            painter.drawRect(rect.normalized())

        elif shape_type == "circle":
            rect = QRect(start, end)
            painter.drawEllipse(rect.normalized())

        elif shape_type == "line":
            painter.drawLine(start, end)

        elif shape_type == "arrow":
            self._draw_arrow(painter, start, end, shape["size"])

    def _draw_arrow(self, painter, start, end, size):
        """Draw an arrow from start to end"""
        # Draw the main line
        painter.drawLine(start, end)

        # Calculate arrow head
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = max(10, size * 3)

        # Arrow head points
        p1 = QPoint(
            int(end.x() - arrow_size * math.cos(angle - math.pi / 6)),
            int(end.y() - arrow_size * math.sin(angle - math.pi / 6))
        )
        p2 = QPoint(
            int(end.x() - arrow_size * math.cos(angle + math.pi / 6)),
            int(end.y() - arrow_size * math.sin(angle + math.pi / 6))
        )

        # Draw arrow head
        arrow_head = QPolygon([end, p1, p2])
        painter.setBrush(painter.pen().color())
        painter.drawPolygon(arrow_head)