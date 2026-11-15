import ctypes
import sys

# Set DPI awareness before importing PyQt or PyAutoGUI.
try:
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from UI.main_window import JarvisWindow


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    window = JarvisWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
