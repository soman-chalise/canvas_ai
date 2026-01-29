import os
from dotenv import load_dotenv
import logging

# Wrappers for potential libraries
try:
    from google import genai
except ImportError:
    genai = None

try:
    import ollama
except ImportError:
    ollama = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

try:
    import anthropic
except ImportError:
    anthropic = None

load_dotenv()

class AIClient:
    def __init__(self):
        self.provider = "ollama" # Default
        self.model_name = "llama3"
        
        # 1. Setup Gemini
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.gemini_client = None
        if self.gemini_key and genai:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_key)
                logging.info("AI: Gemini Driver Loaded.")
            except Exception as e:
                logging.error(f"AI: Gemini Error: {e}")

        # 2. Setup OpenAI (Architecture ready)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = None
        if self.openai_key and OpenAI:
            self.openai_client = OpenAI(api_key=self.openai_key)
            logging.info("AI: OpenAI Driver Loaded.")

        # 3. Setup Anthropic (Architecture ready)
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        self.anthropic_client = None
        if self.anthropic_key and anthropic:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)
            logging.info("AI: Anthropic Driver Loaded.")

    def set_model(self, model_name):
        self.model_name = model_name
        
        # Logic to switch providers based on model name selection
        if "gemini" in model_name.lower():
            self.provider = "gemini"
        elif "gpt" in model_name.lower():
            self.provider = "openai"
        elif "claude" in model_name.lower():
            self.provider = "anthropic"
        else:
            self.provider = "ollama"