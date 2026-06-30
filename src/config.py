from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path

    @classmethod
    def from_root(cls, root: Path | str | None = None) -> "ProjectPaths":
        project_root = Path(root).resolve() if root else Path(__file__).resolve().parents[1]
        return cls(root=project_root)

    @property
    def compressed_data_dir(self) -> Path:
        return self.root / "dados_compactos"

    @property
    def extracted_data_dir(self) -> Path:
        return self.root / "dados_extraidos"

    @property
    def processed_data_dir(self) -> Path:
        return self.root / "dados_processados"

    @property
    def reports_dir(self) -> Path:
        return self.root / "relatorios"

    @property
    def logs_dir(self) -> Path:
        return self.reports_dir / "logs"

    @property
    def consolidated_csv_path(self) -> Path:
        return self.processed_data_dir / "finbra_consolidado.csv.gz"

    @property
    def sqlite_path(self) -> Path:
        return self.processed_data_dir / "finbra_consolidado.sqlite"

    @property
    def pipeline_log_path(self) -> Path:
        return self.logs_dir / "pipeline.log"

    @property
    def analysis_log_path(self) -> Path:
        return self.logs_dir / "analysis.log"


DEFAULT_PATHS = ProjectPaths.from_root()

CSV_READ_OPTIONS = {
    "sep": ";",
    "skiprows": 3,
    "encoding": "latin-1",
    "decimal": ",",
    "thousands": ".",
}

RAW_TO_CANONICAL_COLUMNS = {
    "Institui\u00e7\u00e3o": "instituicao",
    "Cod.IBGE": "cod_ibge",
    "UF": "uf",
    "Popula\u00e7\u00e3o": "populacao",
    "Coluna": "estagio",
    "Conta": "conta",
    "Identificador da Conta": "identificador_conta",
    "Valor": "valor",
}

CONSOLIDATED_COLUMNS = [
    "ano",
    "capital",
    "instituicao",
    "cod_ibge",
    "uf",
    "populacao",
    "estagio",
    "conta",
    "tipo_conta",
    "codigo_conta",
    "nome_conta",
    "identificador_conta",
    "valor",
]

SQLITE_INDEXES = [
    ("idx_despesas_ano", "ano"),
    ("idx_despesas_capital", "capital"),
    ("idx_despesas_tipo_conta", "tipo_conta"),
    ("idx_despesas_estagio", "estagio"),
    ("idx_despesas_codigo_conta", "codigo_conta"),
]

EXPENSE_STAGE_COMMITTED = "Despesas Empenhadas"
EXPENSE_STAGE_PAID = "Despesas Pagas"
PRIORITY_FUNCTION_CODES = ("10", "12", "04", "15", "08")
