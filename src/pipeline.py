from __future__ import annotations

import argparse
from pathlib import Path

from .config import ProjectPaths
from .finbra_etl import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extrai, consolida e persiste os dados FINBRA/Siconfi.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Raiz do projeto. Por padrao, usa a pasta acima de src/.",
    )
    parser.add_argument(
        "--skip-extract",
        action="store_true",
        help="Reutiliza arquivos ja extraidos em dados_extraidos/.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    paths = ProjectPaths.from_root(args.root)
    result = run_pipeline(paths, extract=not args.skip_extract)

    print(f"Arquivos extraidos: {len(result.extracted_files)}")
    print(f"Linhas consolidadas: {result.rows:,}".replace(",", "."))
    print(f"CSV consolidado: {result.consolidated_csv_path}")
    print(f"SQLite: {result.sqlite_path}")


if __name__ == "__main__":
    main()
