import json
import os
import re
from pathlib import Path

from config import BACKUP_DIR, MAX_FILE_SIZE, WORKSPACE
from Core.paths import _directory_roots, safe_managed_path, safe_path

def create_file(filename, content=""):
    path = safe_path(filename)
    if path.exists():
        raise FileExistsError("Le fichier existe déjà.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Fichier créé : {path.relative_to(WORKSPACE)}"
def create_folder(foldername):
    path = safe_path(foldername)
    path.mkdir(parents=True, exist_ok=True)
    return f"Dossier créé : {path.relative_to(WORKSPACE)}"
def write_file(filename, content):
    path = safe_path(filename)
    if not path.is_file():
        raise FileNotFoundError("Fichier introuvable.")
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        raise ValueError("Contenu trop volumineux pour cet outil.")
    path.write_text(content, encoding="utf-8")
    return f"Fichier modifié : {path.relative_to(WORKSPACE)}"
def read_file(filename):
    path = safe_path(filename)
    if not path.is_file():
        raise FileNotFoundError("Fichier introuvable.")
    if path.stat().st_size > MAX_FILE_SIZE:
        raise ValueError("Fichier trop volumineux pour être lu en une fois.")
    return path.read_text(encoding="utf-8")
def open_file(filename):
    path = safe_path(filename)
    if not path.is_file():
        raise FileNotFoundError("Fichier introuvable.")
    os.startfile(str(path))
    return f"Ouverture demandée : {path.name}"
def open_workspace():
    os.startfile(str(WORKSPACE))
    return "Workspace ouvert dans l'explorateur."
def list_managed_files(location="workspace/"):
    roots = _directory_roots()
    key = location.rstrip("/")
    root = roots[key] if key in roots else safe_managed_path(location)
    if not root.exists() or not root.is_dir():
        raise NotADirectoryError(f"Dossier introuvable : {root}")
    items = []
    for item in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.casefold()))[:200]:
        items.append({"name": item.name, "type": "directory" if item.is_dir() else "file", "size": item.stat().st_size if item.is_file() else None})
    return json.dumps({"path": str(root), "items": items}, ensure_ascii=False, indent=2)
def read_managed_file(location):
    path = safe_managed_path(location)
    if not path.is_file(): raise FileNotFoundError(f"Fichier introuvable : {location}")
    if path.stat().st_size > MAX_FILE_SIZE: raise ValueError("Fichier trop volumineux.")
    return path.read_text(encoding="utf-8")
def write_managed_file(location, content):
    path = safe_managed_path(location)
    if len(content.encode("utf-8")) > MAX_FILE_SIZE: raise ValueError("Contenu trop volumineux.")
    if path.exists(): raise FileExistsError("Le fichier existe déjà ; refus de l'écraser.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"Fichier créé : {location}"
def backup_config(location, backup_name=None):
    source = safe_managed_path(location)
    if not source.exists(): raise FileNotFoundError(f"Source introuvable : {location}")
    name = backup_name or (source.name + (".zip" if source.is_dir() else ""))
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", name): raise ValueError("Nom de sauvegarde invalide.")
    destination = (BACKUP_DIR / name).resolve()
    destination.relative_to(BACKUP_DIR.resolve())
    if destination.exists(): raise FileExistsError("Cette sauvegarde existe déjà.")
    import shutil, zipfile
    if source.is_file():
        if source.stat().st_size > 20_000_000: raise ValueError("Sauvegarde limitée à 20 Mo.")
        shutil.copy2(source, destination)
    else:
        files = [item for item in source.rglob("*") if item.is_file()]
        if len(files) > 1000 or sum(item.stat().st_size for item in files) > 20_000_000:
            raise ValueError("Dossier trop volumineux : maximum 1000 fichiers et 20 Mo.")
        if not name.lower().endswith(".zip"): raise ValueError("Une sauvegarde de dossier doit utiliser l'extension .zip.")
        with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in files: archive.write(item, item.relative_to(source))
    return f"Sauvegarde créée : backups/{name}"
def restore_config(backup_name, destination):
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", backup_name or ""): raise ValueError("Nom de sauvegarde invalide.")
    source = (BACKUP_DIR / backup_name).resolve()
    source.relative_to(BACKUP_DIR.resolve())
    if not source.is_file(): raise FileNotFoundError(f"Sauvegarde introuvable : {backup_name}")
    target = safe_managed_path(destination)
    if target.exists(): raise FileExistsError("La destination existe déjà ; refus de l'écraser.")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".zip":
        import zipfile
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                member_path = Path(member.filename)
                if member_path.is_absolute() or ".." in member_path.parts:
                    raise ValueError("Archive refusée : chemin interne non sûr.")
            target.mkdir(parents=True, exist_ok=False)
            archive.extractall(target)
    else:
        import shutil
        shutil.copy2(source, target)
    return f"Configuration restaurée vers {destination}"
