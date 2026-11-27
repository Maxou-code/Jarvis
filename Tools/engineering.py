import ast
import math
import re
from datetime import datetime

from Core.paths import safe_path


_FUNCTIONS = {
    "abs": abs,
    "cos": math.cos,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
    "max": max,
    "min": min,
    "sin": math.sin,
    "sqrt": math.sqrt,
    "tan": math.tan,
}
_BINARY_OPERATORS = {
    ast.Add: lambda left, right: left + right,
    ast.Sub: lambda left, right: left - right,
    ast.Mult: lambda left, right: left * right,
    ast.Div: lambda left, right: left / right,
    ast.Pow: lambda left, right: left ** right,
    ast.Mod: lambda left, right: left % right,
}


def _finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} doit être un nombre fini.")
    try:
        result = float(value)
    except OverflowError as error:
        raise ValueError(f"{name} doit être un nombre fini.") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} doit être un nombre fini.")
    return result


def _evaluate_expression(expression, values):
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 500:
        raise ValueError("Chaque équation doit être une expression de 1 à 500 caractères.")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as error:
        raise ValueError(f"Expression invalide : {expression[:80]}") from error
    if sum(1 for _ in ast.walk(tree)) > 100:
        raise ValueError("Expression trop complexe.")

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.Name):
            if node.id == "pi":
                return math.pi
            if node.id == "e":
                return math.e
            if node.id not in values:
                raise ValueError(f"Variable inconnue dans l'équation : {node.id}")
            return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = evaluate(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 12:
                raise ValueError("Les exposants des équations sont limités à 12.")
            return _BINARY_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function = _FUNCTIONS.get(node.func.id)
            if function is None or node.keywords or not 1 <= len(node.args) <= 2:
                raise ValueError("Fonction ou arguments non autorisés dans l'équation.")
            return function(*(evaluate(argument) for argument in node.args))
        raise ValueError("Syntaxe non autorisée dans l'équation.")

    try:
        result = float(evaluate(tree))
    except (ArithmeticError, OverflowError) as error:
        raise ValueError("L'équation produit une valeur non définie.") from error
    if not math.isfinite(result):
        raise ValueError("L'équation produit une valeur non finie.")
    return result


def solve_linear_system(matrix, vector):
    """Solve Ax=b with scaled pivoting and verify the residual."""
    if not isinstance(matrix, list) or not 1 <= len(matrix) <= 20:
        raise ValueError("La matrice doit contenir de 1 à 20 lignes.")
    size = len(matrix)
    if any(not isinstance(row, list) or len(row) != size for row in matrix):
        raise ValueError("La matrice doit être carrée.")
    if not isinstance(vector, list) or len(vector) != size:
        raise ValueError("Le vecteur second membre doit avoir la même taille que la matrice.")

    coefficients = [
        [_finite_number(value, "Coefficient") for value in row]
        for row in matrix
    ]
    right_hand_side = [_finite_number(value, "Second membre") for value in vector]
    original = [row[:] for row in coefficients]
    original_rhs = right_hand_side[:]
    scale = max((abs(value) for row in coefficients for value in row), default=0.0)
    if scale == 0:
        raise ValueError("La matrice est singulière.")

    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(coefficients[row][column]))
        if abs(coefficients[pivot][column]) <= scale * 1e-14:
            raise ValueError("La matrice est singulière ou mal conditionnée.")
        coefficients[column], coefficients[pivot] = coefficients[pivot], coefficients[column]
        right_hand_side[column], right_hand_side[pivot] = right_hand_side[pivot], right_hand_side[column]

        pivot_value = coefficients[column][column]
        for row in range(column + 1, size):
            factor = coefficients[row][column] / pivot_value
            coefficients[row][column] = 0.0
            for entry in range(column + 1, size):
                coefficients[row][entry] -= factor * coefficients[column][entry]
            right_hand_side[row] -= factor * right_hand_side[column]

    solution = [0.0] * size
    for row in range(size - 1, -1, -1):
        solution[row] = (
            right_hand_side[row]
            - sum(coefficients[row][column] * solution[column] for column in range(row + 1, size))
        ) / coefficients[row][row]
    if any(not math.isfinite(value) for value in solution):
        raise ArithmeticError("La solution du système contient une valeur non finie.")

    residual = max(
        abs(sum(original[row][column] * solution[column] for column in range(size)) - original_rhs[row])
        for row in range(size)
    )
    tolerance = 1e-10 * max(
        1.0,
        max(sum(abs(value) for value in row) for row in original)
        * max(abs(value) for value in solution),
        max(abs(value) for value in original_rhs),
    )
    if not math.isfinite(residual) or not math.isfinite(tolerance) or residual > tolerance:
        raise ArithmeticError("La vérification du résidu du système a échoué.")

    return {
        "solution": solution,
        "verification": {
            "method": "pivot partiel, substitution arrière et contrôle du résidu",
            "residual_infinity_norm": residual,
            "tolerance": tolerance,
            "passed": True,
        },
    }


def _rk4_step(equations, time, state, step, parameters):
    def derivatives(at_time, at_state):
        values = {"t": at_time, **parameters}
        values.update({f"y{index}": value for index, value in enumerate(at_state)})
        return [_evaluate_expression(equation, values) for equation in equations]

    first = derivatives(time, state)
    second = derivatives(
        time + step / 2,
        [value + step * slope / 2 for value, slope in zip(state, first)],
    )
    third = derivatives(
        time + step / 2,
        [value + step * slope / 2 for value, slope in zip(state, second)],
    )
    fourth = derivatives(
        time + step,
        [value + step * slope for value, slope in zip(state, third)],
    )
    return [
        value + step * (a + 2 * b + 2 * c + d) / 6
        for value, a, b, c, d in zip(state, first, second, third, fourth)
    ]


def simulate_ode(equations, initial_values, t_start, t_end, steps=100, parameters=None):
    """Integrate a first-order ODE system with RK4 and a doubled-step cross-check."""
    if not isinstance(equations, list) or not 1 <= len(equations) <= 8:
        raise ValueError("Fournis de 1 à 8 équations, une par état y0, y1, etc.")
    if not isinstance(initial_values, list) or len(initial_values) != len(equations):
        raise ValueError("Chaque équation doit avoir une valeur initiale correspondante.")
    if isinstance(steps, bool) or not isinstance(steps, int) or not 2 <= steps <= 5000:
        raise ValueError("steps doit être un entier compris entre 2 et 5000.")
    start = _finite_number(t_start, "t_start")
    end = _finite_number(t_end, "t_end")
    if end <= start:
        raise ValueError("t_end doit être supérieur à t_start.")
    initial = [_finite_number(value, "Valeur initiale") for value in initial_values]

    if parameters is None:
        parameters = {}
    if not isinstance(parameters, dict) or len(parameters) > 20:
        raise ValueError("parameters doit contenir au maximum 20 paramètres numériques.")
    reserved = {"t", "pi", "e"} | {f"y{index}" for index in range(len(equations))} | set(_FUNCTIONS)
    validated_parameters = {}
    for name, value in parameters.items():
        if (
            not isinstance(name, str)
            or len(name) > 64
            or not name.isidentifier()
            or name in reserved
        ):
            raise ValueError(f"Nom de paramètre invalide : {name!r}.")
        validated_parameters[name] = _finite_number(value, f"Paramètre {name}")

    for equation in equations:
        _evaluate_expression(equation, {"t": start, **validated_parameters, **{
            f"y{index}": value for index, value in enumerate(initial)
        }})

    step_size = (end - start) / steps
    state = initial[:]
    sample_stride = max(1, math.ceil(steps / 99))
    samples = [{"t": start, **{f"y{index}": value for index, value in enumerate(state)}}]
    for index in range(steps):
        state = _rk4_step(equations, start + index * step_size, state, step_size, validated_parameters)
        if any(not math.isfinite(value) for value in state):
            raise ArithmeticError("La simulation a divergé vers une valeur non finie.")
        if (index + 1) % sample_stride == 0 or index + 1 == steps:
            samples.append({
                "t": start + (index + 1) * step_size,
                **{f"y{state_index}": value for state_index, value in enumerate(state)},
            })

    reference = initial[:]
    reference_step = step_size / 2
    for index in range(steps * 2):
        reference = _rk4_step(
            equations, start + index * reference_step, reference,
            reference_step, validated_parameters,
        )
        if any(not math.isfinite(value) for value in reference):
            raise ArithmeticError("La simulation de vérification a divergé.")
    relative_error = max(
        abs(value - reference_value) / max(1.0, abs(reference_value))
        for value, reference_value in zip(state, reference)
    )
    if not math.isfinite(relative_error):
        raise ArithmeticError("La comparaison de convergence a produit une valeur non finie.")
    passed = relative_error <= 0.01
    return {
        "method": "Runge-Kutta d'ordre 4 (RK4)",
        "interval": [start, end],
        "steps": steps,
        "initial_values": initial,
        "final_values": state,
        "samples": samples,
        "verification": {
            "method": "comparaison de la solution finale avec un pas deux fois plus fin",
            "max_relative_difference": relative_error,
            "tolerance": 0.01,
            "passed": passed,
            "note": "Ce contrôle de convergence ne remplace pas une validation physique du modèle.",
        },
    }


def create_technical_report(title, objective, assumptions, method, results, verification, limitations):
    fields = {
        "Objectif": objective,
        "Hypothèses": assumptions,
        "Méthode": method,
        "Résultats": results,
        "Vérification": verification,
        "Limites": limitations,
    }
    if not isinstance(title, str) or not title.strip() or len(title) > 160:
        raise ValueError("Le titre est obligatoire et limité à 160 caractères.")
    for name, value in fields.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 12_000:
            raise ValueError(f"{name} doit contenir de 1 à 12000 caractères.")

    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", title.strip()).strip("_-")[:64] or "rapport"
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    relative_path = f"reports/{slug}_{stamp}.md"
    destination = safe_path(relative_path)
    suffix = 2
    while destination.exists():
        relative_path = f"reports/{slug}_{stamp}_{suffix}.md"
        destination = safe_path(relative_path)
        suffix += 1
    destination.parent.mkdir(parents=True, exist_ok=True)
    content = [
        f"# {title.strip()}",
        "",
        f"- **Généré le :** {datetime.now().astimezone().isoformat(timespec='seconds')}",
        "- **Statut :** rapport généré par JARVIS ; validation indépendante recommandée avant usage critique.",
    ]
    content.extend(f"\n## {heading}\n\n{text.strip()}" for heading, text in fields.items())
    destination.write_text("\n".join(content) + "\n", encoding="utf-8")
    return {"report": {"path": relative_path, "format": "Markdown"}}
