import sys
from PyQt6.QtWidgets import QApplication
import keyboard
from PyQt6.QtCore import QObject, pyqtSignal

from app.ui import GhostUI
from app.chat_ui import ChatWindow
from app.ai_client import AIClient

class HotkeyBridge(QObject):
    triggered = pyqtSignal()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # 1. Init Backend
    ai_client = AIClient()
    
    # 2. Init Windows (Create them ONCE)
    chat_win = ChatWindow(ai_client)
    
    # Pre-instantiate GhostUI so it's ready in memory
    # We pass chat_win's handler to it once
    ghost_win = GhostUI(ai_client)
    ghost_win.capture_completed.connect(chat_win.handle_capture)
    ghost_win.hide() # Ensure it starts hidden

    bridge = HotkeyBridge()

    def open_overlay():
        bridge.triggered.emit()

    def show_overlay_safe():
        # Check if it's already visible to prevent double-triggering
        if not ghost_win.isVisible():
            # Reset the canvas before showing so old drawings are gone
            ghost_win.clear_all() 
            
            # Use showFullScreen to ensure it covers all monitors/taskbars
            ghost_win.showFullScreen() 
            ghost_win.raise_()
            ghost_win.activateWindow()
        else:
            print("Overlay is already active.")

    bridge.triggered.connect(show_overlay_safe)

    # Hotkey registration
    keyboard.add_hotkey('alt+q', open_overlay)

    print("Canvas Copilot Ready. Press Ctrl+Shift+Space to annotate.")
    sys.exit(app.exec())