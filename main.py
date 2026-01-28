import sys
import os
import logging
# 1. ADDED QStyle to imports
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyle
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QObject, pyqtSignal, Qt
import keyboard

from app.ui import GhostUI
from app.chat_ui import ChatWindow
from app.ai_client import AIClient

# --- DEV LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class HotkeyBridge(QObject):
    triggered = pyqtSignal()

def create_tray_icon(app, ghost_window):
    # 2. FIXED: Use QStyle.StandardPixmap.SP_ComputerIcon
    icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    
    tray_icon = QSystemTrayIcon(icon, app)
    tray_icon.setToolTip("Canvas Copilot (Alt+Q)")

    menu = QMenu()
    
    # Action: Open Overlay
    action_open = QAction("Annotate Screen (Alt+Q)", app)
    action_open.triggered.connect(lambda: ghost_window.showFullScreen())
    menu.addAction(action_open)

    menu.addSeparator()

    # Action: Exit
    action_exit = QAction("Exit", app)
    action_exit.triggered.connect(app.quit)
    menu.addAction(action_exit)

    tray_icon.setContextMenu(menu)
    tray_icon.show()
    return tray_icon

if __name__ == "__main__":
    # Fix DPI Scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Don't quit just because windows are hidden (System Tray Mode)
    app.setQuitOnLastWindowClosed(False)

    try:
        logging.info("Initializing Backend...")
        ai_client = AIClient()
        
        # Init Windows
        chat_win = ChatWindow(ai_client)
        
        ghost_win = GhostUI(ai_client)
        ghost_win.capture_completed.connect(chat_win.handle_capture)
        ghost_win.hide() 

        # Init System Tray
        tray = create_tray_icon(app, ghost_win)
        
        # Init Hotkeys
        bridge = HotkeyBridge()
        
        def show_overlay_safe():
            if not ghost_win.isVisible():
                ghost_win.clear_all() 
                ghost_win.showFullScreen() 
                ghost_win.raise_()
                ghost_win.activateWindow()
            else:
                logging.info("Overlay is already active.")
        
        bridge.triggered.connect(show_overlay_safe)
        
        # Register Hotkey (Alt+Q)
        keyboard.add_hotkey('alt+q', lambda: bridge.triggered.emit())

        logging.info("-------------------------------------------")
        logging.info("Canvas Copilot Ready!")
        logging.info("1. Minimized to System Tray (Bottom Right)")
        logging.info("2. Press Alt+Q to open the overlay")
        logging.info("-------------------------------------------")
        
        sys.exit(app.exec())
        
    except Exception as e:
        logging.critical(f"Startup Error: {e}", exc_info=True)
        sys.exit(1)