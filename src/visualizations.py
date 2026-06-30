from __future__ import annotations

from dataclasses import dataclass
from html import escape
import logging
from pathlib import Path
from textwrap import shorten

import pandas as pd

from .indicators import AnalysisTables


LOGGER = logging.getLogger(__name__)

SVG_WIDTH = 1120
BAR_HEIGHT = 34
BAR_GAP = 14
MARGIN_LEFT = 260
MARGIN_RIGHT = 160
MARGIN_TOP = 96
MARGIN_BOTTOM = 72
PALETTE = ["#2563eb", "#0f766e", "#dc2626", "#7c3aed", "#ca8a04", "#0891b2", "#be185d", "#16a34a"]


@dataclass(frozen=True)
class ChartSpec:
    filename: str
    title: str
    description: str


def format_billions(value: float) -> str:
    return f"R$ {value / 1_000_000_000:.1f} bi".replace(".", ",")


def format_millions(value: float) -> str:
    return f"R$ {value / 1_000_000:.1f} mi".replace(".", ",")


def format_currency_short(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return format_billions(value)
    if abs(value) >= 1_000_000:
        return format_millions(value)
    return f"R$ {value:,.0f}".replace(",", ".")


def format_percent(value: float) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{value * 100:.1f}%".replace(".", ",")


def svg_document(width: int, height: int, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
  <rect width="100%" height="100%" fill="#ffffff"/>
{body}
</svg>
"""


def text(x: float, y: float, content: str, size: int = 16, weight: int = 400, fill: str = "#111827", anchor: str = "start") -> str:
    return (
        f'  <text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{escape(content)}</text>'
    )


def title_block(title: str, subtitle: str, width: int = SVG_WIDTH) -> str:
    return "\n".join(
        [
            text(32, 42, title, size=24, weight=700),
            text(32, 70, subtitle, size=14, fill="#4b5563"),
            f'  <line x1="32" y1="84" x2="{width - 32}" y2="84" stroke="#e5e7eb" stroke-width="1"/>',
        ]
    )


def horizontal_bar_chart(
    data: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    subtitle: str,
    output_path: Path,
    value_formatter=format_currency_short,
    color: str = "#2563eb",
) -> Path:
    data = data.copy().sort_values(value_col, ascending=False)
    chart_height = len(data) * (BAR_HEIGHT + BAR_GAP) - BAR_GAP
    height = MARGIN_TOP + chart_height + MARGIN_BOTTOM
    bar_max_width = SVG_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    max_value = float(data[value_col].max()) if len(data) else 0

    elements = [title_block(title, subtitle)]
    elements.append(
        f'  <line x1="{MARGIN_LEFT}" y1="{MARGIN_TOP - 12}" x2="{MARGIN_LEFT}" y2="{MARGIN_TOP + chart_height + 12}" stroke="#e5e7eb"/>'
    )

    for idx, (_, row) in enumerate(data.iterrows()):
        y = MARGIN_TOP + idx * (BAR_HEIGHT + BAR_GAP)
        value = float(row[value_col])
        width = 0 if max_value == 0 else (value / max_value) * bar_max_width
        label = shorten(str(row[label_col]), width=34, placeholder="...")
        elements.append(text(MARGIN_LEFT - 16, y + 23, label, size=14, fill="#374151", anchor="end"))
        elements.append(
            f'  <rect x="{MARGIN_LEFT}" y="{y}" width="{width:.1f}" height="{BAR_HEIGHT}" rx="4" fill="{color}"/>'
        )
        elements.append(text(MARGIN_LEFT + width + 12, y + 23, value_formatter(value), size=13, fill="#374151"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_document(SVG_WIDTH, height, "\n".join(elements)), encoding="utf-8")
    LOGGER.info("Grafico salvo: %s", output_path)
    return output_path


def grouped_bar_chart(
    data: pd.DataFrame,
    label_col: str,
    first_col: str,
    second_col: str,
    title: str,
    subtitle: str,
    output_path: Path,
    first_label: str = "Empenhado",
    second_label: str = "Pago",
) -> Path:
    data = data.copy().sort_values(second_col, ascending=False)
    group_height = 54
    height = MARGIN_TOP + len(data) * (group_height + BAR_GAP) + MARGIN_BOTTOM
    bar_max_width = SVG_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    max_value = float(data[[first_col, second_col]].max().max()) if len(data) else 0

    elements = [title_block(title, subtitle)]
    elements.extend(
        [
            f'  <rect x="{SVG_WIDTH - 315}" y="35" width="14" height="14" fill="#93c5fd"/>',
            text(SVG_WIDTH - 292, 47, first_label, size=13, fill="#374151"),
            f'  <rect x="{SVG_WIDTH - 195}" y="35" width="14" height="14" fill="#2563eb"/>',
            text(SVG_WIDTH - 172, 47, second_label, size=13, fill="#374151"),
        ]
    )

    for idx, (_, row) in enumerate(data.iterrows()):
        y = MARGIN_TOP + idx * (group_height + BAR_GAP)
        label = shorten(str(row[label_col]), width=34, placeholder="...")
        first_value = float(row[first_col])
        second_value = float(row[second_col])
        first_width = 0 if max_value == 0 else (first_value / max_value) * bar_max_width
        second_width = 0 if max_value == 0 else (second_value / max_value) * bar_max_width
        elements.append(text(MARGIN_LEFT - 16, y + 34, label, size=14, fill="#374151", anchor="end"))
        elements.append(f'  <rect x="{MARGIN_LEFT}" y="{y}" width="{first_width:.1f}" height="20" rx="3" fill="#93c5fd"/>')
        elements.append(f'  <rect x="{MARGIN_LEFT}" y="{y + 26}" width="{second_width:.1f}" height="20" rx="3" fill="#2563eb"/>')
        elements.append(text(MARGIN_LEFT + max(first_width, second_width) + 12, y + 34, format_currency_short(second_value), size=13, fill="#374151"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_document(SVG_WIDTH, height, "\n".join(elements)), encoding="utf-8")
    LOGGER.info("Grafico salvo: %s", output_path)
    return output_path


def line_chart(
    data: pd.DataFrame,
    title: str,
    subtitle: str,
    output_path: Path,
    x_col: str = "ano",
    y_col: str = "pago_per_capita",
    series_col: str = "funcao",
) -> Path:
    width = SVG_WIDTH
    height = 640
    left = 86
    right = 260
    top = 112
    bottom = 86
    chart_width = width - left - right
    chart_height = height - top - bottom

    years = sorted(int(year) for year in data[x_col].unique())
    max_y = float(data[y_col].max()) if len(data) else 0
    min_year, max_year = min(years), max(years)

    def x_pos(year: int) -> float:
        if max_year == min_year:
            return left + chart_width / 2
        return left + ((year - min_year) / (max_year - min_year)) * chart_width

    def y_pos(value: float) -> float:
        return top + chart_height - (0 if max_y == 0 else (value / max_y) * chart_height)

    elements = [title_block(title, subtitle, width)]
    elements.append(f'  <line x1="{left}" y1="{top + chart_height}" x2="{left + chart_width}" y2="{top + chart_height}" stroke="#d1d5db"/>')
    elements.append(f'  <line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_height}" stroke="#d1d5db"/>')

    for year in years:
        x = x_pos(year)
        elements.append(f'  <line x1="{x:.1f}" y1="{top + chart_height}" x2="{x:.1f}" y2="{top + chart_height + 6}" stroke="#9ca3af"/>')
        elements.append(text(x, top + chart_height + 28, str(year), size=12, fill="#4b5563", anchor="middle"))

    for tick in range(5):
        value = (max_y / 4) * tick
        y = y_pos(value)
        elements.append(f'  <line x1="{left}" y1="{y:.1f}" x2="{left + chart_width}" y2="{y:.1f}" stroke="#f3f4f6"/>')
        elements.append(text(left - 10, y + 4, f"R$ {value:,.0f}".replace(",", "."), size=11, fill="#6b7280", anchor="end"))

    for idx, (series, group) in enumerate(data.groupby(series_col)):
        color = PALETTE[idx % len(PALETTE)]
        group = group.sort_values(x_col)
        points = [(x_pos(int(row[x_col])), y_pos(float(row[y_col]))) for _, row in group.iterrows()]
        point_string = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        elements.append(f'  <polyline points="{point_string}" fill="none" stroke="{color}" stroke-width="3"/>')
        for x, y in points:
            elements.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}"/>')
        legend_y = top + idx * 28
        elements.append(f'  <rect x="{width - right + 42}" y="{legend_y - 11}" width="14" height="14" fill="{color}"/>')
        elements.append(text(width - right + 64, legend_y + 1, shorten(str(series), width=28, placeholder="..."), size=13, fill="#374151"))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(svg_document(width, height, "\n".join(elements)), encoding="utf-8")
    LOGGER.info("Grafico salvo: %s", output_path)
    return output_path


def completeness_chart(tables: AnalysisTables, charts_dir: Path) -> Path:
    return horizontal_bar_chart(
        tables.completeness,
        label_col="ano",
        value_col="qtd_capitais",
        title="Completude dos dados por ano",
        subtitle="Quantidade de capitais declaradas no FINBRA/Siconfi",
        output_path=charts_dir / "completude_por_ano.svg",
        value_formatter=lambda value: f"{int(value)} capitais",
        color="#0f766e",
    )


def top_functions_chart(tables: AnalysisTables, charts_dir: Path) -> Path:
    data = tables.function_summary.head(10)
    return horizontal_bar_chart(
        data,
        label_col="funcao",
        value_col="pago",
        title=f"Funcoes com maior volume pago ({min(tables.complete_years)}-{max(tables.complete_years)})",
        subtitle="Valores pagos agregados nos anos completos",
        output_path=charts_dir / "top_funcoes_pagas.svg",
        value_formatter=format_billions,
        color="#2563eb",
    )


def maceio_per_capita_chart(tables: AnalysisTables, charts_dir: Path) -> Path:
    return line_chart(
        tables.maceio_priority_functions,
        title="Evolucao de Maceio por funcao prioritaria",
        subtitle="Despesa paga per capita nos anos completos",
        output_path=charts_dir / "maceio_pago_per_capita.svg",
    )


def largest_gaps_chart(tables: AnalysisTables, charts_dir: Path) -> Path:
    data = tables.largest_gaps.head(10).copy()
    data["rotulo"] = data["capital"] + " | " + data["funcao"]
    return horizontal_bar_chart(
        data,
        label_col="rotulo",
        value_col="diferenca_empenhado_pago",
        title=f"Maiores gaps entre empenhado e pago em {tables.reference_year}",
        subtitle="Diferenca absoluta em reais por capital e funcao",
        output_path=charts_dir / "maiores_gaps_empenhado_pago.svg",
        value_formatter=format_millions,
        color="#dc2626",
    )


def maceio_subfunctions_chart(tables: AnalysisTables, charts_dir: Path) -> Path:
    data = tables.maceio_health_education_subfunctions.head(10)
    return grouped_bar_chart(
        data,
        label_col="conta",
        first_col="empenhado",
        second_col="pago",
        title=f"Subfuncoes de Saude e Educacao em Maceio ({tables.reference_year})",
        subtitle="Comparacao entre despesa empenhada e paga",
        output_path=charts_dir / "maceio_subfuncoes_empenhado_pago.svg",
    )


def save_charts(tables: AnalysisTables, reports_dir: Path) -> list[Path]:
    charts_dir = reports_dir / "figuras"
    chart_paths = [
        completeness_chart(tables, charts_dir),
        top_functions_chart(tables, charts_dir),
        maceio_per_capita_chart(tables, charts_dir),
        largest_gaps_chart(tables, charts_dir),
        maceio_subfunctions_chart(tables, charts_dir),
    ]
    LOGGER.info("Graficos salvos: %s", len(chart_paths))
    return chart_paths
