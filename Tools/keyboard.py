import pyautogui

ALLOWED_KEYS = {
    "enter", "tab", "space", "esc",
    "up", "down", "left", "right",
    "home", "end", "pageup", "pagedown",
    "backspace", "delete",
    "f1", "f2", "f3", "f4", "f5", "f6", "f10"
}
def type_text(text):
    if not isinstance(text, str):
        raise ValueError("Le texte doit être une chaîne.")
    if len(text) > 5000:
        raise ValueError("Texte trop long (maximum 5000 caractères).")
    # clipboard permet de mieux gérer les accents et caractères Unicode sous Windows.
    try:
        import pyperclip
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    except ImportError:
        # Repli compatible ASCII si pyperclip n'est pas installé.
        pyautogui.write(text, interval=0.005)
    return f"Texte saisi ({len(text)} caractères)."
ALLOWED_HOTKEYS = {
    ("ctrl", "s"),
    ("ctrl", "a"),
    ("ctrl", "c"),
    ("ctrl", "v"),
    ("ctrl", "z"),
    ("ctrl", "y"),
    ("ctrl", "f"),
    ("ctrl", "w"),
    ("alt", "tab"),
    ("alt", "f4"),
    ("win", "e")
}
def press_key(key):
    key = key.lower()
    if key not in ALLOWED_KEYS:
        raise ValueError("Touche non autorisée.")
    pyautogui.press(key)
    return f"Touche pressée : {key}"
def hotkey(keys):
    normalized = tuple(key.lower() for key in keys)
    if normalized not in ALLOWED_HOTKEYS:
        raise ValueError("Combinaison de touches non autorisée.")
    pyautogui.hotkey(*normalized)
    return f"Raccourci exécuté : {'+'.join(normalized)}"
