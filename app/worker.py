import os
import ollama
from PyQt6.QtCore import QThread, pyqtSignal
from google.genai import types

def read_file_content(path):
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(path)
            return "\n".join([page.extract_text() for page in reader.pages])
        elif ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml']:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"[Could not read file type: {ext}]"
    except Exception as e:
        return f"[Error reading {os.path.basename(path)}: {str(e)}]"

class AIWorker(QThread):
    finished = pyqtSignal() 
    chunk_received = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, ai_client, history, attached_files=None):
        super().__init__()
        self.ai_client = ai_client
        self.history = history # Unified format: [{'role': 'user', 'text': '...', 'images': []}]
        self.attached_files = attached_files or []

    def run(self):
        try:
            # 1. Process Attached Files (Append to the LAST user message in history context)
            file_context = ""
            for file_path in self.attached_files:
                filename = os.path.basename(file_path)
                file_content = read_file_content(file_path)
                file_context += f"\n--- FILE: {filename} ---\n{file_content}\n"

            # ==========================================
            # BRANCH: GOOGLE GEMINI (Context Aware)
            # ==========================================
            if self.ai_client.provider == "gemini":
                if not self.ai_client.gemini_client:
                    raise Exception("Gemini API Key not found.")

                gemini_contents = []
                
                # Convert History to Gemini Format
                for i, msg in enumerate(self.history):
                    parts = []
                    
                    # Add Text
                    text_content = msg['text']
                    # If this is the latest message, add the file context
                    if i == len(self.history) - 1 and file_context:
                        text_content = f"CONTEXT FROM FILES:\n{file_context}\n\nQUERY: {text_content}"
                        
                    parts.append(types.Part.from_text(text=text_content))
                    
                    # Add Images
                    for img_path in msg['images']:
                        with open(img_path, "rb") as f:
                            img_data = f.read()
                            parts.append(types.Part.from_bytes(data=img_data, mime_type="image/png"))
                    
                    # Role Mapping (user -> user, model -> model)
                    gemini_contents.append(types.Content(role=msg['role'], parts=parts))

                response_stream = self.ai_client.gemini_client.models.generate_content_stream(
                    model=self.ai_client.model_name,
                    contents=gemini_contents
                )

                for chunk in response_stream:
                    if chunk.text:
                        self.chunk_received.emit(chunk.text)

            # ==========================================
            # BRANCH: OLLAMA (Context Aware)
            # ==========================================
            elif self.ai_client.provider == "ollama":
                ollama_messages = []
                
                for i, msg in enumerate(self.history):
                    content = msg['text']
                    # Add file context to the last message
                    if i == len(self.history) - 1 and file_context:
                        content = f"CONTEXT FROM FILES:\n{file_context}\n\nQUERY: {content}"

                    # Ollama role mapping: 'model' -> 'assistant'
                    role = 'assistant' if msg['role'] == 'model' else 'user'
                    
                    message_dict = {
                        'role': role,
                        'content': content
                    }
                    
                    # Handle images (Ollama python lib takes paths directly)
                    if msg['images']:
                        message_dict['images'] = msg['images']
                        
                    ollama_messages.append(message_dict)

                stream = ollama.chat(
                    model=self.ai_client.model_name,
                    messages=ollama_messages,
                    stream=True
                )

                for chunk in stream:
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        self.chunk_received.emit(content)

            self.finished.emit()

        except Exception as e:
            self.error.emit(f"AI Error ({self.ai_client.provider}): {str(e)}")