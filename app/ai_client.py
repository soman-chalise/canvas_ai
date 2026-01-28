import os
from dotenv import load_dotenv
import logging

# Optional imports (don't crash if library missing)
try:
    from google import genai
except ImportError:
    genai = None

try:
    import ollama
except ImportError:
    ollama = None

load_dotenv()

class AIClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_client = None
        self.provider = "ollama" # Default fallback
        self.model_name = "llama3"

        # 1. Try Gemini
        if self.api_key and genai:
            try:
                self.gemini_client = genai.Client(api_key=self.api_key)
                self.provider = "gemini"
                self.model_name = "gemini-2.0-flash"
                logging.info("AI: Connected to Gemini.")
            except Exception as e:
                logging.error(f"AI: Gemini API Key invalid: {e}")

        # 2. Check Ollama
        if self.provider == "ollama":
            if not ollama:
                logging.warning("AI: Ollama library not installed. AI features will fail.")
            else:
                # Simple ping check
                try:
                    ollama.list()
                    logging.info("AI: Connected to Ollama.")
                except Exception:
                    logging.warning("AI: Ollama server not running (localhost:11434).")

    def set_model(self, model_name):
        self.model_name = model_name
        if "gemini" in model_name.lower() and self.gemini_client:
            self.provider = "gemini"
        else:
            self.provider = "ollama"