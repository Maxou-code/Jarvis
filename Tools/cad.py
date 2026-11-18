import json
import re
from pathlib import Path

from config import MAX_PYTHON_3D_MODEL_SECONDS, WORKSPACE
from Core.paths import safe_path
from Tools.python_runner import run_python


def read_cadquery_guide():
    """Lit uniquement le guide CadQuery fourni avec l'application."""
    guide_path = Path(__file__).resolve().parent.parent / "Docs" / "cadquery.md"
    if not guide_path.is_file():
        raise FileNotFoundError(f"Guide CadQuery introuvable : {guide_path}")
    return guide_path.read_text(encoding="utf-8")


def create_3d_model(title, code, filename="modele_3d"):
    """Exécute un script CadQuery contrôlé et produit un STL dans le workspace.

    Le script fourni doit définir `model` comme cq.Workplane ou cq.Shape.
    L'exécution passe par le runner Python existant, avec ses restrictions de
    chemins, durée et accès réseau/processus.
    """
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Le titre du modèle est obligatoire.")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("Le code CadQuery est vide.")
    if len(code.encode("utf-8")) > 30_000:
        raise ValueError("Le script de modélisation est limité à 30 Ko.")

    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", str(filename)).strip("_-")[:64]
    if not slug:
        slug = "modele_3d"

    models_dir = WORKSPACE / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    relative_stl = Path("models") / f"{slug}.stl"
    stl_path = safe_path(relative_stl.as_posix())
    if stl_path.exists():
        # Ne jamais écraser silencieusement un modèle précédent.
        suffix = 2
        while True:
            candidate = models_dir / f"{slug}_{suffix}.stl"
            if not candidate.exists():
                stl_path = candidate
                relative_stl = candidate.relative_to(WORKSPACE)
                break
            suffix += 1

    script = (
        "from pathlib import Path\n"
        "import cadquery as cq\n"
        + re.sub(r"(?m)^\s*import\s+cq\s*$", "import cadquery as cq", code.rstrip())
        + "\n\n"
        + "if 'model' not in globals():\n"
        + "    raise ValueError(\"Le script doit définir une variable `model`.\")\n"
        + f"cq.exporters.export(model, {str(relative_stl.as_posix())!r})\n"
        + f"print('STL_EXPORTED:{relative_stl.as_posix()}')\n"
    )

    execution = json.loads(
        run_python(
            script,
            timeout=MAX_PYTHON_3D_MODEL_SECONDS,
            max_timeout=MAX_PYTHON_3D_MODEL_SECONDS
        )
    )
    if not execution.get("success"):
        error = execution.get("stderr") or execution.get("stdout") or "Erreur inconnue pendant la génération STL."
        raise RuntimeError(str(error)[-5000:])
    if not stl_path.is_file() or stl_path.stat().st_size < 84:
        raise RuntimeError("CadQuery n'a pas produit de fichier STL valide.")

    return {
        "model": {
            "title": title.strip()[:120],
            "path": relative_stl.as_posix(),
            "filename": stl_path.name,
            "size_bytes": stl_path.stat().st_size,
            "format": "STL"
        }
    }
