from threading import Event, Lock

from PyQt6.QtCore import QObject, pyqtSignal

from Core.agent import ask_jarvis
from Tools.mouse import release_all_mouse_buttons
from config import THINK_ENABLED

class AgentWorker(QObject):
    token = pyqtSignal(str, str)
    thinking = pyqtSignal(str, str)
    response_start = pyqtSignal(str)
    tool_event = pyqtSignal(str, str, str, object)
    finished = pyqtSignal(str)
    failed = pyqtSignal(str, str)

    def __init__(
        self, prompt, conversation_id, images=None, think_enabled=THINK_ENABLED,
        engineering_mode=False,
    ):
        super().__init__()
        self.prompt = prompt
        self.conversation_id = conversation_id
        self.images = images or []
        self.think_enabled = think_enabled
        self.engineering_mode = engineering_mode
        self._cancel_event = Event()
        self._response_lock = Lock()
        self._active_response = None

    def cancel(self):
        self._cancel_event.set()
        with self._response_lock:
            if self._active_response is not None:
                self._active_response.close()

    def _set_active_response(self, response):
        with self._response_lock:
            self._active_response = response
            if response is not None and self._cancel_event.is_set():
                response.close()

    def run(self):
        callbacks = {
            "on_token": lambda token: self.token.emit(self.conversation_id, token),
            "on_thinking": lambda token: self.thinking.emit(self.conversation_id, token),
            "on_response_start": lambda: self.response_start.emit(self.conversation_id),
            "on_tool": lambda state, name, details: self.tool_event.emit(
                self.conversation_id, state, name, details
            ),
            "on_stream_response": self._set_active_response,
        }
        try:
            ask_jarvis(
                self.prompt,
                user_images=self.images,
                callbacks=callbacks,
                think_enabled=self.think_enabled,
                cancel_event=self._cancel_event,
                engineering_mode=self.engineering_mode,
            )
            self.finished.emit(self.conversation_id)
        except Exception as exc:
            self.failed.emit(self.conversation_id, f"{type(exc).__name__}: {exc}")
        finally:
            try:
                release_all_mouse_buttons()
            except Exception:
                pass
