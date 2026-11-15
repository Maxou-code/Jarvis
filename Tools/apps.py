import ctypes
import json
import subprocess
import time
from ctypes import wintypes
from pathlib import Path

import pyautogui

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_RESTORE = 9
def _get_process_executable(pid):
    """Retourne le nom de l'exécutable associé à un processus Windows."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD
    ]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD)
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid)
    )
    if not handle:
        return None

    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        success = kernel32.QueryFullProcessImageNameW(
            handle, 0, buffer, ctypes.byref(size)
        )
        return Path(buffer.value).name.lower() if success else None
    finally:
        kernel32.CloseHandle(handle)
def get_open_windows():
    """Retourne les fenêtres Windows visibles avec titre, PID et exécutable."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    windows = []

    EnumWindowsProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )

    user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [
        wintypes.HWND, wintypes.LPWSTR, ctypes.c_int
    ]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND, ctypes.POINTER(wintypes.DWORD)
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD

    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True

        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        title = title_buffer.value.strip()
        if not title:
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        windows.append({
            "title": title,
            "hwnd": int(hwnd),
            "pid": int(pid.value),
            "process": _get_process_executable(pid.value) or "inconnu"
        })
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return json.dumps(windows, ensure_ascii=False, indent=2)
def list_installed_apps():
    """
    Liste les applications enregistrées dans le menu Démarrer Windows.
    Get-StartApps couvre les applications Win32 et Microsoft Store/UWP.
    """
    powershell_script = (
        "Get-StartApps | "
        "Where-Object { $_.Name -and $_.AppID } | "
        "Select-Object Name, AppID | "
        "ConvertTo-Json -Compress"
    )

    result = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-Command", powershell_script
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=25,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )

    if result.returncode != 0:
        details = result.stderr.strip() or "Erreur PowerShell inconnue."
        raise RuntimeError(f"Impossible de lire le menu Démarrer : {details}")

    raw = result.stdout.strip()
    if not raw:
        return "Aucune application indexée dans le menu Démarrer."

    data = json.loads(raw)
    if isinstance(data, dict):
        data = [data]

    unique = {}
    for item in data:
        name = str(item.get("Name", "")).strip()
        app_id = str(item.get("AppID", "")).strip()
        if name and app_id:
            unique[(name.casefold(), app_id.casefold())] = {
                "name": name,
                "app_id": app_id
            }

    apps = sorted(unique.values(), key=lambda item: item["name"].casefold())
    return json.dumps(apps, ensure_ascii=False, indent=2)
def focus_window(hwnd):
    """Restaure et place une fenêtre existante au premier plan."""
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.ShowWindow(hwnd, SW_RESTORE)
    return bool(user32.SetForegroundWindow(hwnd))
def _find_matching_apps(query):
    """Recherche une correspondance exacte, puis partielle, dans le menu Démarrer."""
    query = query.strip().casefold()
    if not query:
        return []

    raw = list_installed_apps()
    if raw.startswith("Aucune application"):
        return []

    apps = json.loads(raw)
    exact = [item for item in apps if item["name"].casefold() == query]
    if exact:
        return exact

    return [item for item in apps if query in item["name"].casefold()]
def _find_matching_open_windows(query):
    """Recherche les fenêtres dont le titre contient le nom demandé."""
    query = query.strip().casefold()
    if not query:
        return []

    windows = json.loads(get_open_windows())
    return [
        window for window in windows
        if query in window["title"].casefold()
    ]
def search_application_from_start_menu(display_name):
    """Lance une application par la recherche du menu Démarrer."""
    pyautogui.press("win")
    time.sleep(0.6)

    try:
        import pyperclip
        pyperclip.copy(display_name)
        pyautogui.hotkey("ctrl", "v")
    except ImportError:
        pyautogui.write(display_name, interval=0.04)

    time.sleep(1.2)
    pyautogui.press("enter")
    time.sleep(2.0)

    matches = _find_matching_open_windows(display_name)
    if len(matches) == 1:
        focus_window(matches[0]["hwnd"])
        return (
            f"Commande de lancement envoyée pour « {display_name} ». "
            f"Fenêtre détectée : « {matches[0]['title']} »."
        )

    return (
        f"Recherche de « {display_name} » validée dans le menu Démarrer. "
        "Le lancement a été demandé, mais aucune fenêtre portant clairement "
        "ce nom n'a pu être identifiée. Vérifie avec get_open_windows ou capture_screen."
    )
def open_app(app):
    """
    Ouvre une application disponible dans le menu Démarrer.
    Réactive une fenêtre existante si son titre correspond sans ambiguïté.
    """
    if not isinstance(app, str) or not app.strip():
        raise ValueError("Indique le nom de l'application à ouvrir.")

    query = app.strip()
    installed_matches = _find_matching_apps(query)

    if not installed_matches:
        raise ValueError(
            f"Aucune application du menu Démarrer ne correspond à « {query} ». "
            "Utilise list_installed_apps pour consulter les noms disponibles."
        )

    if len(installed_matches) > 1:
        names = [item["name"] for item in installed_matches[:15]]
        raise ValueError(
            f"Plusieurs applications correspondent à « {query} » : "
            + ", ".join(names)
            + ". Précise le nom exact."
        )

    display_name = installed_matches[0]["name"]
    open_matches = _find_matching_open_windows(display_name)

    if len(open_matches) == 1:
        focus_window(open_matches[0]["hwnd"])
        return (
            f"« {display_name} » est déjà ouvert. "
            f"Fenêtre réactivée : « {open_matches[0]['title']} »."
        )

    if len(open_matches) > 1:
        titles = [window["title"] for window in open_matches[:10]]
        raise ValueError(
            f"Plusieurs fenêtres correspondent à « {display_name} » : "
            + " ; ".join(titles)
            + ". Précise la fenêtre à utiliser."
        )

    return search_application_from_start_menu(display_name)
