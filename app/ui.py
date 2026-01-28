from PyQt6.QtWidgets import (
    QMainWindow, QLineEdit, QWidget, QHBoxLayout,
    QPushButton, QApplication, QVBoxLayout, QTextEdit,
    QColorDialog, QSlider, QLabel, QComboBox, QFileDialog
)
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import (
    QFont, QCursor, QPainter, QColor,
    QPainterPath, QPen, QLinearGradient, QRadialGradient
)
import ollama
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
        self.delete_btn.move(self.width() - 28, 4)
        super().resizeEvent(event)

    def mousePressEvent(self, event):
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
        if not self.resizing:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
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

class CommandBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(740, 60)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(10)
        
        self.setObjectName("CommandBar")
        self.setStyleSheet("""
            QWidget#CommandBar {
                background: rgba(30, 30, 40, 220);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 30px;
            }
        """)

        # 1. Attachment Button
        self.btn_attach = QPushButton("📎")
        self.btn_attach.setFixedSize(36, 36)
        self.btn_attach.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_attach.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 10);
                border: none; border-radius: 18px; color: white; font-size: 16px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 30); }
        """)
        self.btn_attach.clicked.connect(self.attach_files)
        layout.addWidget(self.btn_attach)

        # 2. Model Selector
        self.model_combo = QComboBox()
        
        available_models = ["gemini-2.5-flash"]
        try:
            models_info = ollama.list()
            if hasattr(models_info, 'get') and 'models' in models_info:
                for m in models_info['models']:
                    available_models.append(m['model'])
            elif isinstance(models_info, list):
                for m in models_info:
                    available_models.append(m['model'])
        except Exception:
            available_models.extend(["llava", "llama3"])

        self.model_combo.addItems(available_models)
        self.model_combo.setFixedWidth(140)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background: rgba(0, 0, 0, 0.3);
                color: #ddd; border: 1px solid rgba(255,255,255,30);
                border-radius: 8px; padding: 5px; font-size: 11px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: rgb(40, 40, 50); color: white;
                selection-background-color: rgba(100, 100, 255, 0.5);
            }
        """)
        layout.addWidget(self.model_combo)

        # 3. Input Field
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask about the screen...")
        self.input.setFont(QFont("Segoe UI", 12))
        self.input.setStyleSheet("""
            QLineEdit {
                background: transparent; border: none; color: white;
            }
        """)
        layout.addWidget(self.input)

        # 4. File Counter
        self.file_badge = QLabel("")
        self.file_badge.setStyleSheet("color: #aaa; font-size: 11px; margin-right: 5px;")
        self.file_badge.hide()
        layout.addWidget(self.file_badge)

        # 5. Enter Button
        self.btn_enter = QPushButton("➤")
        self.btn_enter.setFixedSize(40, 40)
        self.btn_enter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_enter.setStyleSheet("""
            QPushButton {
                background: rgba(100, 100, 255, 180);
                border: none; border-radius: 20px; color: white; font-size: 16px;
            }
            QPushButton:hover { background: rgba(120, 120, 255, 200); }
        """)
        layout.addWidget(self.btn_enter)

        self.attached_files = []

    def attach_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Attach Context", "", 
            "Documents (*.pdf *.txt *.md *.py *.js *.html *.docx)"
        )
        if files:
            self.attached_files.extend(files)
            self.update_badge()

    def update_badge(self):
        count = len(self.attached_files)
        if count > 0:
            self.file_badge.setText(f"{count} file(s)")
            self.file_badge.show()
        else:
            self.file_badge.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 30, 30)
        painter.fillPath(path, QColor(30, 30, 40, 200))


class GhostUI(QMainWindow):
    capture_completed = pyqtSignal(str, str, list, str)

    def __init__(self, ai_client=None):
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

        self.command_bar = CommandBar(self)
        screen_width = self.screen().geometry().width()
        screen_height = self.screen().geometry().height()
        
        self.command_bar.move((screen_width - 740) // 2, screen_height - 100)
        self.command_bar.btn_enter.clicked.connect(self.submit_to_ai)
        self.command_bar.input.returnPressed.connect(self.submit_to_ai)
        self.command_bar.show()

        self.toolbar = QWidget(self)
        self.toolbar.setObjectName("Toolbar")
        self.toolbar.setFixedSize(540, 60)
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
        self._is_submitting = False

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
        painter.restore()

    def enable_draw(self):
        self.tool_state.mode = "draw"
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.clear_checks()
        self.btn_draw.setChecked(True)

    def enable_erase(self):
        self.tool_state.mode = "erase"
        self.setCursor(Qt.CursorShape.BlankCursor)
        self.clear_checks()
        self.btn_erase.setChecked(True)

    def enable_shapes(self):
        self.tool_state.mode = "shape"
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.clear_checks()
        self.btn_shape.setChecked(True)
        self.toggle_shape_popover()

    def delete_textbox(self, textbox):
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
        # --- FIXED: Use the painter's new clear method ---
        self.painter.clear()
        
        for box in self.textboxes:
            box.close()
        self.textboxes.clear()
        
    def clear_checks(self):
        for b in [self.btn_draw, self.btn_erase, self.btn_text, self.btn_shape]:
            b.setChecked(False)

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
            self.update()

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
        elif event.key() == Qt.Key.Key_Escape:
            self.close()
            
    def closeEvent(self, event):
        if self.brush_popover:
            self.brush_popover.close()
        if self.shape_popover:
            self.shape_popover.close()
        super().closeEvent(event)

    def submit_to_ai(self):
        """Modified to prevent double-submission (409 trigger)"""
        if self._is_submitting:
            return
            
        prompt = self.command_bar.input.text()
        attached_files = self.command_bar.attached_files
        selected_model = self.command_bar.model_combo.currentText()
        
        # If no prompt, check textboxes
        if not prompt.strip() and not attached_files:
            prompts = [b.text() for b in self.textboxes if b.text().strip()]
            prompt = " ".join(prompts) if prompts else "Explain this."

        self._is_submitting = True  # Set guard
        self.command_bar.btn_enter.setEnabled(False) # Visual feedback
        
        text_data = [(b.text(), b.x(), b.y(), b.width(), b.height()) for b in self.textboxes]
        
        # Hide UI elements for clean capture
        self.toolbar.hide()
        self.command_bar.hide()
        for b in self.textboxes: b.hide()
        
        QApplication.processEvents()
        
        try:
            path = capture_screen_with_overlay(self.painter.strokes, text_data)
            self.close()
            # Emit signal to ChatWindow
            self.capture_completed.emit(path, prompt, attached_files, selected_model)
        finally:
            # Reset state for next time the overlay is opened
            self._is_submitting = False
            self.command_bar.btn_enter.setEnabled(True)