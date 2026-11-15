import ast
import json
import math
from datetime import datetime

def get_current_datetime():
    """Retourne la date et l'heure locales du PC, avec le fuseau horaire."""
    now = datetime.now().astimezone()
    result = {
        "date": now.strftime("%Y-%m-%d"),
        "heure": now.strftime("%H:%M:%S"),
        "jour": ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"][now.weekday()],
        "date_formatee": now.strftime("%d/%m/%Y"),
        "fuseau_horaire": now.tzname(),
        "decalage_utc": now.strftime("%z"),
        "iso": now.isoformat()
    }
    return json.dumps(result, ensure_ascii=False)
def calculate(expression):
    """
    Calcule une expression mathématique sans eval().
    Opérateurs : + - * / // % ** (ou ^ pour la puissance).
    Fonctions : sqrt, sin, cos, tan, log, log10, exp, abs, round, etc.
    Constantes : pi, e, tau.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("Fournis une expression mathématique.")
    if len(expression) > 300:
        raise ValueError("Expression trop longue (maximum 300 caractères).")

    normalized = expression.replace("^", "**")
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise ValueError("Syntaxe mathématique invalide.") from exc

    if sum(1 for _ in ast.walk(tree)) > 80:
        raise ValueError("Expression trop complexe.")

    result = _evaluate_math_node(tree)
    if isinstance(result, complex):
        raise ValueError("Le résultat complexe n'est pas pris en charge.")
    if isinstance(result, float) and not math.isfinite(result):
        raise ValueError("Le résultat n'est pas un nombre fini.")
    if isinstance(result, (int, float)) and abs(result) > 1e100:
        raise ValueError("Résultat trop grand.")
    return json.dumps({
        "expression": expression,
        "resultat": result
    }, ensure_ascii=False)
_CALCULATOR_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "log": math.log,
    "log10": math.log10,
    "ln": math.log,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "ceil": math.ceil,
    "floor": math.floor,
    "degrees": math.degrees,
    "radians": math.radians
}
_CALCULATOR_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau
}
def _evaluate_math_node(node):
    """Évalue récursivement une expression AST avec une liste blanche stricte."""
    if isinstance(node, ast.Expression):
        return _evaluate_math_node(node.body)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("Seuls les nombres sont autorisés.")
        return node.value

    if isinstance(node, ast.Name):
        if node.id in _CALCULATOR_CONSTANTS:
            return _CALCULATOR_CONSTANTS[node.id]
        raise ValueError(f"Constante inconnue : {node.id}")

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = _evaluate_math_node(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value

    if isinstance(node, ast.BinOp):
        left = _evaluate_math_node(node.left)
        right = _evaluate_math_node(node.right)

        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            result = left / right
        elif isinstance(node.op, ast.FloorDiv):
            result = left // right
        elif isinstance(node.op, ast.Mod):
            result = left % right
        elif isinstance(node.op, ast.Pow):
            if abs(right) > 100:
                raise ValueError("Exposant trop élevé (maximum : 100 en valeur absolue).")
            if abs(left) > 1e100:
                raise ValueError("Base trop élevée.")
            result = left ** right
        else:
            raise ValueError("Opérateur mathématique non autorisé.")

        return result

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Appel de fonction non autorisé.")
        function = _CALCULATOR_FUNCTIONS.get(node.func.id)
        if function is None:
            raise ValueError(f"Fonction inconnue ou non autorisée : {node.func.id}")
        if node.keywords:
            raise ValueError("Les arguments nommés ne sont pas autorisés.")
        args = [_evaluate_math_node(arg) for arg in node.args]
        return function(*args)

    raise ValueError("Expression invalide ou syntaxe non autorisée.")
