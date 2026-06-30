from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import sqlite3
import zipfile
from pathlib import Path

import pandas as pd

from .config import (
    CONSOLIDATED_COLUMNS,
    CSV_READ_OPTIONS,
    ProjectPaths,
    RAW_TO_CANONICAL_COLUMNS,
    SQLITE_INDEXES,
)


LOGGER = logging.getLogger(__name__)

FUNCTION_PATTERN = re.compile(r"^(?P<codigo>\d{2})\s+-\s+(?P<nome>.+)$")
SUBFUNCTION_PATTERN = re.compile(r"^(?P<codigo>\d{2}\.\d{3})\s+-\s+(?P<nome>.+)$")
OTHER_SUBFUNCTIONS_PATTERN = re.compile(r"^(?P<codigo>FU\d{2})\s+-\s+(?P<nome>.+)$")
CAPITAL_PATTERN = re.compile(r"^Prefeitura Municipal d(?:e|a|o|as|os) (?P<capital>.+) - (?P<uf>[A-Z]{2})$")


@dataclass(frozen=True)
class PipelineResult:
    extracted_files: list[Path]
    rows: int
    consolidated_csv_path: Path
    sqlite_path: Path


def discover_zip_files(compressed_data_dir: Path) -> list[Path]:
    LOGGER.debug("Buscando arquivos ZIP em %s", compressed_data_dir)
    zip_files = sorted(compressed_data_dir.rglob("*.zip"))
    if not zip_files:
        raise FileNotFoundError(f"Nenhum arquivo ZIP encontrado em {compressed_data_dir}.")
    LOGGER.info("ZIPs encontrados: %s", len(zip_files))
    return zip_files


def extract_zip_files(zip_files: list[Path], extracted_data_dir: Path) -> list[Path]:
    extracted_files: list[Path] = []

    for zip_path in zip_files:
        year = zip_path.parent.name
        LOGGER.debug("Extraindo %s para o ano %s", zip_path, year)
        if not year.isdigit():
            raise ValueError(f"O ano nao foi identificado pela pasta do arquivo: {zip_path}")

        destination_dir = extracted_data_dir / year
        destination_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path) as archive:
            for member in archive.infolist():
                if member.is_dir():
                    continue

                destination_path = destination_dir / Path(member.filename).name
                with archive.open(member) as source, destination_path.open("wb") as output:
                    output.write(source.read())
                extracted_files.append(destination_path)

    LOGGER.info("Arquivos CSV extraidos: %s", len(extracted_files))
    return extracted_files


def classify_account(account: str) -> str:
    if FUNCTION_PATTERN.match(account):
        return "funcao"
    if SUBFUNCTION_PATTERN.match(account):
        return "subfuncao"
    if OTHER_SUBFUNCTIONS_PATTERN.match(account):
        return "demais_subfuncoes"
    if account.startswith("Despesas "):
        return "total"
    return "outra"


def parse_account_code(account: str, account_type: str) -> str | None:
    patterns = {
        "funcao": FUNCTION_PATTERN,
        "subfuncao": SUBFUNCTION_PATTERN,
        "demais_subfuncoes": OTHER_SUBFUNCTIONS_PATTERN,
    }
    pattern = patterns.get(account_type)
    if not pattern:
        return None

    match = pattern.match(account)
    return match.group("codigo") if match else None


def parse_account_name(account: str) -> str:
    for pattern in (FUNCTION_PATTERN, SUBFUNCTION_PATTERN, OTHER_SUBFUNCTIONS_PATTERN):
        match = pattern.match(account)
        if match:
            return match.group("nome").strip()
    return account.strip()


def parse_capital(institution: str, uf: str) -> str:
    match = CAPITAL_PATTERN.match(institution)
    if match and match.group("uf") == uf:
        return match.group("capital").strip()
    return institution.strip()


def validate_columns(df: pd.DataFrame, source_path: Path) -> None:
    missing = sorted(set(RAW_TO_CANONICAL_COLUMNS) - set(df.columns))
    if missing:
        raise ValueError(f"Colunas ausentes em {source_path}: {missing}")
    LOGGER.debug("Colunas validadas em %s", source_path)


def read_finbra_csv(csv_path: Path) -> pd.DataFrame:
    year = int(csv_path.parent.name)
    LOGGER.debug("Lendo CSV %s", csv_path)
    df = pd.read_csv(csv_path, **CSV_READ_OPTIONS)
    validate_columns(df, csv_path)

    df = df.rename(columns=RAW_TO_CANONICAL_COLUMNS)
    df["ano"] = year
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
    df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce").astype("Int64")
    df["cod_ibge"] = pd.to_numeric(df["cod_ibge"], errors="coerce").astype("Int64")
    df["tipo_conta"] = df["conta"].apply(classify_account)
    df["codigo_conta"] = df.apply(lambda row: parse_account_code(row["conta"], row["tipo_conta"]), axis=1)
    df["nome_conta"] = df["conta"].apply(parse_account_name)
    df["capital"] = df.apply(lambda row: parse_capital(row["instituicao"], row["uf"]), axis=1)

    LOGGER.debug("CSV %s lido com %s linhas", csv_path, len(df))
    return df[CONSOLIDATED_COLUMNS]


def find_extracted_csv_files(extracted_data_dir: Path) -> list[Path]:
    LOGGER.debug("Buscando CSVs extraidos em %s", extracted_data_dir)
    csv_files = sorted(extracted_data_dir.rglob("finbra.csv"))
    if not csv_files:
        raise FileNotFoundError("Nenhum finbra.csv encontrado. Execute a extracao dos ZIPs primeiro.")
    LOGGER.info("CSVs para consolidar: %s", len(csv_files))
    return csv_files


def consolidate_csv_files(csv_files: list[Path]) -> pd.DataFrame:
    frames = [read_finbra_csv(csv_path) for csv_path in csv_files]
    consolidated = pd.concat(frames, ignore_index=True)
    LOGGER.info("Linhas consolidadas: %s", f"{len(consolidated):,}".replace(",", "."))
    return consolidated


def save_consolidated_csv(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.debug("Salvando CSV consolidado em %s", output_path)
    df.to_csv(output_path, index=False, compression={"method": "gzip", "mtime": 0})
    LOGGER.info("CSV consolidado salvo: %s", output_path)
    return output_path


def save_sqlite_database(df: pd.DataFrame, db_path: Path) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.debug("Salvando base SQLite em %s", db_path)
    with sqlite3.connect(db_path) as conn:
        df.to_sql("despesas", conn, if_exists="replace", index=False)
        for index_name, column_name in SQLITE_INDEXES:
            conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON despesas ({column_name})")
            LOGGER.debug("Indice SQLite criado ou reutilizado: %s(%s)", index_name, column_name)
        conn.execute("ANALYZE")
    LOGGER.info("Base SQLite salva: %s", db_path)
    return db_path


def run_pipeline(paths: ProjectPaths, extract: bool = True) -> PipelineResult:
    LOGGER.info("Iniciando pipeline de dados")
    extracted_files: list[Path] = []
    if extract:
        zip_files = discover_zip_files(paths.compressed_data_dir)
        extracted_files = extract_zip_files(zip_files, paths.extracted_data_dir)
    else:
        LOGGER.info("Extracao ignorada; usando dados ja existentes em %s", paths.extracted_data_dir)

    csv_files = find_extracted_csv_files(paths.extracted_data_dir)
    df = consolidate_csv_files(csv_files)
    csv_path = save_consolidated_csv(df, paths.consolidated_csv_path)
    sqlite_path = save_sqlite_database(df, paths.sqlite_path)

    result = PipelineResult(
        extracted_files=extracted_files,
        rows=len(df),
        consolidated_csv_path=csv_path,
        sqlite_path=sqlite_path,
    )
    LOGGER.info("Pipeline finalizado com sucesso")
    return result
