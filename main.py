import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import keyboard
from app.ui import GhostUI
from app.ai_client import AIClient

should_pop = False
win = None

def trigger_ui():
    global should_pop
    should_pop = True

if __name__ == "__main__":
    app = QApplication(sys.argv)
    ai_client = AIClient()

    # Hotkey
    keyboard.add_hotkey('ctrl+shift+space', trigger_ui)

    timer = QTimer()
    def check_loop():
        global should_pop, win
        if should_pop:
            should_pop = False
            win = GhostUI(ai_client)
            win.show()

    timer.timeout.connect(check_loop)
    timer.start(100)

    print("Canvas AI Ready. Ctrl+Shift+Space to start.")
    sys.exit(app.exec())
