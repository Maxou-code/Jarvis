import pyautogui

from Tools.screen import screenshot_to_desktop_coordinates

VALID_MOUSE_BUTTONS = {"left", "right", "middle"}
HELD_MOUSE_BUTTONS = set()
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15

def validate_mouse_button(button):
    if button not in VALID_MOUSE_BUTTONS:
        raise ValueError(
            "Bouton invalide. Valeurs : left, right, middle."
        )
def move_mouse(x, y, duration=0.2):
    real_x, real_y = screenshot_to_desktop_coordinates(x, y)

    duration = float(duration)

    if not 0 <= duration <= 10:
        raise ValueError("La durée doit être comprise entre 0 et 10 secondes.")

    pyautogui.moveTo(
        real_x,
        real_y,
        duration=duration
    )

    return (
        f"Souris déplacée vers ({x}, {y}), "
        f"durée : {duration}s."
    )
def click_mouse(x, y, button="left", clicks=1):
    validate_mouse_button(button)

    if not isinstance(clicks, int) or not 1 <= clicks <= 3:
        raise ValueError("Le nombre de clics doit être compris entre 1 et 3.")

    real_x, real_y = screenshot_to_desktop_coordinates(x, y)

    pyautogui.click(
        real_x,
        real_y,
        button=button,
        clicks=clicks,
        interval=0.12
    )

    return f"{clicks} clic(s) {button} effectué(s) en ({x}, {y})."
def mouse_down(button="left", x=None, y=None):
    validate_mouse_button(button)

    if (x is None) != (y is None):
        raise ValueError("Il faut fournir x et y ensemble.")

    if x is not None:
        real_x, real_y = screenshot_to_desktop_coordinates(x, y)
        pyautogui.moveTo(real_x, real_y, duration=0.1)

    pyautogui.mouseDown(button=button)
    HELD_MOUSE_BUTTONS.add(button)

    return f"Bouton {button} maintenu."
def mouse_up(button="left"):
    validate_mouse_button(button)

    pyautogui.mouseUp(button=button)
    HELD_MOUSE_BUTTONS.discard(button)

    return f"Bouton {button} relâché."
def drag_mouse(
        start_x,
        start_y,
        end_x,
        end_y,
        button="left",
        duration=0.8
):
    validate_mouse_button(button)

    duration = float(duration)

    if not 0.05 <= duration <= 15:
        raise ValueError(
            "La durée du glissement doit être comprise entre 0.05 et 15 secondes."
        )

    real_start = screenshot_to_desktop_coordinates(start_x, start_y)
    real_end = screenshot_to_desktop_coordinates(end_x, end_y)

    try:
        pyautogui.moveTo(
            real_start[0],
            real_start[1],
            duration=0.15
        )

        pyautogui.mouseDown(button=button)
        HELD_MOUSE_BUTTONS.add(button)

        pyautogui.moveTo(
            real_end[0],
            real_end[1],
            duration=duration
        )

    finally:
        # Évite de laisser un bouton enfoncé en cas d'erreur.
        pyautogui.mouseUp(button=button)
        HELD_MOUSE_BUTTONS.discard(button)

    return (
        f"Glissement {button} effectué : "
        f"({start_x}, {start_y}) vers ({end_x}, {end_y}), "
        f"durée {duration}s."
    )
def release_all_mouse_buttons():
    for button in list(HELD_MOUSE_BUTTONS):
        try:
            pyautogui.mouseUp(button=button)
        except Exception:
            pass
        finally:
            HELD_MOUSE_BUTTONS.discard(button)

    return "Tous les boutons de souris ont été relâchés."
def scroll_mouse(amount):
    if not isinstance(amount, int) or not -10 <= amount <= 10:
        raise ValueError("Le défilement doit être un entier entre -10 et 10.")

    pyautogui.scroll(amount)
    return f"Défilement effectué ({amount})."
