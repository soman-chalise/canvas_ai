from PyQt6.QtWidgets import (
    QMainWindow, QLineEdit, QWidget, QHBoxLayout,
    QPushButton, QApplication, QVBoxLayout, QTextEdit,
    QColorDialog, QSlider
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import (
    QFont, QCursor, QPainter, QColor,
    QPainterPath, QPen
)

from .painter import Painter
from .capture import capture_screen_with_overlay
from .tool_state import ToolState


# -------------------------
# Brush Size Popover (HORIZONTAL, SAFE)
# -------------------------
class BrushPopover(QWidget):
    def __init__(self, tool_state, parent=None):
        super().__init__(parent)
        self.tool_state = tool_state

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(220, 50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(1, 12)
        self.slider.setValue(self.tool_state.brush_size)
        self.slider.valueChanged.connect(self.update_size)

        layout.addWidget(self.slider)

    def update_size(self, value):
        self.tool_state.brush_size = value

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 16, 16)
        painter.fillPath(path, QColor(28, 28, 32, 210))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawPath(path)


# -------------------------
# Resizable Textbox
# -------------------------
class ResizableTextbox(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Ask...")
        self.setFixedSize(220, 48)
        self.setFont(QFont("Segoe UI", 12))
        self.setCursor(Qt.CursorShape.IBeamCursor)

        self.setStyleSheet("""
            QLineEdit {
                background: rgba(28, 28, 32, 180);
                color: #f0f0f0;
                border: 1px solid rgba(255,255,255,50);
                border-radius: 10px;
                padding: 6px;
            }
            QLineEdit:focus {
                border: 1px solid rgba(255,255,255,120);
            }
        """)

        self.dragging = False
        self.offset = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.dragging = True
            self.offset = event.position().toPoint()
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(self.mapToParent(event.position().toPoint() - self.offset))
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging = False
        self.setCursor(Qt.CursorShape.IBeamCursor)


# -------------------------
# Main Overlay UI
# -------------------------
class GhostUI(QMainWindow):
    def __init__(self, ai_client):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.ai_client = ai_client
        self.tool_state = ToolState()
        self.textboxes = []

        self.painter = Painter(self, self.tool_state)

        # FULLSCREEN MODE (SAFE: ESC always exits)
        self.showFullScreen()
        self.setMouseTracking(True)

        self.brush_popover = None

        # -----------------
        # Toolbar
        # -----------------
        self.toolbar = QWidget(self)
        self.toolbar.setObjectName("Toolbar")
        self.toolbar.setFixedSize(360, 50)
        self.toolbar.move(40, 40)

        self.toolbar.setStyleSheet("""
            QWidget#Toolbar {
                background: rgba(28, 28, 32, 180);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 22px;
            }
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255,255,255,200);
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(255,255,255,35);
            }
            QPushButton:checked {
                background: rgba(255,255,255,60);
            }
        """)

        layout = QHBoxLayout(self.toolbar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        def tool_btn(icon):
            b = QPushButton(icon)
            b.setFixedSize(34, 34)
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            return b

        self.btn_draw = tool_btn("✏")
        self.btn_erase = tool_btn("⌫")
        self.btn_color = tool_btn("🎨")
        self.btn_brush = tool_btn("▓")
        self.btn_text = tool_btn("📝")
        self.btn_undo = tool_btn("↶")
        self.btn_redo = tool_btn("↷")

        for b in [self.btn_draw, self.btn_erase, self.btn_color,
                  self.btn_brush, self.btn_text, self.btn_undo, self.btn_redo]:
            layout.addWidget(b)

        self.btn_draw.clicked.connect(self.enable_draw)
        self.btn_erase.clicked.connect(self.enable_erase)
        self.btn_color.clicked.connect(self.pick_color)
        self.btn_brush.clicked.connect(self.toggle_brush_popover)
        self.btn_text.clicked.connect(self.add_new_textbox)
        self.btn_undo.clicked.connect(self.painter.undo)
        self.btn_redo.clicked.connect(self.painter.redo)

        self.toolbar.raise_()
        self.toolbar.show()

        # Enable toolbar dragging
        self._dragging_toolbar = False
        self._toolbar_drag_offset = QPoint()

    # -----------------
    # Tool Modes
    # -----------------
    def clear_checks(self):
        for b in [self.btn_draw, self.btn_erase, self.btn_text]:
            b.setChecked(False)

    def enable_draw(self):
        self.tool_state.mode = "draw"
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.clear_checks()
        self.btn_draw.setChecked(True)

    def enable_erase(self):
        self.tool_state.mode = "erase"
        self.setCursor(Qt.CursorShape.ForbiddenCursor)
        self.clear_checks()
        self.btn_erase.setChecked(True)

    def add_new_textbox(self):
        self.tool_state.mode = "text"
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.clear_checks()
        self.btn_text.setChecked(True)

        box = ResizableTextbox(self)
        pos = self.mapFromGlobal(QCursor.pos())
        box.move(pos.x() - 110, pos.y() - 24)
        box.show()
        self.textboxes.append(box)

    # -----------------
    # Color & Brush
    # -----------------
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
        pos = self.toolbar.mapToGlobal(QPoint(70, self.toolbar.height() + 6))
        self.brush_popover.move(pos)
        self.brush_popover.show()

    # -----------------
    # Paint
    # -----------------
    def paintEvent(self, event):
        self.painter.paint_event(event)

    # -----------------
    # Mouse Routing
    # -----------------
    def mousePressEvent(self, event):
        if self.toolbar.geometry().contains(event.position().toPoint()):
            return
        if self.tool_state.mode in ("draw", "erase"):
            self.painter.mouse_press(event)

    def mouseMoveEvent(self, event):
        if self.tool_state.mode == "draw":
            self.painter.mouse_move(event)

    def mouseReleaseEvent(self, event):
        if self.tool_state.mode == "draw":
            self.painter.mouse_release(event)

    # -----------------
    # Keyboard & Exit
    # -----------------
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.submit_to_ai()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()

    def closeEvent(self, event):
        if self.brush_popover:
            self.brush_popover.close()
            self.brush_popover = None
        super().closeEvent(event)

    # -----------------
    # Submit to AI
    # -----------------
    def submit_to_ai(self):
        text_data = [(b.text(), b.x(), b.y(), b.width(), b.height()) for b in self.textboxes]
        prompts = [b.text() for b in self.textboxes if b.text().strip()]
        prompt = " ".join(prompts) if prompts else "Explain what is highlighted."

        self.hide()
        QApplication.processEvents()

        path = capture_screen_with_overlay(self.painter.strokes, text_data)
        self.close()
        self.ai_client.send_image(path, prompt)


# -------------------------
# Response Window
# -------------------------
class ResponseWindow(QWidget):
    def __init__(self, text):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(480, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.close)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            "background: transparent; color: #aaa; font-size: 18px; border: none;"
        )
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        self.text_area.setStyleSheet("background: transparent; border: none;")
        formatted = text.replace("\n", "<br>")
        self.text_area.setHtml(
            f"<div style='color:#eee; font-size:14px; font-family:Segoe UI'>{formatted}</div>"
        )
        layout.addWidget(self.text_area)

        self.old_pos = self.pos()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 18, 18)
        painter.fillPath(path, QColor(28, 28, 32, 240))
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1))
        painter.drawPath(path)

    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition().toPoint() - self.old_pos
        self.move(self.pos() + delta)
        self.old_pos = event.globalPosition().toPoint()
