from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import ProjectPaths
from .indicators import build_analysis_tables
from .logging_utils import configure_logging
from .reporting import save_output_tables, save_report
from .visualizations import save_charts


LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera indicadores e relatorio analitico FINBRA/Siconfi.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Raiz do projeto. Por padrao, usa a pasta acima de src/.",
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
    configure_logging(paths.analysis_log_path, verbose=args.verbose)

    try:
        if not paths.sqlite_path.exists():
            raise FileNotFoundError("Base SQLite nao encontrada. Execute primeiro: python -m src.pipeline")

        tables = build_analysis_tables(paths.sqlite_path)
        saved_tables = save_output_tables(tables, paths.reports_dir)
        chart_paths = save_charts(tables, paths.reports_dir)
        report_path = save_report(tables, paths.reports_dir)
    except Exception:
        LOGGER.exception("Analise interrompida por erro")
        return 1

    LOGGER.info("Resumo da analise")
    LOGGER.info("Tabelas geradas: %s", len(saved_tables))
    LOGGER.info("Graficos gerados: %s", len(chart_paths))
    LOGGER.info("Relatorio gerado: %s", report_path)
    LOGGER.info("Log salvo em: %s", paths.analysis_log_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
