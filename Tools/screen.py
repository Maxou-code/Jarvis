import base64
import io

import mss
import pyautogui
from PIL import Image

from config import SCREENSHOT_JPEG_QUALITY, SCREENSHOT_MAX_SIZE

LAST_SCREENSHOT_SIZE = None
LAST_MONITOR_INFO = None

def capture_screen():
    """
    Capture l'écran principal.
    Les coordonnées envoyées au modèle correspondent exactement
    à l'image reçue, même si celle-ci a été redimensionnée.
    Une grille discrète aide le modèle à localiser les éléments.
    """
    global LAST_SCREENSHOT_SIZE, LAST_MONITOR_INFO

    with mss.MSS() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)

        screenshot = Image.frombytes(
            "RGB",
            shot.size,
            shot.rgb
        )

    source_width, source_height = screenshot.size

    # Mémorise la géométrie réelle du moniteur capturé.
    LAST_MONITOR_INFO = {
        "left": monitor["left"],
        "top": monitor["top"],
        "width": source_width,
        "height": source_height
    }

    # Redimensionnement proportionnel, sans déformation.
    screenshot.thumbnail(
        SCREENSHOT_MAX_SIZE,
        Image.Resampling.LANCZOS
    )

    width, height = screenshot.size
    LAST_SCREENSHOT_SIZE = (width, height)

    buffer = io.BytesIO()

    screenshot.save(
        buffer,
        format="JPEG",
        quality=SCREENSHOT_JPEG_QUALITY,
        optimize=True
    )

    encoded = base64.b64encode(
        buffer.getvalue()
    ).decode("ascii")

    return encoded, width, height
def screenshot_to_desktop_coordinates(x, y):
    """
    Convertit les coordonnées de l'image envoyée au modèle
    vers les coordonnées physiques du bureau Windows.

    Refuse de cliquer si la géométrie de l'écran est incohérente.
    """
    if LAST_SCREENSHOT_SIZE is None or LAST_MONITOR_INFO is None:
        raise RuntimeError(
            "Aucune capture récente. Appelle capture_screen avant le clic."
        )

    if isinstance(x, bool) or isinstance(y, bool):
        raise ValueError("Les coordonnées doivent être numériques.")

    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise ValueError("Les coordonnées doivent être numériques.")

    image_width, image_height = LAST_SCREENSHOT_SIZE

    monitor_left = LAST_MONITOR_INFO["left"]
    monitor_top = LAST_MONITOR_INFO["top"]
    monitor_width = LAST_MONITOR_INFO["width"]
    monitor_height = LAST_MONITOR_INFO["height"]

    if not (0 <= x < image_width and 0 <= y < image_height):
        raise ValueError(
            f"Coordonnées hors capture : ({x}, {y}). "
            f"Image : {image_width}x{image_height}."
        )

    desktop_width, desktop_height = pyautogui.size()

    # On vérifie que PyAutoGUI et MSS parlent bien du même écran.
    if (
            desktop_width != monitor_width
            or desktop_height != monitor_height
    ):
        raise RuntimeError(
            "Les dimensions MSS et PyAutoGUI ne correspondent pas. "
            f"MSS : {monitor_width}x{monitor_height}, "
            f"PyAutoGUI : {desktop_width}x{desktop_height}. "
            "Clic annulé pour éviter une mauvaise position."
        )

    scale_x = monitor_width / image_width
    scale_y = monitor_height / image_height

    real_x = round(monitor_left + x * scale_x)
    real_y = round(monitor_top + y * scale_y)

    real_x = min(max(real_x, 0), monitor_left + monitor_width - 1)
    real_y = min(max(real_y, 0), monitor_top + monitor_height - 1)

    return real_x, real_y
