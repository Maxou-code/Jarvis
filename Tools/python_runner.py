import ast
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from config import MAX_PYTHON_3D_MODEL_SECONDS, MAX_PYTHON_OUTPUT, MAX_PYTHON_SECONDS, MAX_SCRIPT_SIZE, WORKSPACE

def _validate_python_script(code):
    """Vérifie la syntaxe et bloque quelques primitives d'exécution indirecte.

    Les imports ne sont plus limités à une liste fixe : Python pourra charger
    tout module réellement disponible dans l'environnement de JARVIS.
    """
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Le script Python est vide.")
    if len(code.encode("utf-8")) > MAX_SCRIPT_SIZE:
        raise ValueError(f"Script limité à {MAX_SCRIPT_SIZE} octets.")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise ValueError(f"Syntaxe Python invalide : {exc}") from exc

    forbidden_calls = {"eval", "exec", "compile", "__import__", "breakpoint"}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in forbidden_calls):
            raise ValueError(f"Fonction non autorisée : {node.func.id}")
def list_python_packages():
    """Liste les modules standard et packages installés visibles par JARVIS."""
    import importlib.metadata
    import pkgutil
    import site
    import sys

    module_names = set(getattr(sys, "stdlib_module_names", set()))
    for module in pkgutil.iter_modules():
        module_names.add(module.name)

    user_site = site.getusersitepackages()
    if isinstance(user_site, str):
        user_site = [user_site]
    for directory in user_site:
        if directory and Path(directory).is_dir():
            for module in pkgutil.iter_modules([directory]):
                module_names.add(module.name)

    packages = []
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name") or "package-inconnu"
        packages.append({"name": name, "version": dist.version})
    packages.sort(key=lambda item: item["name"].casefold())

    return json.dumps({
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "package_count": len(packages),
        "module_count": len(module_names),
        "packages": packages,
        "importable_modules": sorted(module_names, key=str.casefold),
        "note": "La disponibilité dépend de l'environnement Python utilisé pour lancer JARVIS."
    }, ensure_ascii=False, indent=2)
def run_python(code, timeout=MAX_PYTHON_SECONDS, *, max_timeout=MAX_PYTHON_SECONDS):
    """Exécute un script isolé, avec imports de l'environnement Python de JARVIS."""
    _validate_python_script(code)

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, int)
        or isinstance(max_timeout, bool)
        or not isinstance(max_timeout, int)
        or not 1 <= max_timeout <= MAX_PYTHON_3D_MODEL_SECONDS
        or not 1 <= timeout <= max_timeout
    ):
        raise ValueError(
            f"timeout doit être compris entre 1 et {max_timeout} secondes."
        )

    stamp = str(int(time.time() * 1000))
    script = WORKSPACE / f".jarvis_script_{stamp}.py"
    runner_path = WORKSPACE / f".jarvis_runner_{stamp}.py"
    runner = r'''import os, sys, runpy, sysconfig, site
from pathlib import Path
ROOT = Path(sys.argv[1]).resolve()
SCRIPT = Path(sys.argv[2]).resolve()

# Le mode -I ignore le site utilisateur : on l'ajoute explicitement.
user_sites = site.getusersitepackages()
if isinstance(user_sites, str):
    user_sites = [user_sites]
for directory in user_sites:
    if directory and Path(directory).is_dir() and directory not in sys.path:
        sys.path.append(directory)

PYROOTS = [Path(sys.prefix).resolve(), Path(sys.base_prefix).resolve()]
for key in ("stdlib", "platstdlib", "purelib", "platlib"):
    value = sysconfig.get_paths().get(key)
    if value:
        PYROOTS.append(Path(value).resolve())
for directory in user_sites:
    if directory:
        PYROOTS.append(Path(directory).resolve())

def inside(path, root):
    try:
        Path(path).resolve().relative_to(root)
        return True
    except Exception:
        return False

def audit(event, args):
    # Garde-fous pratiques, pas une sandbox inviolable.
    blocked = {
        "os.remove", "os.unlink",
        "os.rmdir", "os.chmod", "os.chown"
    }
    if event in blocked:
        raise PermissionError("Action interdite dans run_python : " + event)

    if event == "os.mkdir" and args:
        if not inside(args[0], ROOT):
            raise PermissionError("Création de dossier hors Jarvis_Workspace interdite.")

    if event == "open" and args:
        raw = args[0]
        mode = args[1] if len(args) > 1 else "r"
        flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
        try:
            target = Path(raw).resolve()
        except Exception:
            raise PermissionError("Chemin non autorisé.")
        writing = any(c in str(mode) for c in ("w", "a", "x", "+")) or bool(
            flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
        )
        if inside(target, ROOT):
            return
        if not writing and any(inside(target, root) for root in PYROOTS):
            return
        raise PermissionError("Accès fichier hors Jarvis_Workspace interdit : " + str(target))

sys.addaudithook(audit)
sys.argv = [str(SCRIPT)]
runpy.run_path(str(SCRIPT), run_name="__main__")
'''
    try:
        script.write_text(code, encoding="utf-8")
        runner_path.write_text(runner, encoding="utf-8")
        mpl_config = WORKSPACE / ".mplconfig"
        mpl_config.mkdir(exist_ok=True)
        # Conserver les variables Windows indispensables. Plusieurs bibliothèques
        # (ezdxf/CadQuery notamment) utilisent Path.home() pendant leur import.
        # Le runner -I reçoit un environnement contrôlé : USERPROFILE/HOME doivent
        # donc être transmis explicitement.
        user_home = (
            os.environ.get("USERPROFILE")
            or os.environ.get("HOME")
            or os.path.expanduser("~")
        )
        env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            "WINDIR": os.environ.get("WINDIR", ""),
            "USERPROFILE": user_home,
            "HOME": user_home,
            "HOMEDRIVE": os.environ.get("HOMEDRIVE", ""),
            "HOMEPATH": os.environ.get("HOMEPATH", ""),
            "APPDATA": os.environ.get("APPDATA", str(Path(user_home) / "AppData" / "Roaming")),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", str(Path(user_home) / "AppData" / "Local")),
            "TEMP": os.environ.get("TEMP", str(WORKSPACE)),
            "TMP": os.environ.get("TMP", str(WORKSPACE)),
            "MPLCONFIGDIR": str(mpl_config),
            "XDG_CONFIG_HOME": str(WORKSPACE / ".config"),
            "XDG_CACHE_HOME": str(WORKSPACE / ".cache"),
            "HF_HOME": str(WORKSPACE / ".cache" / "huggingface"),
            "TORCH_HOME": str(WORKSPACE / ".cache" / "torch"),
            "NUMBA_CACHE_DIR": str(WORKSPACE / ".cache" / "numba"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        result = subprocess.run(
            [sys.executable, "-I", str(runner_path), str(WORKSPACE.resolve()), str(script.resolve())],
            cwd=str(WORKSPACE), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout, env=env
        )
        return json.dumps({
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": (result.stdout or "")[-MAX_PYTHON_OUTPUT:],
            "stderr": (result.stderr or "")[-MAX_PYTHON_OUTPUT:],
            "workspace": str(WORKSPACE),
            "python_executable": sys.executable,
            "imports": "stdlib + packages installés dans l'environnement de JARVIS"
        }, ensure_ascii=False, indent=2)
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Script interrompu après {timeout} secondes.")
    finally:
        for file_path in (script, runner_path):
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass
