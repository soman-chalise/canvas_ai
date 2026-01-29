import os
import logging
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QPushButton, QLabel, 
    QScrollArea, QFrame, QSizePolicy, QFileDialog,
    QComboBox, QMessageBox, QTextBrowser
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QPropertyAnimation, QRect
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPainterPath, 
    QLinearGradient, QPixmap, QIcon
)

from .database import DatabaseManager
from .worker import AIWorker


# ==================== MODERN CHAT BUBBLE ====================
class ChatBubble(QFrame):
    def __init__(self, role, text, image_path=None, parent=None):
        super().__init__(parent)
        self.role = role  # 'user' or 'model'
        self.text_content = text
        self.image_path = image_path
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        
        # If there's an image, show it
        if image_path and os.path.exists(image_path):
            img_label = QLabel()
            pixmap = QPixmap(image_path)
            # Scale to max 400px width while maintaining aspect ratio
            scaled = pixmap.scaledToWidth(400, Qt.TransformationMode.SmoothTransformation)
            img_label.setPixmap(scaled)
            img_label.setMaximumWidth(400)
            layout.addWidget(img_label)
        
        # Message text - Use QTextBrowser for proper resizing
        text_label = QTextBrowser()
        text_label.setPlainText(text)
        text_label.setReadOnly(True)
        text_label.setFont(QFont("Segoe UI", 11))
        text_label.setFrameStyle(QFrame.Shape.NoFrame)
        text_label.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_label.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        # Auto-adjust height based on content
        text_label.document().documentLayout().documentSizeChanged.connect(
            lambda: text_label.setFixedHeight(int(text_label.document().size().height()) + 4)
        )
        
        if role == 'user':
            text_label.setStyleSheet("background: transparent; color: rgba(255,255,255,240); border: none;")
        else:
            text_label.setStyleSheet("background: transparent; color: rgba(240,240,255,255); border: none;")
        
        layout.addWidget(text_label)
        self.text_widget = text_label  # Store reference for updates
        
        # Style based on role
        if role == 'user':
            self.setObjectName("UserBubble")
            self.setStyleSheet("""
                QFrame#UserBubble {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(90, 90, 95, 200), 
                        stop:1 rgba(110, 110, 115, 200));
                    border-radius: 18px;
                    border: 1px solid rgba(180,180,185,50);
                }
            """)
        else:
            self.setObjectName("ModelBubble")
            self.setStyleSheet("""
                QFrame#ModelBubble {
                    background: rgba(55, 55, 60, 180);
                    border-radius: 18px;
                    border: 1px solid rgba(150,150,155,40);
                }
            """)
        
        # Limit width for elegant layout
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)


# ==================== SIDEBAR CHAT ITEM ====================
class ChatSessionItem(QFrame):
    clicked = pyqtSignal(int)  # Emits session_id
    delete_requested = pyqtSignal(int)  # Emits session_id
    
    def __init__(self, session_id, title, parent=None):
        super().__init__(parent)
        self.session_id = session_id
        self.is_active = False
        
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 6, 6)
        
        # Chat icon
        icon_label = QLabel("💬")
        icon_label.setFont(QFont("Segoe UI", 14))
        layout.addWidget(icon_label)
        
        # Title
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 10))
        self.title_label.setStyleSheet("color: rgba(255,255,255,200);")
        self.title_label.setWordWrap(False)
        layout.addWidget(self.title_label, 1)
        
        # Delete button
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255,100,100,120);
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255,80,80,200);
            }
        """)
        self.delete_btn.hide()
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.session_id))
        layout.addWidget(self.delete_btn)
        
        self.update_style()
    
    def enterEvent(self, event):
        self.delete_btn.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if not self.is_active:
            self.delete_btn.hide()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.session_id)
    
    def set_active(self, active):
        self.is_active = active
        self.update_style()
        if active:
            self.delete_btn.show()
        else:
            self.delete_btn.hide()
    
    def update_style(self):
        if self.is_active:
            self.setStyleSheet("""
                ChatSessionItem {
                    background: rgba(85, 85, 90, 140);
                    border-radius: 12px;
                    border-left: 3px solid rgba(140,140,145,220);
                }
            """)
        else:
            self.setStyleSheet("""
                ChatSessionItem {
                    background: rgba(45, 45, 50, 90);
                    border-radius: 12px;
                    border-left: 3px solid transparent;
                }
                ChatSessionItem:hover {
                    background: rgba(65, 65, 70, 130);
                }
            """)


# ==================== SIDEBAR WIDGET ====================
class Sidebar(QFrame):
    new_chat_requested = pyqtSignal()
    session_selected = pyqtSignal(int)
    session_deleted = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setObjectName("Sidebar")
        self.setStyleSheet("""
            QFrame#Sidebar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(35, 35, 38, 245),
                    stop:1 rgba(45, 45, 48, 245));
                border-right: 1px solid rgba(120,120,125,30);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(8)
        
        # Header
        header = QLabel("Chat History")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: rgba(255,255,255,220); padding: 4px;")
        layout.addWidget(header)
        
        # New Chat Button
        self.new_chat_btn = QPushButton("✨ New Chat")
        self.new_chat_btn.setFixedHeight(40)
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        self.new_chat_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(95, 95, 100, 180),
                    stop:1 rgba(115, 115, 120, 180));
                color: white;
                border: 1px solid rgba(160,160,165,70);
                border-radius: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(110, 110, 115, 210),
                    stop:1 rgba(130, 130, 135, 210));
            }
        """)
        self.new_chat_btn.clicked.connect(self.new_chat_requested.emit)
        layout.addWidget(self.new_chat_btn)
        
        # Scroll Area for Sessions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(50,50,55,100);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(110,110,115,150);
                border-radius: 4px;
            }
        """)
        
        self.session_container = QWidget()
        self.session_layout = QVBoxLayout(self.session_container)
        self.session_layout.setContentsMargins(0, 0, 0, 0)
        self.session_layout.setSpacing(6)
        self.session_layout.addStretch()
        
        scroll.setWidget(self.session_container)
        layout.addWidget(scroll, 1)
        
        # Store session widgets
        self.session_widgets = {}  # {session_id: ChatSessionItem}
        self.active_session_id = None
    
    def load_sessions(self, sessions):
        """Load sessions from database: [(id, title), ...]"""
        # Clear existing
        for widget in self.session_widgets.values():
            widget.deleteLater()
        self.session_widgets.clear()
        
        # Add new sessions (they come in DESC order from DB)
        for session_id, title in sessions:
            self.add_session(session_id, title)
    
    def add_session(self, session_id, title):
        item = ChatSessionItem(session_id, title)
        item.clicked.connect(self.session_selected.emit)
        item.delete_requested.connect(self._on_delete_requested)
        
        # Insert at top (before the stretch)
        self.session_layout.insertWidget(0, item)
        self.session_widgets[session_id] = item
    
    def set_active_session(self, session_id):
        # Deactivate all
        for sid, widget in self.session_widgets.items():
            widget.set_active(sid == session_id)
        self.active_session_id = session_id
    
    def _on_delete_requested(self, session_id):
        # Confirmation dialog
        reply = QMessageBox.question(
            self, 'Delete Chat',
            f'Are you sure you want to delete this chat?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.session_deleted.emit(session_id)
    
    def remove_session(self, session_id):
        if session_id in self.session_widgets:
            widget = self.session_widgets.pop(session_id)
            widget.deleteLater()


# ==================== MAIN CHAT WINDOW ====================
class ChatWindow(QMainWindow):
    def __init__(self, ai_client):
        super().__init__()
        self.ai_client = ai_client
        self.db = DatabaseManager()
        
        self.current_session_id = None
        self.current_worker = None
        self.current_response_text = ""
        
        self.setWindowTitle("Canvas AI Chat")
        self.setMinimumSize(1200, 800)
        
        # Main Container
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left Sidebar
        self.sidebar = Sidebar()
        self.sidebar.new_chat_requested.connect(self.create_new_chat)
        self.sidebar.session_selected.connect(self.load_session)
        self.sidebar.session_deleted.connect(self.delete_session)
        main_layout.addWidget(self.sidebar)
        
        # Right Chat Area
        chat_area = QWidget()
        chat_area.setObjectName("ChatArea")
        chat_area.setStyleSheet("""
            QWidget#ChatArea {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(52, 52, 56, 255),
                    stop:0.5 rgba(48, 48, 52, 255),
                    stop:1 rgba(44, 44, 48, 255));
            }
        """)
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)
        
        # Chat Display Area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(55,55,60,100);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(110,110,115,150);
                border-radius: 5px;
                min-height: 30px;
            }
        """)
        
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(16, 8, 16, 8)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()
        
        self.chat_scroll.setWidget(self.chat_container)
        chat_layout.addWidget(self.chat_scroll, 1)
        
        # Input Area
        input_container = QFrame()
        input_container.setObjectName("InputContainer")
        input_container.setFixedHeight(70)
        input_container.setStyleSheet("""
            QFrame#InputContainer {
                background: rgba(58, 58, 62, 220);
                border-radius: 20px;
                border: 1px solid rgba(130,130,135,40);
            }
        """)
        
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 10, 12, 10)
        input_layout.setSpacing(10)
        
        # Attach Button
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setFixedSize(36, 36)
        self.attach_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.attach_btn.setToolTip("Attach Files")
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 15);
                border: none;
                border-radius: 20px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 30);
            }
        """)
        self.attach_btn.clicked.connect(self.attach_files)
        input_layout.addWidget(self.attach_btn)
        
        # Model Selector
        self.model_combo = QComboBox()
        self.model_combo.setFixedWidth(140)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background: rgba(70, 70, 75, 160);
                color: rgba(255,255,255,220);
                border: 1px solid rgba(130,130,135,40);
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background: rgba(60, 60, 65, 240);
                color: rgba(255,255,255,220);
                selection-background-color: rgba(100, 100, 105, 160);
            }
        """)
        self.load_models()
        input_layout.addWidget(self.model_combo)
        
        # Input Field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask anything...")
        self.input_field.setFont(QFont("Segoe UI", 12))
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                color: rgba(255,255,255,240);
                border: none;
                padding: 8px;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.input_field, 1)
        
        # File Badge
        self.file_badge = QLabel("")
        self.file_badge.setStyleSheet("color: rgba(160,160,165,220); font-size: 10px;")
        self.file_badge.hide()
        input_layout.addWidget(self.file_badge)
        
        # Send Button
        self.send_btn = QPushButton("➤")
        self.send_btn.setFixedSize(44, 44)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setFont(QFont("Segoe UI", 16))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(100, 100, 105, 220),
                    stop:1 rgba(120, 120, 125, 220));
                color: white;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(115, 115, 120, 250),
                    stop:1 rgba(135, 135, 140, 250));
            }
            QPushButton:disabled {
                background: rgba(70, 70, 75, 120);
            }
        """)
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_btn)
        
        chat_layout.addWidget(input_container)
        main_layout.addWidget(chat_area, 1)
        
        # State
        self.attached_files = []
        
        # Initialize
        self.load_sidebar()
        self.create_new_chat()
        
        logging.info("ChatWindow initialized.")
    
    def load_models(self):
        """Load available AI models"""
        models = ["gemini-2.5-flash"]
        try:
            import ollama
            info = ollama.list()
            if hasattr(info, 'get') and 'models' in info:
                for m in info['models']:
                    models.append(m['model'])
            elif isinstance(info, list):
                for m in info:
                    models.append(m['model'])
        except Exception:
            models.extend(["llava", "llama3"])
        
        self.model_combo.addItems(models)
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
    
    def on_model_changed(self, model_name):
        self.ai_client.set_model(model_name)
    
    def load_sidebar(self):
        """Load all chat sessions into sidebar"""
        sessions = self.db.get_sessions()
        self.sidebar.load_sessions(sessions)
    
    def create_new_chat(self):
        """Create a new chat session"""
        session_id = self.db.create_session()
        self.sidebar.add_session(session_id, "New Chat")
        self.load_session(session_id)
    
    def load_session(self, session_id):
        """Load a specific chat session"""
        self.current_session_id = session_id
        self.sidebar.set_active_session(session_id)
        
        # Clear current chat display
        self.clear_chat_display()
        
        # Load messages from database
        messages = self.db.get_messages(session_id)
        for msg in messages:
            self.add_chat_bubble(msg['role'], msg['text'], msg['image_path'])
        
        self.scroll_to_bottom()
    
    def delete_session(self, session_id):
        """Delete a chat session"""
        self.db.delete_session(session_id)
        self.sidebar.remove_session(session_id)
        
        # If we deleted the active session, create a new one
        if session_id == self.current_session_id:
            self.create_new_chat()
    
    def clear_chat_display(self):
        """Clear all chat bubbles"""
        for i in reversed(range(self.chat_layout.count())):
            widget = self.chat_layout.itemAt(i).widget()
            if widget and not isinstance(widget, type(None)):
                # Skip the stretch item at the end
                if widget.objectName() != "stretch":
                    widget.deleteLater()
    
    def add_chat_bubble(self, role, text, image_path=None):
        """Add a chat bubble to the display"""
        bubble = ChatBubble(role, text, image_path)
        
        # Create a container for alignment control
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        if role == 'user':
            # User on right - 30% space, 70% bubble
            container_layout.addStretch(3)
            container_layout.addWidget(bubble, 7)
        else:
            # AI on left - 70% bubble, 30% space
            container_layout.addWidget(bubble, 7)
            container_layout.addStretch(3)
        
        # Insert before the stretch
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, container)
        
        self.scroll_to_bottom()
    
    def scroll_to_bottom(self):
        """Scroll chat to bottom"""
        QTimer.singleShot(100, lambda: self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        ))
    
    def attach_files(self):
        """Attach files for context"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Attach Context Files", "",
            "Documents (*.pdf *.txt *.md *.py *.js *.html *.docx)"
        )
        if files:
            self.attached_files.extend(files)
            self.update_file_badge()
    
    def update_file_badge(self):
        """Update file attachment badge"""
        count = len(self.attached_files)
        if count > 0:
            self.file_badge.setText(f"📄 {count} file(s)")
            self.file_badge.show()
        else:
            self.file_badge.hide()
    
    def send_message(self):
        """Send user message to AI"""
        user_input = self.input_field.text().strip()
        if not user_input:
            return
        
        # Clear input
        self.input_field.clear()
        
        # Add user message to chat
        self.add_chat_bubble('user', user_input)
        
        # Save to database
        self.db.add_message(self.current_session_id, 'user', user_input, file_paths=self.attached_files)
        
        # Reload sidebar to update session title
        self.load_sidebar()
        self.sidebar.set_active_session(self.current_session_id)
        
        # Prepare conversation history
        history = self.build_conversation_history()
        
        # Send to AI
        self.send_btn.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # Create AI response bubble (initially empty)
        self.current_response_text = ""
        self.current_response_bubble = ChatBubble('model', "")
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.current_response_bubble)
        self.chat_layout.setAlignment(self.current_response_bubble, Qt.AlignmentFlag.AlignLeft)
        
        # Start AI worker
        # --- FIX: Pass a COPY of the list, not the reference ---
        self.current_worker = AIWorker(self.ai_client, history, list(self.attached_files))
        
        self.current_worker.chunk_received.connect(self.on_chunk_received)
        self.current_worker.finished.connect(self.on_ai_finished)
        self.current_worker.error.connect(self.on_ai_error)
        self.current_worker.start()
        
        # Clear attachments
        self.attached_files.clear()
        self.update_file_badge()
    
    def build_conversation_history(self):
        """Build conversation history for AI"""
        messages = self.db.get_messages(self.current_session_id)
        history = []
        
        for msg in messages:
            history.append({
                'role': msg['role'],
                'text': msg['text'],
                'images': [msg['image_path']] if msg['image_path'] else []
            })
        
        return history
    
    def on_chunk_received(self, chunk):
        """Handle streaming AI response chunks"""
        self.current_response_text += chunk
        
        # Update the bubble's text using the stored text_widget reference
        if (hasattr(self, 'current_response_bubble') and 
            self.current_response_bubble and 
            hasattr(self.current_response_bubble, 'text_widget')):
            try:
                self.current_response_bubble.text_widget.setPlainText(self.current_response_text)
            except RuntimeError:
                # Widget was deleted, ignore
                pass
        
        self.scroll_to_bottom()
    
    def on_ai_finished(self):
        """Handle AI response completion"""
        # Save to database
        self.db.add_message(self.current_session_id, 'model', self.current_response_text)
        
        # Re-enable input
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        
        # Cleanup
        self.current_worker = None
        self.current_response_bubble = None
        if hasattr(self, 'current_response_container'):
            self.current_response_container = None
    
    def on_ai_error(self, error_msg):
        """Handle AI errors"""
        # Remove the empty bubble
        if self.current_response_bubble:
            self.current_response_bubble.deleteLater()
            self.current_response_bubble = None
        
        # Show error bubble
        self.add_chat_bubble('model', f"❌ Error: {error_msg}")
        
        # Re-enable input
        self.send_btn.setEnabled(True)
        self.input_field.setEnabled(True)
    
    def handle_capture(self, image_path, prompt, attached_files, model):
        """Handle screen capture from Canvas overlay"""
        # Ensure we have an active session
        if not self.current_session_id:
            self.create_new_chat()
        
        # Show the chat window
        self.showMaximized()
        self.raise_()
        self.activateWindow()
        
        # Set the model
        if model:
            idx = self.model_combo.findText(model)
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)
        
        # If we have an image, make sure we're using a vision-capable model
        if image_path:
            gemini_idx = self.model_combo.findText("gemini-2.5-flash")
            if gemini_idx >= 0:
                self.model_combo.setCurrentIndex(gemini_idx)
                logging.info("Auto-switched to Gemini for image analysis")
        
        # Set the prompt
        if prompt:
            self.input_field.setText(prompt)
        
        # Add attached files
        if attached_files:
            self.attached_files.extend(attached_files)
            self.update_file_badge()
        
        # Add the screenshot to user message
        if image_path:
            logging.info(f"Received image path: {image_path}")
            
            # Convert to absolute path if relative
            if not os.path.isabs(image_path):
                image_path = os.path.abspath(image_path)
            
            if not os.path.exists(image_path):
                logging.error(f"Captured image not found: {image_path}")
                return
            
            # Save user message with image
            self.db.add_message(self.current_session_id, 'user', prompt or "Analyze this image", image_path)
            
            # Display user bubble with image
            self.add_chat_bubble('user', prompt or "Analyze this image", image_path)
            
            # Reload sidebar
            self.load_sidebar()
            self.sidebar.set_active_session(self.current_session_id)
            
            # FORCE Gemini provider for image analysis
            self.ai_client.set_model("gemini-2.5-flash")
            
            # Prepare history and send to AI
            history = self.build_conversation_history()
            
            self.send_btn.setEnabled(False)
            self.input_field.setEnabled(False)
            
            # Create AI response bubble
            self.current_response_text = ""
            self.current_response_bubble = ChatBubble('model', "")
            
            # Use container for proper alignment
            response_container = QWidget()
            container_layout = QHBoxLayout(response_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            
            container_layout.addWidget(self.current_response_bubble, 7)
            container_layout.addStretch(3)
            
            self.chat_layout.insertWidget(self.chat_layout.count() - 1, response_container)
            self.current_response_container = response_container
            
            # Start AI worker
            # --- FIX: Pass a COPY of the list ---
            self.current_worker = AIWorker(self.ai_client, history, list(self.attached_files))
            
            self.current_worker.chunk_received.connect(self.on_chunk_received)
            self.current_worker.finished.connect(self.on_ai_finished)
            self.current_worker.error.connect(self.on_ai_error)
            self.current_worker.start()
            
            # Clear attachments
            self.attached_files.clear()
            self.update_file_badge()
            self.input_field.clear()