from PyQt6.QtWidgets import (QMainWindow, QLineEdit, QWidget, QHBoxLayout, 
                             QPushButton, QApplication, QVBoxLayout, QTextEdit)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QFont, QCursor, QPainter, QColor, QPainterPath, QPen
from .painter import Painter
from .capture import capture_screen_with_overlay

class ResponseWindow(QWidget):
    """Floating bubble for AI answers."""
    def __init__(self, text):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("background: transparent; color: #888; font-size: 20px; border: none;")
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        formatted_text = text.replace('\n', '<br>')
        self.text_area.setHtml(f"<div style='color: #eee; font-family: Segoe UI; font-size: 14px;'>{formatted_text}</div>")
        self.text_area.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.text_area)
        self.setLayout(layout)
        self.oldPos = self.pos()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 20, 20)
        painter.fillPath(path, QColor(25, 25, 25, 245))
        painter.setPen(QPen(QColor(255, 255, 0, 80), 2))
        painter.drawPath(path)

    def mousePressEvent(self, event): self.oldPos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPosition().toPoint()

class ResizableTextbox(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Ask...")
        self.setFixedSize(220, 50)
        self.setStyleSheet("""
            QLineEdit {
                background: rgba(20, 20, 20, 235);
                color: #ffff00;
                border: 2px solid #ffff00;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        self.dragging = False
        self.resizing = False
        self.offset = QPoint()

        # Delete button
        self.del_btn = QPushButton("×", self)
        self.del_btn.setFixedSize(20, 20)
        self.del_btn.setStyleSheet(
            "background: red; color: white; border-radius: 10px; font-weight: bold; border: none;"
        )
        self.del_btn.hide()
        self.del_btn.clicked.connect(self.delete_me)

    def delete_me(self):
        if hasattr(self.parent(), 'textboxes'):
            self.parent().textboxes.remove(self)
        self.deleteLater()

    def enterEvent(self, event): self.del_btn.show()
    def leaveEvent(self, event): self.del_btn.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.del_btn.move(self.width() - 25, 5)
        new_size = max(10, int(self.height() * 0.4))
        self.setFont(QFont("Segoe UI", new_size))

    def mousePressEvent(self, event):
        if event.position().x() > self.width() - 25 and event.position().y() > self.height() - 25:
            self.resizing = True
        elif event.button() == Qt.MouseButton.RightButton:
            self.dragging = True
            self.offset = event.position().toPoint()
            self.setCursor(Qt.CursorShape.SizeAllCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            self.setFixedSize(max(100, int(event.position().x())), max(40, int(event.position().y())))
        elif self.dragging:
            self.move(self.mapToParent(event.position().toPoint() - self.offset))
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging = self.resizing = False
        self.setCursor(Qt.CursorShape.IBeamCursor)


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
        self.mode = "idle"
        self.textboxes = []
        self.painter = Painter(self)
        self.showFullScreen()
        self.setMouseTracking(True)

        # --- Toolbar ---
        self.toolbar = QWidget(self)
        self.toolbar.setFixedSize(400, 60)
        self.toolbar.move(50, 50)
        self.toolbar.setStyleSheet("background: rgba(30, 30, 30, 250); border: 2px solid #444; border-radius: 12px;")
        
        t_layout = QHBoxLayout(self.toolbar)
        self.btn_draw = QPushButton("Draw")
        self.btn_text = QPushButton("+Text")
        self.btn_undo = QPushButton("Undo")
        self.btn_redo = QPushButton("Redo")
        for btn in [self.btn_draw, self.btn_text, self.btn_undo, self.btn_redo]:
            btn.setStyleSheet("color: white; background: #444; border-radius: 6px; font-weight: bold; font-size: 10px;")
            t_layout.addWidget(btn)

        self.btn_draw.clicked.connect(self.enable_draw)
        self.btn_text.clicked.connect(self.add_new_textbox)
        self.btn_undo.clicked.connect(self.painter.undo)
        self.btn_redo.clicked.connect(self.painter.redo)

        # IMPORTANT: Make the toolbar visible!
        self.toolbar.show()

    # --- Textboxes & Drawing Mode ---
    def enable_draw(self):
        self.mode = "draw"
        self.setCursor(Qt.CursorShape.CrossCursor)

    def add_new_textbox(self):
        box = ResizableTextbox(self)
        m_pos = self.mapFromGlobal(QCursor.pos())
        box.move(m_pos.x() - 110, m_pos.y() - 25)
        box.show()
        self.textboxes.append(box)

    # --- Key Events ---
    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z: self.painter.undo()
            elif event.key() == Qt.Key.Key_Y: self.painter.redo()
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if event.key() == Qt.Key.Key_D: self.enable_draw()
            elif event.key() == Qt.Key.Key_T: self.add_new_textbox()
        if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]: self.submit_to_ai()
        elif event.key() == Qt.Key.Key_Escape: self.close()

    # --- Paint Event ---
    def paintEvent(self, event):
        self.painter.paint_event(event)

    # --- Mouse Events ---
    def mousePressEvent(self, event):
        if self.toolbar.geometry().contains(event.position().toPoint()):
            super().mousePressEvent(event)
            return
        if any(tb.geometry().contains(event.position().toPoint()) for tb in self.textboxes):
            super().mousePressEvent(event)
            return
        if self.mode == "draw":
            self.painter.mouse_press(event)

    def mouseMoveEvent(self, event):
        if self.toolbar.geometry().contains(event.position().toPoint()):
            super().mouseMoveEvent(event)
            return
        if any(tb.geometry().contains(event.position().toPoint()) for tb in self.textboxes):
            super().mouseMoveEvent(event)
            return
        self.painter.mouse_move(event)

    def mouseReleaseEvent(self, event):
        if self.toolbar.geometry().contains(event.position().toPoint()):
            super().mouseReleaseEvent(event)
            return
        if any(tb.geometry().contains(event.position().toPoint()) for tb in self.textboxes):
            super().mouseReleaseEvent(event)
            return
        self.painter.mouse_release(event)

    # --- Submit to AI ---
    def submit_to_ai(self):
        text_data = [(b.text(), b.x(), b.y(), b.width(), b.height()) for b in self.textboxes]
        prompts = [b.text() for b in self.textboxes if b.text().strip()]
        full_prompt = " ".join(prompts) if prompts else "Explain what is highlighted."

        self.hide()
        QApplication.processEvents()
        screenshot_path = capture_screen_with_overlay(self.painter.points, text_data)
        self.close()

        self.ai_client.send_image(screenshot_path, full_prompt)