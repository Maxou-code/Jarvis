from PyQt6.QtCore import QObject, pyqtSignal

from Core.agent import ask_jarvis
from Tools.mouse import release_all_mouse_buttons
from config import THINK_ENABLED

class AgentWorker(QObject):
    token = pyqtSignal(str)
    thinking = pyqtSignal(str)
    response_start = pyqtSignal()
    tool_event = pyqtSignal(str, str, object)
    finished = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, prompt, images=None, think_enabled=THINK_ENABLED):
        super().__init__()
        self.prompt = prompt
        self.images = images or []
        self.think_enabled = think_enabled

    def run(self):
        callbacks = {
            "on_token": self.token.emit,
            "on_thinking": self.thinking.emit,
            "on_response_start": self.response_start.emit,
            "on_tool": lambda state, name, details: self.tool_event.emit(state, name, details)
        }
        try:
            ask_jarvis(
                self.prompt,
                user_images=self.images,
                callbacks=callbacks,
                think_enabled=self.think_enabled,
            )
            self.finished.emit()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            try:
                release_all_mouse_buttons()
            except Exception:
                pass
