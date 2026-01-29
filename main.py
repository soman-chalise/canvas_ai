import sys
import os
import logging
import keyboard # pip install keyboard
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyle
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import QObject, pyqtSignal, Qt

# Import your modules
from app.ui import GhostUI
from app.chat_ui import ChatWindow
from app.ai_client import AIClient

# --- DEV LOGGING ---
# Create formatters
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Create handlers
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_formatter)

# Debug file handler (captures all logs)
debug_file_handler = logging.FileHandler('app_debug.log', mode='a', encoding='utf-8')
debug_file_handler.setLevel(logging.DEBUG)
debug_file_handler.setFormatter(log_formatter)

# Error file handler (captures only errors and critical)
error_file_handler = logging.FileHandler('app_error.log', mode='a', encoding='utf-8')
error_file_handler.setLevel(logging.ERROR)
error_file_handler.setFormatter(log_formatter)

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to capture all logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        console_handler,
        debug_file_handler,
        error_file_handler
    ]
)

class AppController(QObject):
    open_canvas_signal = pyqtSignal() # Thread-safe signal

    def __init__(self, app):
        super().__init__()
        self.app = app
        
        try:
            logging.info("Initializing Backend...")
            
            # 1. Dependency Injection
            self.ai_client = AIClient()
            
            # 2. Init Windows
            self.chat_win = ChatWindow(self.ai_client)
            self.ghost_win = GhostUI(self.ai_client)
            
            # 3. Wiring Signals
            # When Canvas captures -> Send to Chat
            self.ghost_win.capture_completed.connect(self.handle_canvas_capture)
            
            # When Hotkey pressed -> Toggle Canvas
            self.open_canvas_signal.connect(self.toggle_canvas)

            # 4. System Tray
            self.setup_tray()

            # 5. Register Hotkey (Alt+Q)
            # We use a lambda to emit a Qt signal because 'keyboard' runs in a background thread
            try:
                keyboard.add_hotkey('alt+q', lambda: self.open_canvas_signal.emit())
                logging.info("Global Hotkey 'Alt+Q' registered.")
            except ImportError:
                logging.warning("Library 'keyboard' not installed. Hotkeys disabled.")
            except Exception as e:
                logging.error(f"Hotkey Error: {e}")

            # 6. App starts minimally - windows only open when triggered
            # (Chat opens via tray click, Canvas via Alt+Q)

            logging.info("-------------------------------------------")
            logging.info("AI Shell Running")
            logging.info("-> Click Tray Icon to open Chat")
            logging.info("-> Press Alt+Q to open Canvas")
            logging.info("-------------------------------------------")

        except Exception as e:
            logging.critical(f"Startup Error: {e}", exc_info=True)
            sys.exit(1)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self.app)
        
        # --- FIX: Use SP_ComputerIcon instead of the non-existent ShellIcon ---
        icon = self.app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("AI Shell")

        # Context Menu
        menu = QMenu()
        
        action_chat = QAction("Open AI Chat", self.app)
        action_chat.triggered.connect(self.toggle_chat)
        menu.addAction(action_chat)

        action_canvas = QAction("Open Canvas Overlay (Alt+Q)", self.app)
        action_canvas.triggered.connect(self.toggle_canvas)
        menu.addAction(action_canvas)

        menu.addSeparator()

        action_exit = QAction("Exit", self.app)
        action_exit.triggered.connect(self.exit_app)
        menu.addAction(action_exit)

        self.tray_icon.setContextMenu(menu)
        
        # Click tray to toggle chat
        self.tray_icon.activated.connect(lambda reason: self.toggle_chat() if reason in (
            QSystemTrayIcon.ActivationReason.Trigger, 
            QSystemTrayIcon.ActivationReason.DoubleClick
        ) else None)
        
        self.tray_icon.show()

    def toggle_chat(self):
        # Logic: If hidden, show Maximized. 
        if self.chat_win.isVisible():
            self.chat_win.hide()
        else:
            self.chat_win.showMaximized() # <--- CHANGED FROM show()
            self.chat_win.raise_()
            self.chat_win.activateWindow()

    def toggle_canvas(self):
        if self.ghost_win.isVisible():
            self.ghost_win.hide()
        else:
            # Reset before showing
            self.ghost_win.clear_all()
            self.ghost_win.showFullScreen()
            self.ghost_win.raise_()
            self.ghost_win.activateWindow()

    def handle_canvas_capture(self, image_path, prompt, attached_files, model):
        # Open chat and pass the screenshot data
        self.chat_win.handle_capture(image_path, prompt, attached_files, model)

    def exit_app(self):
        self.app.quit()

def main():
    # 1. High DPI Fixes
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.Floor
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running when windows close (Tray mode)

    # Initialize Controller
    controller = AppController(app)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()