from __future__ import annotations

import unittest

from src.finbra_etl import classify_account, parse_account_code, parse_account_name, parse_capital


class FinbraEtlParsingTests(unittest.TestCase):
    def test_classifies_account_levels(self) -> None:
        self.assertEqual(classify_account("10 - Saude"), "funcao")
        self.assertEqual(classify_account("10.301 - Atencao Basica"), "subfuncao")
        self.assertEqual(classify_account("FU10 - Demais Subfuncoes"), "demais_subfuncoes")
        self.assertEqual(classify_account("Despesas Exceto Intraorcamentarias"), "total")

    def test_parses_account_code_and_name(self) -> None:
        account = "12.365 - Educacao Infantil"
        self.assertEqual(parse_account_code(account, "subfuncao"), "12.365")
        self.assertEqual(parse_account_name(account), "Educacao Infantil")

    def test_parses_capital_with_different_prepositions(self) -> None:
        self.assertEqual(parse_capital("Prefeitura Municipal de Maceio - AL", "AL"), "Maceio")
        self.assertEqual(parse_capital("Prefeitura Municipal do Rio de Janeiro - RJ", "RJ"), "Rio de Janeiro")


if __name__ == "__main__":
    unittest.main()
