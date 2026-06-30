from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import ProjectPaths
from .finbra_etl import run_pipeline
from .logging_utils import configure_logging


LOGGER = logging.getLogger(__name__)


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
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe logs detalhados tambem no console.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = ProjectPaths.from_root(args.root)
    configure_logging(paths.pipeline_log_path, verbose=args.verbose)

    try:
        result = run_pipeline(paths, extract=not args.skip_extract)
    except Exception:
        LOGGER.exception("Pipeline interrompido por erro")
        return 1

    LOGGER.info("Resumo do pipeline")
    LOGGER.info("Arquivos extraidos: %s", len(result.extracted_files))
    LOGGER.info("Linhas consolidadas: %s", f"{result.rows:,}".replace(",", "."))
    LOGGER.info("CSV consolidado: %s", result.consolidated_csv_path)
    LOGGER.info("SQLite: %s", result.sqlite_path)
    LOGGER.info("Log salvo em: %s", paths.pipeline_log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
