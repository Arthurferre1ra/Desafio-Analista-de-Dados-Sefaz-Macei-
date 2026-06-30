from __future__ import annotations

import argparse
from pathlib import Path

from .config import ProjectPaths
from .indicators import build_analysis_tables
from .reporting import save_output_tables, save_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera indicadores e relatorio analitico FINBRA/Siconfi.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Raiz do projeto. Por padrao, usa a pasta acima de src/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = ProjectPaths.from_root(args.root)

    if not paths.sqlite_path.exists():
        raise FileNotFoundError("Base SQLite nao encontrada. Execute primeiro: python -m src.pipeline")

    tables = build_analysis_tables(paths.sqlite_path)
    saved_tables = save_output_tables(tables, paths.reports_dir)
    report_path = save_report(tables, paths.reports_dir)

    print(f"Tabelas geradas: {len(saved_tables)}")
    print(f"Relatorio gerado: {report_path}")


if __name__ == "__main__":
    main()
