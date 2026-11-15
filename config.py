from pathlib import Path
import json

MODEL = "Jarvis-3.5"
CONTENT_MAX_WIDTH = 1300   # largeur max de la conversation ET de la barre d'entrée
ENTRY_MAX_WIDTH = 950
CONTENT_SIDE_MARGIN = 34
URL = "http://localhost:11434/api/chat"
WORKSPACE = Path.home() / "Jarvis_Workspace"
WORKSPACE.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = WORKSPACE / "jarvis_config.json"
BACKUP_DIR = WORKSPACE / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

KNOWLEDGE_DB = WORKSPACE / "jarvis_knowledge.sqlite3"
MAX_PYTHON_SECONDS = 30
MAX_PYTHON_3D_MODEL_SECONDS = 600
MAX_PYTHON_OUTPUT = 20_000
MAX_SCRIPT_SIZE = 50_000
MAX_RECOVERY_ATTEMPTS = 3
MAX_ERROR_DETAILS = 5000
MAX_TOOL_ROUNDS = 50
MAX_HISTORY_MESSAGES = 36
MAX_FILE_SIZE = 1_000_000
SCREENSHOT_MAX_SIZE = (2560, 1440)
SCREENSHOT_JPEG_QUALITY = 88
REQUEST_TIMEOUT = (30, 900)
THINK_ENABLED = True


def _load_authorized_dirs():
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return {str(k): str(Path(v).expanduser().resolve()) for k, v in (data.get("authorized_dirs") or {}).items() if Path(v).expanduser().is_dir()}
    except Exception:
        return {}
AUTHORIZED_DIRS = _load_authorized_dirs()

def _save_app_config():
    CONFIG_FILE.write_text(json.dumps({"authorized_dirs": AUTHORIZED_DIRS}, ensure_ascii=False, indent=2), encoding="utf-8")
