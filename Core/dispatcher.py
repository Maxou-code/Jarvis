import json
import traceback

from config import MAX_ERROR_DETAILS
from Tools.apps import get_open_windows, list_installed_apps, open_app
from Tools.calc import calculate, get_current_datetime
from Tools.cad import create_3d_model, read_cadquery_guide
from Tools.charts import plot_chart
from Tools.files import (backup_config, create_file, create_folder, list_managed_files,
                         open_file, open_workspace, read_file, read_managed_file,
                         restore_config, write_file, write_managed_file)
from Tools.engineering import (
    create_technical_report,
    simulate_ode,
    solve_linear_system,
)
from Tools.keyboard import hotkey, press_key, type_text
from Tools.knowledge import knowledge_list, knowledge_save, knowledge_search
from Tools.mouse import (click_mouse, drag_mouse, move_mouse, mouse_down, mouse_up,
                         release_all_mouse_buttons, scroll_mouse)
from Tools.notifications import notify_user
from Tools.python_runner import list_python_packages, run_python
from Tools.screen import capture_screen
from Tools.web import web_search

FUNCTIONS = {
    "get_current_datetime": get_current_datetime,
    "calculate": calculate,
    "solve_linear_system": solve_linear_system,
    "simulate_ode": simulate_ode,
    "create_technical_report": create_technical_report,
    "web_search": web_search,
    "run_python": run_python,
    "list_python_packages": list_python_packages,
    "list_managed_files": list_managed_files,
    "read_managed_file": read_managed_file,
    "write_managed_file": write_managed_file,
    "backup_config": backup_config,
    "restore_config": restore_config,
    "knowledge_save": knowledge_save,
    "knowledge_search": knowledge_search,
    "knowledge_list": knowledge_list,
    "plot_chart": plot_chart,
    "create_3d_model": create_3d_model,
    "read_cadquery_guide": read_cadquery_guide,
    "create_file": create_file,
    "create_folder": create_folder,
    "write_file": write_file,
    "read_file": read_file,
    "open_file": open_file,
    "open_workspace": open_workspace,
    "list_installed_apps": list_installed_apps,
    "get_open_windows": get_open_windows,
    "open_app": open_app,
    "move_mouse": move_mouse,
    "click_mouse": click_mouse,
    "mouse_down": mouse_down,
    "mouse_up": mouse_up,
    "drag_mouse": drag_mouse,
    "release_all_mouse_buttons": release_all_mouse_buttons,
    "scroll_mouse": scroll_mouse,
    "type_text": type_text,
    "press_key": press_key,
    "hotkey": hotkey,
    "notify_user": notify_user,
}
def execute_tool(name, args):
    if name not in FUNCTIONS:
        return json.dumps({
            "success": False,
            "tool": name,
            "error_type": "UnknownTool",
            "error": f"Outil inconnu : {name}",
            "suggestion": "Utilise uniquement les outils disponibles."
        }, ensure_ascii=False)

    try:
        result = FUNCTIONS[name](**args)

        print(f"[OK] {name} — {result}")

        return json.dumps({
            "success": True,
            "tool": name,
            "result": result if isinstance(result, (dict, list)) else str(result)
        }, ensure_ascii=False)

    except Exception as error:
        error_details = traceback.format_exc()

        print(f"[ERREUR] {name} — {type(error).__name__}: {error}")

        return json.dumps({
            "success": False,
            "tool": name,
            "arguments": args,
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": error_details[-MAX_ERROR_DETAILS:],
            "instruction": (
                "Analyse cette erreur. Identifie sa cause, "
                "corrige les arguments ou choisis une autre méthode, "
                "puis réessaie si cela est raisonnable."
                if name != "create_3d_model" else
                "Analyse cette erreur, puis consulte obligatoirement "
                "read_cadquery_guide avant de corriger le script ou de réessayer."
            )
        }, ensure_ascii=False)
def normalize_tool_arguments(arguments):
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        return json.loads(arguments) if arguments.strip() else {}
    raise ValueError("Format des arguments d'outil invalide.")
