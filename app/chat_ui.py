

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QScrollArea, QLabel, QFileDialog, QFrame,
    QComboBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QPainter, QPainterPath
import markdown
import ollama  # pip install ollama

from .worker import AIWorker

class ChatBubble(QFrame):
    def __init__(self, text="", is_user=False, image_path=None):
        super().__init__()
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 10, 15, 10)
        
        self.is_user = is_user
        self.raw_text = text  # Store raw text for appending chunks

        # If there's an image (User screenshot)
        if image_path:
            img_lbl = QLabel()
            img_lbl.setText(f"📸 [Screenshot attached]") 
            img_lbl.setStyleSheet("color: rgba(255,255,255,150); font-style: italic;")
            self.layout.addWidget(img_lbl)

        # Message Text Label
        self.msg = QLabel()
        self.msg.setWordWrap(True)
        self.msg.setTextFormat(Qt.TextFormat.RichText)
        self.msg.setOpenExternalLinks(True) 
        
        # Initial Render
        self.render_text()
        self.layout.addWidget(self.msg)

        # Styling
        if is_user:
            self.setStyleSheet("""
                ChatBubble {
                    background-color: rgba(70, 70, 90, 180);
                    border-radius: 15px;
                    border-bottom-right-radius: 2px;
                }
            """)
        else:
            self.setStyleSheet("""
                ChatBubble {
                    background-color: rgba(40, 40, 50, 150);
                    border-radius: 15px;
                    border-bottom-left-radius: 2px;
                    border: 1px solid rgba(255,255,255,30);
                }
            """)

    def append_text(self, chunk):
        """Streaming support: append chunk and re-render"""
        self.raw_text += chunk
        self.render_text()

    def render_text(self):
        """Renders raw_text to HTML/Markdown"""
        if not self.is_user:
            # Markdown to HTML
            try:
                html = markdown.markdown(self.raw_text, extensions=['fenced_code', 'codehilite'])
            except Exception:
                html = self.raw_text # Fallback
            
            # Wrap in styling for readable text
            self.msg.setText(f"<div style='color: #eee; font-family: Segoe UI, sans-serif; line-height: 1.4;'>{html}</div>")
            self.msg.setStyleSheet("background: transparent;")
        else:
            self.msg.setText(self.raw_text)
            self.msg.setStyleSheet("color: white; background: transparent;")


class ChatWindow(QWidget):
    def __init__(self, ai_client):
        super().__init__()
        self.ai_client = ai_client
        self.worker = None
        self.current_ai_bubble = None # Track the active bubble being streamed to
        self.accumulated_response = "" # Temp store for current AI response
        
        # --- MEMORY: Store conversation history ---
        # Format: [{'role': 'user', 'text': '...', 'images': []}, ...]
        self.history = [] 

        # Window Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(450, 650)
        
        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        
        # Glass Container
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.addWidget(self.container)

        # --- HEADER ---
        header = QHBoxLayout()
        title = QLabel("🔮")
        title.setStyleSheet("color: white; font-size: 16px;")
        header.addWidget(title)
        
        # Model Selector (Dropdown)
        self.model_combo = QComboBox()
        
        # --- DYNAMIC MODEL FETCHING ---
        available_models = ["gemini-2.0-flash"]
        try:
            # Try to fetch models from Ollama
            models_info = ollama.list()
            # Depending on ollama version, structure varies
            if hasattr(models_info, 'get') and 'models' in models_info:
                for m in models_info['models']:
                    available_models.append(m['model'])
            elif isinstance(models_info, list):
                for m in models_info:
                    available_models.append(m['model'])
        except Exception as e:
            print(f"Ollama detection failed: {e}")
            # Fallbacks if Ollama isn't running
            available_models.extend(["llava", "llama3"])
            
        self.model_combo.addItems(available_models)
        self.model_combo.setFixedWidth(140)
        self.model_combo.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,20);
                color: white; border: none; border-radius: 8px;
                padding: 4px 10px; font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background: rgb(40, 40, 50); color: white;
            }
        """)
        self.model_combo.currentTextChanged.connect(self.change_model)
        header.addWidget(self.model_combo)

        header.addStretch()
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(24, 24)
        btn_close.clicked.connect(self.hide)
        btn_close.setStyleSheet("background: transparent; color: #aaa; border: none;")
        header.addWidget(btn_close)
        
        self.container_layout.addLayout(header)

        # --- CHAT AREA ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical { width: 8px; background: rgba(0,0,0,0.1); }
            QScrollBar::handle:vertical { background: rgba(255,255,255,0.2); border-radius: 4px; }
        """)
        
        self.chat_content = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.addStretch() 
        self.chat_layout.setSpacing(10)
        self.scroll.setWidget(self.chat_content)
        self.container_layout.addWidget(self.scroll)

        # --- INPUT AREA ---
        input_row = QHBoxLayout()
        
        self.btn_file = QPushButton("📎")
        self.btn_file.setFixedSize(32, 32)
        self.btn_file.clicked.connect(self.upload_file)
        self.btn_file.setStyleSheet("background: rgba(255,255,255,20); border-radius: 16px; color: white;")
        
        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText("Ask a follow up...")
        self.input_box.setFixedHeight(40)
        self.input_box.setStyleSheet("""
            QTextEdit {
                background: rgba(30, 30, 40, 200);
                border: 1px solid rgba(255,255,255,50);
                border-radius: 20px;
                color: white;
                padding: 8px 15px;
            }
        """)
        
        self.btn_send = QPushButton("➤")
        self.btn_send.setFixedSize(32, 32)
        self.btn_send.clicked.connect(lambda: self.handle_user_input(self.input_box.toPlainText()))
        self.btn_send.setStyleSheet("background: rgba(100, 100, 255, 180); border-radius: 16px; color: white;")

        input_row.addWidget(self.btn_file)
        input_row.addWidget(self.input_box)
        input_row.addWidget(self.btn_send)
        self.container_layout.addLayout(input_row)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(self.rect().toRectF(), 20, 20)
        painter.fillPath(path, QColor(20, 20, 30, 240))
        painter.setPen(QColor(255, 255, 255, 40))
        painter.drawPath(path)

    def change_model(self, model_name):
        """Called when user selects from dropdown"""
        self.ai_client.set_model(model_name)

    def add_message(self, text, is_user, image_path=None):
        bubble = ChatBubble(text, is_user, image_path)
        self.chat_layout.insertWidget(self.chat_layout.count()-1, bubble)
        self.scroll_to_bottom()
        return bubble

    def scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def upload_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Add Context", "", "Documents (*.pdf *.txt *.md *.py)")
        if path:
            self.add_message(f"File added: {path}", is_user=True)
            # Add file context to history (invisible to user logic, but useful for worker)
            self.history.append({'role': 'user', 'text': f"Context File Attached: {path}", 'images': []})

    def handle_capture(self, image_path, prompt, attached_files, model_name="gemini-2.0-flash"):
        """Called by GhostUI when screenshot is taken"""
        self.show()
        self.raise_()
        
        # 1. Sync the dropdown with what was chosen on Canvas
        index = self.model_combo.findText(model_name)
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
        
        # 2. Update backend client
        self.ai_client.set_model(model_name)

        # 3. Show user message UI
        display_text = prompt
        if attached_files:
            filenames = [f.split("/")[-1] for f in attached_files]
            display_text += f"\n\n📎 Attached: {', '.join(filenames)}"
            
        self.add_message(display_text, is_user=True, image_path=image_path)
        
        # 4. Update History
        imgs = [image_path] if image_path else []
        self.history.append({'role': 'user', 'text': prompt, 'images': imgs})
        
        # 5. Start AI
        self.start_ai_generation(attached_files)

    def handle_user_input(self, text):
        if not text.strip(): return
        self.input_box.clear()
        
        # 1. Show message
        self.add_message(text, is_user=True)
        
        # 2. Update History
        self.history.append({'role': 'user', 'text': text, 'images': []})
        
        # 3. Start AI
        self.start_ai_generation(attached_files=None)

    def start_ai_generation(self, attached_files=None):
        # Create empty bubble for streaming
        self.current_ai_bubble = self.add_message("", is_user=False)
        self.accumulated_response = ""
        
        # Instantiate worker with FULL HISTORY
        self.worker = AIWorker(self.ai_client, self.history, attached_files)
        
        self.worker.chunk_received.connect(self.on_ai_chunk)
        self.worker.finished.connect(self.on_ai_finished)
        self.worker.error.connect(self.on_ai_error)
        
        self.worker.start()

    def on_ai_chunk(self, chunk_text):
        self.accumulated_response += chunk_text
        if self.current_ai_bubble:
            self.current_ai_bubble.append_text(chunk_text)
            self.scroll_to_bottom()

    def on_ai_finished(self):
        # Save the full response to history so the AI remembers what it said
        if self.accumulated_response:
            self.history.append({'role': 'model', 'text': self.accumulated_response, 'images': []})
            
        self.current_ai_bubble = None
        self.scroll_to_bottom()

    def on_ai_error(self, error_msg):
        self.add_message(f"⚠️ {error_msg}", is_user=False)
        self.current_ai_bubble = None