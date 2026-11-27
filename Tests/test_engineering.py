import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from Tools.engineering import (
    create_technical_report,
    simulate_ode,
    solve_linear_system,
)


class LinearSystemTests(unittest.TestCase):
    def test_solution_is_verified(self):
        result = solve_linear_system([[3, 2], [1, 2]], [5, 5])
        self.assertAlmostEqual(result["solution"][0], 0)
        self.assertAlmostEqual(result["solution"][1], 2.5)
        self.assertTrue(result["verification"]["passed"])
        self.assertLessEqual(
            result["verification"]["residual_infinity_norm"],
            result["verification"]["tolerance"],
        )

    def test_rejects_singular_matrix(self):
        with self.assertRaisesRegex(ValueError, "singulière"):
            solve_linear_system([[1, 2], [2, 4]], [3, 6])


class OdeSimulationTests(unittest.TestCase):
    def test_exponential_solution_and_step_doubling(self):
        result = simulate_ode(["y0"], [1], 0, 1, steps=40)
        self.assertAlmostEqual(result["final_values"][0], math.e, places=7)
        self.assertTrue(result["verification"]["passed"])
        self.assertGreaterEqual(len(result["samples"]), 2)
        self.assertAlmostEqual(result["samples"][-1]["t"], 1)

    def test_coupled_system_uses_all_state_variables(self):
        result = simulate_ode(
            ["y1", "-y0"],
            [1, 0],
            0,
            1,
            steps=100,
        )
        self.assertAlmostEqual(result["final_values"][0], math.cos(1), places=7)
        self.assertAlmostEqual(result["final_values"][1], -math.sin(1), places=7)

    def test_rejects_unsafe_equation(self):
        with self.assertRaises(ValueError):
            simulate_ode(["__import__('os')"], [1], 0, 1)

    def test_marks_under_resolved_simulation(self):
        result = simulate_ode(["100*y0"], [1], 0, 1, steps=2)
        self.assertFalse(result["verification"]["passed"])


class TechnicalReportTests(unittest.TestCase):
    def test_creates_non_overwriting_markdown_report(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            with patch("Tools.engineering.safe_path", lambda name: root / name):
                arguments = {
                    "title": "Étude de test",
                    "objective": "Tester le rapport.",
                    "assumptions": "Unités SI.",
                    "method": "Calcul numérique.",
                    "results": "Résultat vérifié.",
                    "verification": "Résidu contrôlé.",
                    "limitations": "Essai logiciel uniquement.",
                }
                first = create_technical_report(**arguments)["report"]["path"]
                second = create_technical_report(**arguments)["report"]["path"]
            self.assertNotEqual(first, second)
            self.assertIn("## Vérification", (root / first).read_text(encoding="utf-8"))
            self.assertIn("validation indépendante", (root / second).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
