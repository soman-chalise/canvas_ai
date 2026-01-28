import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QStyle
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QObject, pyqtSignal, Qt

# Import your modules
from app.ui import GhostUI
from app.chat_ui import ChatWindow
from app.ai_client import AIClient

# --- DEV LOGGING ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Print to console
        # logging.FileHandler("app.log")   # Uncomment for file logging
    ]
)

def create_tray_icon(app, toggle_callback):
    """
    Creates a system tray icon that toggles the overlay when clicked.
    """
    # Use standard computer icon
    icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    tray_icon = QSystemTrayIcon(icon, app)
    tray_icon.setToolTip("Canvas Copilot")

    # Double click or Single click to toggle
    tray_icon.activated.connect(lambda reason: toggle_callback() if reason in (
        QSystemTrayIcon.ActivationReason.Trigger, 
        QSystemTrayIcon.ActivationReason.DoubleClick
    ) else None)

    # Context Menu
    menu = QMenu()
    
    action_open = QAction("Annotate Screen", app)
    action_open.triggered.connect(toggle_callback)
    menu.addAction(action_open)

    menu.addSeparator()

    action_exit = QAction("Exit", app)
    action_exit.triggered.connect(app.quit)
    menu.addAction(action_exit)

    tray_icon.setContextMenu(menu)
    tray_icon.show()
    return tray_icon

def main():
    # 1. High DPI Fixes (Must be before QApplication)
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Daemon mode

    try:
        logging.info("Initializing Backend...")
        
        # 2. Dependency Injection
        # Initialize the client once here, pass it down
        ai_client = AIClient()
        
        # 3. Init Windows
        # We don't show them yet
        chat_win = ChatWindow(ai_client)
        ghost_win = GhostUI(ai_client)
        
        # 4. Wiring Signals
        # When GhostUI finishes capture -> Open ChatWindow
        ghost_win.capture_completed.connect(chat_win.handle_capture)

        # 5. Toggle Logic
        def toggle_overlay():
            if ghost_win.isVisible():
                ghost_win.hide()
            else:
                # Reset state before showing
                ghost_win.clear_all()
                ghost_win.showFullScreen()
                ghost_win.raise_()
                ghost_win.activateWindow()

        # 6. System Tray
        tray = create_tray_icon(app, toggle_overlay)

        logging.info("-------------------------------------------")
        logging.info("Canvas Copilot Running")
        logging.info("-> Click the System Tray icon to Annotate")
        logging.info("-------------------------------------------")
        
        sys.exit(app.exec())
        
    except Exception as e:
        logging.critical(f"Fatal Startup Error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()