from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .indicators import AnalysisTables


LOGGER = logging.getLogger(__name__)

OUTPUT_TABLES = {
    "indicadores_funcao_capital.csv": "function_indicators",
    "completude_por_ano.csv": "completeness",
    "resumo_funcoes_anos_completos.csv": "function_summary",
    "maceio_funcoes_prioritarias.csv": "maceio_priority_functions",
    "maiores_gaps_ano_referencia.csv": "largest_gaps",
    "maceio_subfuncoes_saude_educacao_ano_referencia.csv": "maceio_health_education_subfunctions",
}


def format_currency(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value * 100:.1f}%".replace(".", ",")


def markdown_table(df: pd.DataFrame) -> str:
    columns = list(df.columns)
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in df.iterrows():
        values = [str(row[column]) for column in columns]
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def save_output_tables(tables: AnalysisTables, reports_dir: Path) -> list[Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []
    for filename, attribute in OUTPUT_TABLES.items():
        output_path = reports_dir / filename
        getattr(tables, attribute).to_csv(output_path, index=False)
        saved_paths.append(output_path)
        LOGGER.debug("Tabela salva: %s", output_path)
    LOGGER.info("Tabelas analiticas salvas: %s", len(saved_paths))
    return saved_paths


def render_report(tables: AnalysisTables) -> str:
    year_range = f"{min(tables.complete_years)} a {max(tables.complete_years)}"

    top_functions = tables.function_summary.head(8).copy()
    top_functions["pago"] = top_functions["pago"].apply(format_currency)
    top_functions["taxa_execucao"] = top_functions["taxa_execucao"].apply(format_percent)

    maceio = tables.maceio_priority_functions.copy()
    maceio["pago_per_capita"] = maceio["pago_per_capita"].apply(format_currency)
    maceio["taxa_execucao"] = maceio["taxa_execucao"].apply(format_percent)
    maceio["ranking_pago_per_capita"] = maceio["ranking_pago_per_capita"].astype("Int64")
    maceio = maceio[["ano", "funcao", "pago_per_capita", "taxa_execucao", "ranking_pago_per_capita"]]

    gaps = tables.largest_gaps[
        ["ano", "capital", "uf", "funcao", "diferenca_empenhado_pago", "taxa_execucao"]
    ].copy()
    gaps["diferenca_empenhado_pago"] = gaps["diferenca_empenhado_pago"].apply(format_currency)
    gaps["taxa_execucao"] = gaps["taxa_execucao"].apply(format_percent)

    subfunctions = tables.maceio_health_education_subfunctions[
        ["conta", "empenhado", "pago", "taxa_execucao"]
    ].copy()
    subfunctions["empenhado"] = subfunctions["empenhado"].apply(format_currency)
    subfunctions["pago"] = subfunctions["pago"].apply(format_currency)
    subfunctions["taxa_execucao"] = subfunctions["taxa_execucao"].apply(format_percent)

    latest_year = int(tables.completeness["ano"].max())
    latest_count = int(tables.completeness.loc[tables.completeness["ano"].eq(latest_year), "qtd_capitais"].iloc[0])
    max_count = int(tables.completeness["qtd_capitais"].max())

    return f"""# Relatorio de analise

## Escopo

Analise das despesas por funcao das capitais brasileiras no FINBRA/Siconfi. O foco e a comparacao entre despesas empenhadas e despesas pagas.

## Completude dos dados

{markdown_table(tables.completeness)}

O ano de {latest_year} tem {latest_count} capitais declaradas, contra {max_count} nos anos completos. Por isso, as conclusoes principais usam {year_range}; anos parciais ficam apenas como referencia de disponibilidade.

## Funcoes com maior volume pago, {year_range}

{markdown_table(top_functions[["funcao", "pago", "taxa_execucao"]])}

Saude, Educacao, Administracao e Urbanismo aparecem entre as areas mais relevantes do gasto municipal. A taxa de execucao deve ser lida junto com a natureza da funcao, pois obras, contratos longos e restos a pagar podem deslocar pagamentos para exercicios seguintes.

## Posicao de Maceio em funcoes prioritarias

{markdown_table(maceio)}

Maceio foi comparada por gasto pago per capita entre capitais no mesmo ano e funcao. Esse indicador reduz a distorcao causada pelo tamanho populacional das capitais.

## Maiores diferencas entre empenhado e pago em {tables.reference_year}

{markdown_table(gaps)}

Esses casos apontam onde a distancia em reais entre compromisso orcamentario e pagamento efetivo foi maior no ano de referencia. A diferenca pode indicar restos a pagar, atraso de execucao ou caracteristicas do calendario contratual.

## Subfuncoes de Saude e Educacao em Maceio, {tables.reference_year}

{markdown_table(subfunctions)}

As subfuncoes detalham quais frentes puxam o gasto dentro das funcoes agregadas. Em Maceio, esse recorte mostra onde os pagamentos se concentram dentro de Saude e Educacao.

## Decisoes tecnicas

- Os ZIPs originais sao extraidos por codigo para `dados_extraidos/`.
- A leitura trata `latin-1`, separador `;`, tres linhas de metadados e valores com decimal brasileiro.
- A coluna `Conta` e classificada para separar funcao, subfuncao, totais e demais subfuncoes, evitando dupla contagem.
- A base consolidada e salva em `dados_processados/finbra_consolidado.csv.gz`.
- A base consultavel usa SQLite em `dados_processados/finbra_consolidado.sqlite`, com indices nas dimensoes mais usadas.
- Os anos completos sao inferidos pela quantidade maxima de capitais declaradas, sem fixar manualmente 2024.
"""


def save_report(tables: AnalysisTables, reports_dir: Path) -> Path:
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / "relatorio_analise.md"
    report_path.write_text(render_report(tables), encoding="utf-8")
    LOGGER.info("Relatorio salvo: %s", report_path)
    return report_path
