from __future__ import annotations

from dataclasses import dataclass
import logging
import sqlite3
from pathlib import Path

import pandas as pd

from .config import EXPENSE_STAGE_COMMITTED, EXPENSE_STAGE_PAID, PRIORITY_FUNCTION_CODES


LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class AnalysisTables:
    completeness: pd.DataFrame
    function_indicators: pd.DataFrame
    function_summary: pd.DataFrame
    maceio_priority_functions: pd.DataFrame
    largest_gaps: pd.DataFrame
    maceio_health_education_subfunctions: pd.DataFrame
    complete_years: tuple[int, ...]
    reference_year: int


def read_sql(db_path: Path, query: str, params: list[str | int] | None = None) -> pd.DataFrame:
    LOGGER.debug("Executando consulta SQL na base %s", db_path)
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)


def load_function_expenses(db_path: Path) -> pd.DataFrame:
    LOGGER.info("Carregando despesas por funcao")
    query = """
        SELECT
            ano,
            capital,
            uf,
            populacao,
            codigo_conta AS codigo_funcao,
            conta AS funcao,
            estagio,
            valor
        FROM despesas
        WHERE tipo_conta = 'funcao'
          AND estagio IN (?, ?)
    """
    df = read_sql(db_path, query, [EXPENSE_STAGE_COMMITTED, EXPENSE_STAGE_PAID])
    LOGGER.debug("Despesas por funcao carregadas: %s linhas", len(df))
    return df


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return numerator / denominator.where(denominator.ne(0))


def calculate_execution_indicators(function_expenses: pd.DataFrame) -> pd.DataFrame:
    LOGGER.info("Calculando indicadores de execucao financeira")
    indicators = (
        function_expenses.pivot_table(
            index=["ano", "capital", "uf", "populacao", "codigo_funcao", "funcao"],
            columns="estagio",
            values="valor",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename(columns={EXPENSE_STAGE_COMMITTED: "empenhado", EXPENSE_STAGE_PAID: "pago"})
    )

    indicators["diferenca_empenhado_pago"] = indicators["empenhado"] - indicators["pago"]
    indicators["taxa_execucao"] = safe_divide(indicators["pago"], indicators["empenhado"])
    indicators["empenhado_per_capita"] = safe_divide(indicators["empenhado"], indicators["populacao"])
    indicators["pago_per_capita"] = safe_divide(indicators["pago"], indicators["populacao"])

    result = indicators.sort_values(["ano", "codigo_funcao", "taxa_execucao"], ascending=[True, True, False])
    LOGGER.debug("Indicadores calculados: %s linhas", len(result))
    return result


def count_capitals_by_year(db_path: Path) -> pd.DataFrame:
    LOGGER.info("Calculando completude por ano")
    query = """
        SELECT ano, COUNT(DISTINCT capital) AS qtd_capitais
        FROM despesas
        GROUP BY ano
        ORDER BY ano
    """
    return read_sql(db_path, query)


def infer_complete_years(completeness: pd.DataFrame) -> tuple[int, ...]:
    max_capitals = completeness["qtd_capitais"].max()
    years = completeness.loc[completeness["qtd_capitais"].eq(max_capitals), "ano"]
    complete_years = tuple(int(year) for year in years)
    LOGGER.info("Anos completos identificados: %s", ", ".join(map(str, complete_years)))
    return complete_years


def summarize_functions(indicators: pd.DataFrame, complete_years: tuple[int, ...]) -> pd.DataFrame:
    LOGGER.info("Resumindo funcoes para anos completos")
    base = indicators[indicators["ano"].isin(complete_years)].copy()
    summary = (
        base.groupby(["codigo_funcao", "funcao"], as_index=False)
        .agg(
            empenhado=("empenhado", "sum"),
            pago=("pago", "sum"),
            diferenca_empenhado_pago=("diferenca_empenhado_pago", "sum"),
            pago_per_capita_medio=("pago_per_capita", "mean"),
        )
        .sort_values("pago", ascending=False)
    )
    summary["taxa_execucao"] = safe_divide(summary["pago"], summary["empenhado"])
    return summary


def rank_maceio_priority_functions(
    indicators: pd.DataFrame,
    complete_years: tuple[int, ...],
    priority_codes: tuple[str, ...] = PRIORITY_FUNCTION_CODES,
) -> pd.DataFrame:
    LOGGER.info("Calculando ranking de Maceio em funcoes prioritarias")
    base = indicators[
        indicators["ano"].isin(complete_years) & indicators["codigo_funcao"].isin(priority_codes)
    ].copy()
    base["ranking_pago_per_capita"] = base.groupby(["ano", "codigo_funcao"])["pago_per_capita"].rank(
        ascending=False,
        method="min",
    )
    return base[base["capital"].str.contains("Macei", case=False, na=False)].sort_values(
        ["ano", "codigo_funcao"]
    )


def largest_execution_gaps(indicators: pd.DataFrame, year: int, limit: int = 15) -> pd.DataFrame:
    LOGGER.info("Selecionando maiores diferencas entre empenhado e pago em %s", year)
    base = indicators[(indicators["ano"].eq(year)) & (indicators["empenhado"] > 0)].copy()
    return base.sort_values("diferenca_empenhado_pago", ascending=False).head(limit)


def load_maceio_health_education_subfunctions(db_path: Path, year: int, limit: int = 15) -> pd.DataFrame:
    LOGGER.info("Carregando subfuncoes de Saude e Educacao de Maceio em %s", year)
    query = """
        SELECT
            ano,
            capital,
            codigo_conta,
            conta,
            estagio,
            valor
        FROM despesas
        WHERE ano = ?
          AND capital LIKE 'Macei%'
          AND tipo_conta = 'subfuncao'
          AND (codigo_conta LIKE '10.%' OR codigo_conta LIKE '12.%')
          AND estagio IN (?, ?)
    """
    raw = read_sql(db_path, query, [year, EXPENSE_STAGE_COMMITTED, EXPENSE_STAGE_PAID])

    subfunctions = (
        raw.pivot_table(
            index=["ano", "capital", "codigo_conta", "conta"],
            columns="estagio",
            values="valor",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename(columns={EXPENSE_STAGE_COMMITTED: "empenhado", EXPENSE_STAGE_PAID: "pago"})
    )
    subfunctions["taxa_execucao"] = safe_divide(subfunctions["pago"], subfunctions["empenhado"])
    return subfunctions.sort_values("pago", ascending=False).head(limit)


def build_analysis_tables(db_path: Path) -> AnalysisTables:
    LOGGER.info("Iniciando construcao das tabelas analiticas")
    completeness = count_capitals_by_year(db_path)
    complete_years = infer_complete_years(completeness)
    reference_year = max(complete_years)

    function_expenses = load_function_expenses(db_path)
    function_indicators = calculate_execution_indicators(function_expenses)
    function_summary = summarize_functions(function_indicators, complete_years)
    maceio_priority_functions = rank_maceio_priority_functions(function_indicators, complete_years)
    largest_gaps = largest_execution_gaps(function_indicators, reference_year)
    maceio_subfunctions = load_maceio_health_education_subfunctions(db_path, reference_year)

    tables = AnalysisTables(
        completeness=completeness,
        function_indicators=function_indicators,
        function_summary=function_summary,
        maceio_priority_functions=maceio_priority_functions,
        largest_gaps=largest_gaps,
        maceio_health_education_subfunctions=maceio_subfunctions,
        complete_years=complete_years,
        reference_year=reference_year,
    )
    LOGGER.info("Tabelas analiticas criadas com sucesso")
    return tables
