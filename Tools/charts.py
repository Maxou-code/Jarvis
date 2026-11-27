import ast
import math
import operator
import re


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def parse_chart_number(value):
    """Parse a finite number or a small arithmetic expression without eval."""
    if isinstance(value, bool):
        raise ValueError("Les valeurs doivent être des nombres, pas des booléens.")
    if isinstance(value, (int, float)):
        try:
            result = float(value)
        except OverflowError as error:
            raise ValueError("Les valeurs numériques doivent être finies.") from error
        if math.isfinite(result):
            return result
        raise ValueError("Les valeurs numériques doivent être finies.")
    if not isinstance(value, str) or not value.strip() or len(value) > 80:
        raise ValueError("Expression numérique invalide (80 caractères maximum).")

    expression = re.sub(
        r"(?<![A-Za-z])(?:sqrt|√|V)\s*(\([^()]*\)|(?:\d+(?:\.\d*)?|\.\d+))",
        r"sqrt(\1)",
        value.strip(),
    )
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as error:
        raise ValueError("Expression numérique invalide.") from error

    nodes = list(ast.walk(tree))
    if len(nodes) > 32:
        raise ValueError("Expression numérique trop complexe.")

    def evaluate(node):
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            return _BINARY_OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _UNARY_OPERATORS[type(node.op)](evaluate(node.operand))
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sqrt"
            and len(node.args) == 1
            and not node.keywords
        ):
            return math.sqrt(evaluate(node.args[0]))
        raise ValueError("Seuls les nombres, +, -, *, / et √ (ou sqrt) sont acceptés.")

    try:
        result = float(evaluate(tree))
    except (ArithmeticError, OverflowError) as error:
        raise ValueError("Expression numérique invalide ou non finie.") from error
    if not math.isfinite(result):
        raise ValueError("Expression numérique invalide ou non finie.")
    return result


def plot_chart(
    title, x_values, y_values=None, chart_type="line", x_label="", y_label="",
    series=None,
):
    if series is None:
        if y_values is None:
            raise ValueError("Fournis y_values ou une liste de séries.")
        series = [{"name": "Série 1", "y_values": y_values}]
    elif y_values is not None:
        raise ValueError("Utilise y_values ou series, pas les deux.")
    if not isinstance(series, list) or not 1 <= len(series) <= 8:
        raise ValueError("Fournis de 1 à 8 séries.")
    if (
        not isinstance(x_values, list)
        or not x_values
        or len(x_values) > 100
    ):
        raise ValueError("Fournis de 1 à 100 valeurs X.")
    if chart_type not in {"line", "bar"}:
        raise ValueError("chart_type doit être line ou bar.")

    if any(isinstance(value, bool) or not isinstance(value, (str, int, float)) for value in x_values):
        raise ValueError("Les valeurs X doivent être numériques, des expressions mathématiques ou des libellés texte.")

    parsed_x = []
    for value in x_values:
        try:
            parsed_x.append(parse_chart_number(value))
        except ValueError:
            parsed_x.append(None)

    if all(value is not None for value in parsed_x):
        x_is_numeric = True
        validated_x = parsed_x
    elif all(isinstance(value, str) for value in x_values):
        x_is_numeric = False
        validated_x = [value[:40] for value in x_values]
    else:
        raise ValueError("Les valeurs X doivent être soit toutes numériques, soit toutes des libellés texte.")
    x_display_labels = [
        value[:40] if isinstance(value, str) else f"{parsed:g}"
        for value, parsed in zip(x_values, parsed_x)
    ]

    parsed_series = []
    for index, item in enumerate(series):
        if not isinstance(item, dict):
            raise ValueError("Chaque série doit contenir un nom et une liste y_values.")
        name = item.get("name", f"Série {index + 1}")
        values = item.get("y_values")
        if (
            not isinstance(name, str)
            or not isinstance(values, list)
            or len(values) != len(x_values)
        ):
            raise ValueError("Chaque série doit avoir un nom et autant de valeurs Y que de valeurs X.")
        vals = [parse_chart_number(value) for value in values]
        display_labels = [
            value[:40] if isinstance(value, str) else f"{numeric:g}"
            for value, numeric in zip(values, vals)
        ]
        parsed_series.append({
            "name": name.strip()[:40] or f"Série {index + 1}",
            "y_values": vals,
            "y_display_labels": display_labels,
        })

    first_series = parsed_series[0]

    return {
        "chart": {
            "title": str(title)[:120],
            "x_values": validated_x,
            "x_display_labels": x_display_labels,
            "x_axis_type": "numeric" if x_is_numeric else "category",
            "y_values": first_series["y_values"],
            "y_display_labels": first_series["y_display_labels"],
            "series": parsed_series,
            "chart_type": chart_type,
            "x_label": str(x_label)[:80],
            "y_label": str(y_label)[:80],
        }
    }
