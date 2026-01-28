import os
import time
import logging
import ollama
from PyQt6.QtCore import QThread, pyqtSignal
from google.genai import types

def read_file_content(path):
    """Reads content from various file types for AI context."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(path)
            return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif ext in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yaml', '.cpp', '.h']:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        else:
            return f"[Unsupported file type: {ext}]"
    except Exception as e:
        return f"[Error reading {os.path.basename(path)}: {str(e)}]"

class AIWorker(QThread):
    finished = pyqtSignal() 
    chunk_received = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, ai_client, history, attached_files=None):
        super().__init__()
        self.ai_client = ai_client
        self.history = history 
        self.attached_files = attached_files or []

    def run(self):
        try:
            # --- PRODUCTION: Context Pruning ---
            # To stay within free tier limits, send only instructions + last 10 messages
            MAX_MESSAGES = 10
            active_history = self.history
            if len(self.history) > MAX_MESSAGES:
                active_history = self.history[-MAX_MESSAGES:]

            # 1. Process Attached Files into context string
            file_context = ""
            for file_path in self.attached_files:
                if os.path.exists(file_path):
                    filename = os.path.basename(file_path)
                    file_content = read_file_content(file_path)
                    file_context += f"\n--- FILE: {filename} ---\n{file_content}\n"

            # ==========================================
            # GEMINI PROVIDER (with Retry Logic)
            # ==========================================
            if self.ai_client.provider == "gemini":
                if not self.ai_client.gemini_client:
                    raise Exception("Gemini API Key not found.")

                # Prepare Gemini-specific contents format
                gemini_contents = []
                for i, msg in enumerate(active_history):
                    parts = []
                    text_content = msg['text']
                    
                    # Attach file context to the VERY LAST user message
                    if i == len(active_history) - 1 and file_context:
                        text_content = f"CONTEXT FROM FILES:\n{file_context}\n\nUSER QUERY: {text_content}"
                        
                    parts.append(types.Part.from_text(text=text_content))
                    
                    # Attach images (screenshots) if they exist
                    for img_path in msg['images']:
                        if os.path.exists(img_path):
                            with open(img_path, "rb") as f:
                                img_data = f.read()
                                parts.append(types.Part.from_bytes(data=img_data, mime_type="image/jpeg"))
                    
                    gemini_contents.append(types.Content(role=msg['role'], parts=parts))

                # --- RETRY LOOP FOR 429 ERRORS ---
                max_retries = 3
                retry_delay = 5 # seconds
                
                for attempt in range(max_retries):
                    try:
                        response_stream = self.ai_client.gemini_client.models.generate_content_stream(
                            model=self.ai_client.model_name,
                            contents=gemini_contents
                        )

                        for chunk in response_stream:
                            if self.isInterruptionRequested():
                                return
                            if chunk.text:
                                self.chunk_received.emit(chunk.text)
                        
                        # If we reach here, the stream finished successfully
                        break 

                    except Exception as e:
                        err_str = str(e)
                        # If Rate Limited (429) or Server Overloaded (503), wait and retry
                        if ("429" in err_str or "503" in err_str) and attempt < max_retries - 1:
                            logging.warning(f"Gemini Rate Limit hit. Retrying in {retry_delay}s... (Attempt {attempt+1})")
                            time.sleep(retry_delay)
                            retry_delay *= 2 # Exponential backoff
                            continue
                        
                        # If 409 Conflict: user sent request while previous was active
                        elif "409" in err_str:
                            self.error.emit("Conflict: A previous request is still finishing. Please wait 3 seconds.")
                            return
                        
                        # Otherwise, it's a real error
                        else:
                            raise e

            # ==========================================
            # OLLAMA PROVIDER
            # ==========================================
            elif self.ai_client.provider == "ollama":
                ollama_messages = []
                
                for i, msg in enumerate(active_history):
                    content = msg['text']
                    if i == len(active_history) - 1 and file_context:
                        content = f"CONTEXT FROM FILES:\n{file_context}\n\nUSER QUERY: {content}"

                    role = 'assistant' if msg['role'] == 'model' else 'user'
                    message_dict = {'role': role, 'content': content}
                    
                    valid_images = [img for img in msg['images'] if os.path.exists(img)]
                    if valid_images:
                        message_dict['images'] = valid_images
                        
                    ollama_messages.append(message_dict)

                stream = ollama.chat(
                    model=self.ai_client.model_name,
                    messages=ollama_messages,
                    stream=True
                )

                for chunk in stream:
                    if self.isInterruptionRequested():
                        return
                    content = chunk.get('message', {}).get('content', '')
                    if content:
                        self.chunk_received.emit(content)

            self.finished.emit()

        except Exception as e:
            # Final User-Friendly Error Mapping
            error_msg = str(e)
            if "429" in error_msg:
                self.error.emit("Rate limit reached. The free tier allows about 15 requests per minute. Please slow down.")
            elif "quota" in error_msg.lower():
                self.error.emit("Daily API quota exhausted. Try again tomorrow or use a different model.")
            else:
                self.error.emit(f"AI Error: {error_msg}")