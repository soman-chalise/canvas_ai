from PyQt6.QtWidgets import (
    QMainWindow, QLineEdit, QWidget, QHBoxLayout,
    QPushButton, QApplication, QVBoxLayout, QTextEdit,
    QColorDialog, QSlider, QLabel, QComboBox
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import (
    QFont, QCursor, QPainter, QColor,
    QPainterPath, QPen, QLinearGradient, QRadialGradient
)

from .painter import Painter
from .capture import capture_screen_with_overlay
from .tool_state import ToolState


class BrushPopover(QWidget):
    def __init__(self, tool_state, parent=None):
        super().__init__(parent)
        self.tool_state = tool_state
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(280, 80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        label = QLabel("Brush Size")
        label.setStyleSheet("color: rgba(255,255,255,200); font-size: 11px; font-weight: 500;")
        layout.addWidget(label)

        h_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 20)
        self.slider.setValue(self.tool_state.brush_size)
        self.slider.valueChanged.connect(self.update_size)
        
        self.value_label = QLabel(str(self.tool_state.brush_size))
        self.value_label.setFixedWidth(30)
        self.value_label.setStyleSheet("color: rgba(255,255,255,220); font-size: 12px; font-weight: 600;")
        
        h_layout.addWidget(self.slider)
        h_layout.addWidget(self.value_label)
        layout.addLayout(h_layout)

        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: none; height: 6px;
                background: rgba(255,255,255,20);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255,255,255,255), stop:1 rgba(200,200,255,255));
                border: 2px solid rgba(255,255,255,100);
                width: 16px; height: 16px; margin: -5px 0; border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(120,120,255,180), stop:1 rgba(180,120,255,180));
                border-radius: 3px;
            }
        """)

    def update_size(self, value):
        self.tool_state.brush_size = value
        self.value_label.setText(str(value))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 16, 16)
        painter.fillPath(path, QColor(40, 40, 50, 180))
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 40))
        gradient.setColorAt(1, QColor(255, 255, 255, 20))
        painter.fillPath(path, gradient)
        border_gradient = QLinearGradient(0, 0, self.width(), self.height())
        border_gradient.setColorAt(0, QColor(255, 255, 255, 80))
        border_gradient.setColorAt(1, QColor(200, 200, 255, 60))
        painter.setPen(QPen(border_gradient, 1.5))
        painter.drawPath(path)


class ShapePopover(QWidget):
    def __init__(self, tool_state, parent=None):
        super().__init__(parent)
        self.tool_state = tool_state
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(200, 120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        label = QLabel("Shape Type")
        label.setStyleSheet("color: rgba(255,255,255,200); font-size: 11px; font-weight: 500;")
        layout.addWidget(label)

        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["Rectangle", "Circle", "Line", "Arrow"])
        self.shape_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,15); color: rgba(255,255,255,220);
                border: 1px solid rgba(255,255,255,40); border-radius: 8px;
                padding: 6px 12px; font-size: 12px;
            }
            QComboBox:hover {
                background: rgba(255,255,255,25); border: 1px solid rgba(255,255,255,60);
            }
            QComboBox QAbstractItemView {
                background: rgba(40,40,50,240); color: rgba(255,255,255,220);
                selection-background-color: rgba(120,120,255,180);
                border: 1px solid rgba(255,255,255,60); border-radius: 8px;
            }
        """)
        self.shape_combo.currentTextChanged.connect(self.update_shape)
        layout.addWidget(self.shape_combo)

    def update_shape(self, shape_type):
        self.tool_state.shape_type = shape_type.lower()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 16, 16)
        painter.fillPath(path, QColor(40, 40, 50, 180))
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 40))
        gradient.setColorAt(1, QColor(255, 255, 255, 20))
        painter.fillPath(path, gradient)
        border_gradient = QLinearGradient(0, 0, self.width(), self.height())
        border_gradient.setColorAt(0, QColor(255, 255, 255, 80))
        border_gradient.setColorAt(1, QColor(200, 200, 255, 60))
        painter.setPen(QPen(border_gradient, 1.5))
        painter.drawPath(path)


class ResizableTextbox(QLineEdit):
    def __init__(self, parent=None, on_delete_callback=None):
        super().__init__(parent)
        self.on_delete_callback = on_delete_callback
        self.setPlaceholderText("Type here...")
        self.setMinimumSize(120, 40)
        self.resize(240, 50)
        self.setFont(QFont("Segoe UI", 13))
        self.setCursor(Qt.CursorShape.IBeamCursor)

        self.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(50, 50, 70, 200), stop:1 rgba(40, 40, 60, 200));
                color: #f5f5f5; border: 1.5px solid rgba(255,255,255,60);
                border-radius: 12px; padding: 8px 14px;
            }
            QLineEdit:focus {
                border: 1.5px solid rgba(150,150,255,180);
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(60, 60, 80, 220), stop:1 rgba(50, 50, 70, 220));
            }
        """)

        self.dragging = False
        self.resizing = False
        self.offset = QPoint()
        self.resize_start_pos = QPoint()
        self.resize_start_size = None
        
        # Delete button
        self.delete_btn = QPushButton("✕", self)
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.move(self.width() - 28, 4)
        self.delete_btn.clicked.connect(self.delete_self)
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,100,100,180); color: white;
                border: none; border-radius: 12px; font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255,80,80,220);
            }
        """)
        self.delete_btn.hide()

    def delete_self(self):
        if self.on_delete_callback:
            self.on_delete_callback(self)
        self.close()

    def enterEvent(self, event):
        self.delete_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.resizing and not self.dragging:
            self.delete_btn.hide()
        super().leaveEvent(event)

    def resizeEvent(self, event):
        # Keep delete button in top-right corner
        self.delete_btn.move(self.width() - 28, 4)
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        # Check if clicking in resize zone (bottom-right corner)
        resize_zone = QRect(self.width() - 20, self.height() - 20, 20, 20)
        
        if resize_zone.contains(event.position().toPoint()):
            self.resizing = True
            self.resize_start_pos = event.globalPosition().toPoint()
            self.resize_start_size = self.size()
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            self.dragging = True
            self.offset = event.position().toPoint()
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            delta = event.globalPosition().toPoint() - self.resize_start_pos
            new_width = max(120, self.resize_start_size.width() + delta.x())
            new_height = max(40, self.resize_start_size.height() + delta.y())
            self.resize(new_width, new_height)
        elif self.dragging:
            self.move(self.mapToParent(event.position().toPoint() - self.offset))
        else:
            # Update cursor based on position
            resize_zone = QRect(self.width() - 20, self.height() - 20, 20, 20)
            if resize_zone.contains(event.position().toPoint()):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif not self.hasFocus():
                self.setCursor(Qt.CursorShape.IBeamCursor)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.resizing = False
        if not self.hasFocus():
            self.setCursor(Qt.CursorShape.IBeamCursor)
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        # Draw resize handle indicator
        if not self.resizing:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Small triangle in bottom-right
            handle_size = 12
            points = [
                QPoint(self.width() - 2, self.height() - handle_size),
                QPoint(self.width() - 2, self.height() - 2),
                QPoint(self.width() - handle_size, self.height() - 2)
            ]
            
            painter.setBrush(QColor(255, 255, 255, 80))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(points)


class GlassButton(QPushButton):
    def __init__(self, icon, tooltip="", parent=None):
        super().__init__(icon, parent)
        self.setFixedSize(40, 40)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        
        self.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: rgba(255,255,255,200); border-radius: 12px; font-size: 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255,255,255,45), stop:1 rgba(200,200,255,35));
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(150,150,255,80), stop:1 rgba(180,120,255,70));
                color: rgba(255,255,255,255);
            }
        """)


class GhostUI(QMainWindow):
    def __init__(self, ai_client):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.ai_client = ai_client
        self.tool_state = ToolState()
        self.textboxes = []
        self.painter = Painter(self, self.tool_state)
        self.last_mouse_pos = QPoint()

        self.showFullScreen()
        self.setMouseTracking(True)

        self.brush_popover = None
        self.shape_popover = None

        # Toolbar
        self.toolbar = QWidget(self)
        self.toolbar.setObjectName("Toolbar")
        self.toolbar.setFixedSize(540, 60)
        screen_width = self.screen().geometry().width()
        self.toolbar.move((screen_width - 540) // 2, 30)

        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        self.btn_draw = GlassButton("✏️", "Draw (D)")
        self.btn_erase = GlassButton("🧹", "Erase (E)")
        self.btn_shape = GlassButton("◼", "Shapes (S)")
        self.btn_color = GlassButton("🎨", "Color (C)")
        self.btn_brush = GlassButton("●", "Brush Size (B)")
        self.btn_text = GlassButton("📝", "Text (T)")
        self.btn_clear = GlassButton("🗑️", "Clear All")
        self.btn_undo = GlassButton("↶", "Undo (Ctrl+Z)")
        self.btn_redo = GlassButton("↷", "Redo (Ctrl+Y)")
        self.btn_export = GlassButton("💾", "Export (Ctrl+S)")
        self.btn_close = GlassButton("✕", "Close (Esc)")

        for b in [self.btn_draw, self.btn_erase, self.btn_shape, self.btn_color,
                  self.btn_brush, self.btn_text, self.btn_clear,
                  self.btn_undo, self.btn_redo, self.btn_export, self.btn_close]:
            layout.addWidget(b)

        self.btn_draw.clicked.connect(self.enable_draw)
        self.btn_erase.clicked.connect(self.enable_erase)
        self.btn_shape.clicked.connect(self.enable_shapes)
        self.btn_color.clicked.connect(self.pick_color)
        self.btn_brush.clicked.connect(self.toggle_brush_popover)
        self.btn_text.clicked.connect(self.add_new_textbox)
        self.btn_clear.clicked.connect(self.clear_all)
        self.btn_undo.clicked.connect(self.painter.undo)
        self.btn_redo.clicked.connect(self.painter.redo)
        self.btn_export.clicked.connect(self.export_canvas)
        self.btn_close.clicked.connect(self.close)

        self.toolbar.raise_()
        self.toolbar.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        gradient = QRadialGradient(self.width() / 2, self.height() / 2, self.width())
        gradient.setColorAt(0, QColor(30, 60, 150, 25))
        gradient.setColorAt(0.7, QColor(20, 40, 100, 15))
        gradient.setColorAt(1, QColor(10, 20, 50, 20))
        painter.fillRect(self.rect(), gradient)

        self._draw_toolbar_glass(painter)
        self.painter.paint_event(event)

    def _draw_toolbar_glass(self, painter):
        painter.save()
        path = QPainterPath()
        toolbar_rect = self.toolbar.geometry()
        path.addRoundedRect(toolbar_rect.toRectF(), 20, 20)
        
        painter.fillPath(path, QColor(35, 35, 50, 160))
        
        gradient = QLinearGradient(toolbar_rect.x(), toolbar_rect.y(), toolbar_rect.x(), toolbar_rect.bottom())
        gradient.setColorAt(0, QColor(255, 255, 255, 50))
        gradient.setColorAt(0.3, QColor(255, 255, 255, 15))
        gradient.setColorAt(1, QColor(255, 255, 255, 30))
        painter.fillPath(path, gradient)
        
        border_gradient = QLinearGradient(toolbar_rect.left(), toolbar_rect.top(), toolbar_rect.right(), toolbar_rect.bottom())
        border_gradient.setColorAt(0, QColor(255, 255, 255, 100))
        border_gradient.setColorAt(0.5, QColor(200, 200, 255, 80))
        border_gradient.setColorAt(1, QColor(180, 180, 255, 70))
        painter.setPen(QPen(border_gradient, 2))
        painter.drawPath(path)
        painter.restore()

    def clear_checks(self):
        for b in [self.btn_draw, self.btn_erase, self.btn_text, self.btn_shape]:
            b.setChecked(False)

    def enable_draw(self):
        self.tool_state.mode = "draw"
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.clear_checks()
        self.btn_draw.setChecked(True)

    def enable_erase(self):
        self.tool_state.mode = "erase"
        self.setCursor(Qt.CursorShape.BlankCursor)  # Hide cursor, we'll draw custom one
        self.clear_checks()
        self.btn_erase.setChecked(True)

    def enable_shapes(self):
        self.tool_state.mode = "shape"
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.clear_checks()
        self.btn_shape.setChecked(True)
        self.toggle_shape_popover()

    def delete_textbox(self, textbox):
        """Callback for textbox deletion"""
        if textbox in self.textboxes:
            self.textboxes.remove(textbox)

    def add_new_textbox(self):
        self.tool_state.mode = "text"
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.clear_checks()
        self.btn_text.setChecked(True)
        box = ResizableTextbox(self, on_delete_callback=self.delete_textbox)
        pos = self.mapFromGlobal(QCursor.pos())
        box.move(pos.x() - 120, pos.y() - 25)
        box.show()
        self.textboxes.append(box)

    def clear_all(self):
        self.painter.strokes.clear()
        self.painter.redo_stack.clear()
        for box in self.textboxes:
            box.close()
        self.textboxes.clear()
        self.update()

    def export_canvas(self):
        text_data = [(b.text(), b.x(), b.y(), b.width(), b.height()) for b in self.textboxes]
        self.hide()
        QApplication.processEvents()
        path = capture_screen_with_overlay(self.painter.strokes, text_data)
        self.show()
        print(f"Canvas exported to: {path}")

    def pick_color(self):
        color = QColorDialog.getColor(self.tool_state.color, self, "Pick Color")
        if color.isValid():
            self.tool_state.color = color

    def toggle_brush_popover(self):
        if self.brush_popover and self.brush_popover.isVisible():
            self.brush_popover.close()
            self.brush_popover = None
            return
        self.brush_popover = BrushPopover(self.tool_state, self)
        btn_pos = self.btn_brush.mapToGlobal(QPoint(0, 0))
        self.brush_popover.move(btn_pos.x() - 100, btn_pos.y() + 50)
        self.brush_popover.show()

    def toggle_shape_popover(self):
        if self.shape_popover and self.shape_popover.isVisible():
            self.shape_popover.close()
            self.shape_popover = None
            return
        self.shape_popover = ShapePopover(self.tool_state, self)
        btn_pos = self.btn_shape.mapToGlobal(QPoint(0, 0))
        self.shape_popover.move(btn_pos.x() - 60, btn_pos.y() + 50)
        self.shape_popover.show()

    def mousePressEvent(self, event):
        if self.toolbar.geometry().contains(event.position().toPoint()):
            return
        if self.tool_state.mode in ("draw", "erase", "shape"):
            self.painter.mouse_press(event)

    def mouseMoveEvent(self, event):
        self.last_mouse_pos = event.position().toPoint()
        if self.tool_state.mode in ("draw", "shape", "erase"):
            self.painter.mouse_move(event)
        if self.tool_state.mode == "erase":
            self.update()  # Update to show eraser cursor

    def mouseReleaseEvent(self, event):
        if self.tool_state.mode in ("draw", "shape", "erase"):
            self.painter.mouse_release(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_D:
            self.enable_draw()
        elif event.key() == Qt.Key.Key_E:
            self.enable_erase()
        elif event.key() == Qt.Key.Key_S and not event.modifiers():
            self.enable_shapes()
        elif event.key() == Qt.Key.Key_T:
            self.add_new_textbox()
        elif event.key() == Qt.Key.Key_C and not event.modifiers():
            self.pick_color()
        elif event.key() == Qt.Key.Key_B:
            self.toggle_brush_popover()
        elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.painter.undo()
        elif event.key() == Qt.Key.Key_Y and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.painter.redo()
        elif event.key() == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.export_canvas()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.submit_to_ai()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()

    def closeEvent(self, event):
        if self.brush_popover:
            self.brush_popover.close()
        if self.shape_popover:
            self.shape_popover.close()
        super().closeEvent(event)

    def submit_to_ai(self):
        text_data = [(b.text(), b.x(), b.y(), b.width(), b.height()) for b in self.textboxes]
        prompts = [b.text() for b in self.textboxes if b.text().strip()]
        prompt = " ".join(prompts) if prompts else "Explain what is highlighted."
        self.hide()
        QApplication.processEvents()
        path = capture_screen_with_overlay(self.painter.strokes, text_data)
        self.close()
        self.ai_client.send_image(path, prompt)


class ResponseWindow(QWidget):
    def __init__(self, text):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(520, 400)

        screen = QApplication.primaryScreen().geometry()
        self.move((screen.width() - 520) // 2, (screen.height() - 400) // 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        title_bar = QWidget()
        title_bar.setFixedHeight(50)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(20, 10, 15, 10)

        title_label = QLabel("✨ AI Response")
        title_label.setStyleSheet("color: rgba(255,255,255,240); font-size: 15px; font-weight: 600;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.close)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: rgba(255,255,255,180);
                font-size: 20px; border: none; border-radius: 16px;
            }
            QPushButton:hover {
                background: rgba(255,100,100,180); color: white;
            }
        """)
        title_layout.addWidget(close_btn)
        layout.addWidget(title_bar)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("""
            QTextEdit {
                background: transparent; border: none; padding: 20px;
                selection-background-color: rgba(120,120,255,100);
            }
        """)
        formatted = text.replace("\n", "<br>")
        self.text_area.setHtml(f"<div style='color:#eee; font-size:14px; line-height:1.6; font-family:Segoe UI'>{formatted}</div>")
        layout.addWidget(self.text_area)

        self.old_pos = self.pos()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 18, 18)
        painter.fillPath(path, QColor(35, 35, 50, 240))
        
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(255, 255, 255, 50))
        gradient.setColorAt(1, QColor(255, 255, 255, 20))
        painter.fillPath(path, gradient)
        
        painter.setPen(QPen(QColor(255, 255, 255, 80), 2))
        painter.drawPath(path)

    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.old_pos
        self.move(self.pos() + delta)
        self.old_pos = event.globalPosition().toPoint()