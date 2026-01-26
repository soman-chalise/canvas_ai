import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from .ui import ResponseWindow  # Import correctly from the same package

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class AIClient:
    def __init__(self):
        self.client = client
        self.current_window = None # Keep a reference so it doesn't close

    def send_image(self, path, prompt):
        try:
            with open(path, "rb") as f:
                res = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[types.Part.from_bytes(data=f.read(), mime_type="image/png"), prompt]
                )
            
            # Show the response window
            self.current_window = ResponseWindow(res.text)
            self.current_window.show()
            
        except Exception as e:
            print(f"AI Client Error: {e}")