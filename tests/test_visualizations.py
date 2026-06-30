from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.visualizations import horizontal_bar_chart


class VisualizationTests(unittest.TestCase):
    def test_horizontal_bar_chart_creates_svg_file(self) -> None:
        data = pd.DataFrame({"rotulo": ["A", "B"], "valor": [10.0, 5.0]})

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "grafico.svg"
            horizontal_bar_chart(
                data,
                label_col="rotulo",
                value_col="valor",
                title="Grafico de teste",
                subtitle="Validacao de SVG",
                output_path=output_path,
                value_formatter=lambda value: str(int(value)),
            )

            content = output_path.read_text(encoding="utf-8")
            self.assertIn("<svg", content)
            self.assertIn("Grafico de teste", content)
            self.assertIn("A", content)


if __name__ == "__main__":
    unittest.main()
