from __future__ import annotations

import unittest

import pandas as pd

from src.config import EXPENSE_STAGE_COMMITTED, EXPENSE_STAGE_PAID
from src.indicators import calculate_execution_indicators, infer_complete_years


class IndicatorTests(unittest.TestCase):
    def test_infers_complete_years_from_maximum_capital_count(self) -> None:
        completeness = pd.DataFrame({"ano": [2023, 2024, 2025], "qtd_capitais": [26, 26, 11]})
        self.assertEqual(infer_complete_years(completeness), (2023, 2024))

    def test_calculates_execution_rate_safely(self) -> None:
        expenses = pd.DataFrame(
            [
                {
                    "ano": 2024,
                    "capital": "Maceio",
                    "uf": "AL",
                    "populacao": 100,
                    "codigo_funcao": "10",
                    "funcao": "10 - Saude",
                    "estagio": EXPENSE_STAGE_COMMITTED,
                    "valor": 200.0,
                },
                {
                    "ano": 2024,
                    "capital": "Maceio",
                    "uf": "AL",
                    "populacao": 100,
                    "codigo_funcao": "10",
                    "funcao": "10 - Saude",
                    "estagio": EXPENSE_STAGE_PAID,
                    "valor": 150.0,
                },
            ]
        )

        indicators = calculate_execution_indicators(expenses)
        self.assertAlmostEqual(float(indicators.loc[0, "taxa_execucao"]), 0.75)
        self.assertAlmostEqual(float(indicators.loc[0, "pago_per_capita"]), 1.5)


if __name__ == "__main__":
    unittest.main()
