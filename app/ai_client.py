import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

class AIClient:
    def __init__(self):
        # 1. Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_client = None
        if api_key:
            self.gemini_client = genai.Client(api_key=api_key)
        
        # 2. Default Settings
        self.provider = "gemini" if self.gemini_client else "ollama"
        self.model_name = "gemini-2.0-flash" if self.gemini_client else "llama3"

    def set_model(self, model_name):
        self.model_name = model_name
        if "gemini" in model_name.lower():
            self.provider = "gemini"
        else:
            self.provider = "ollama"