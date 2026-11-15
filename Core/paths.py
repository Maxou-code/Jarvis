from pathlib import Path

from config import AUTHORIZED_DIRS, WORKSPACE, _save_app_config

def register_authorized_directory(folder):
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        raise NotADirectoryError(f"Dossier introuvable : {path}")
    if path == Path(path.anchor) or path.name.lower() in {"windows", "system32"}:
        raise ValueError("Ce dossier système est trop sensible pour être autorisé.")
    index = 1
    while f"shared_{index}" in AUTHORIZED_DIRS:
        index += 1
    alias = f"shared_{index}"
    AUTHORIZED_DIRS[alias] = str(path)
    _save_app_config()
    return {"alias": alias, "path": str(path)}
def _directory_roots():
    home = Path.home()
    roots = {"workspace": WORKSPACE.resolve(), "documents": (home / "Documents").resolve(), "downloads": (home / "Downloads").resolve(), "desktop": (home / "Desktop").resolve()}
    roots.update({k: Path(v).resolve() for k, v in AUTHORIZED_DIRS.items()})
    return roots
def safe_managed_path(location):
    if not isinstance(location, str) or not location.strip():
        raise ValueError("Indique un chemin au format alias/chemin.")
    alias, sep, relative = location.strip().replace("\\", "/").partition("/")
    roots = _directory_roots()
    if alias not in roots:
        raise ValueError(f"Alias inconnu : {alias}. Disponibles : {', '.join(sorted(roots))}")
    if not sep or not relative:
        raise ValueError("Précise un chemin après l'alias, par exemple documents/rapport.txt.")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("Les chemins absolus et la remontée '..' sont interdits.")
    root = roots[alias]
    resolved = (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError("Accès en dehors du dossier autorisé interdit.")
    return resolved
def safe_path(filename):
    """Résout un chemin relatif et interdit toute sortie du workspace."""
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("Le nom du fichier est vide ou invalide.")

    candidate = Path(filename)
    if candidate.is_absolute():
        raise ValueError("Seuls les chemins relatifs au workspace sont autorisés.")

    root = WORKSPACE.resolve()
    path = (root / candidate).resolve()

    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("Accès en dehors de Jarvis_Workspace interdit.")

    return path
