"""
services/content/calculator_report.py

Helpers para apresentar e exportar o diagnóstico da calculadora pública.
"""

# pyright: reportMissingTypeStubs=false

from __future__ import annotations

import importlib
import io
import re
import unicodedata
from typing import Any, cast

from core.branding import (
    COMPOSTO_WEB_ACCENT,
    COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH,
    COMPOSTO_WEB_PRIMARY,
    COMPOSTO_WEB_SECONDARY,
    COMPOSTO_WEB_SURFACE,
    COMPOSTO_WEB_TEXT,
    COMPOSTO_WEB_WHITE,
)
from models.content_calculator_result import ContentCalculatorResult
from schemas.content_inbound import CalculatorCompanySegment
from services.content.lm_calculator import (
    SEGMENT_LABELS as RESULT_MESSAGE_SEGMENT_LABELS,
)
from services.content.lm_calculator import (
    build_result_message,
)

PROCESS_LABELS: dict[str, str] = {
    "financeiro": "Financeiro",
    "juridico": "Jurídico",
    "operacional": "Operacional",
    "atendimento": "Atendimento",
    "rh": "RH",
}

ROLE_LABELS: dict[str, str] = {
    "ceo": "CEO",
    "cfo": "CFO",
    "gerente": "Gerência",
    "analista": "Analista",
    "operacional": "Operacional",
}

SEGMENT_LABELS: dict[str, str] = {
    "clinicas": "Clínicas",
    "industria": "Indústria",
    "advocacia": "Advocacia",
    "contabilidade": "Contabilidade",
    "varejo": "Varejo",
    "servicos": "Serviços",
}

COMPANY_SIZE_LABELS: dict[str, str] = {
    "pequena": "Pequena",
    "media": "Média",
    "grande": "Grande",
}

COMPANY_SIZE_CONTEXT_LABELS: dict[str, str] = {
    "pequena": "pequeno",
    "media": "médio",
    "grande": "grande",
}

PROCESS_AREA_LABELS: dict[str, str] = {
    "1": "1 área",
    "2-3": "2 a 3 áreas",
    "4+": "4 ou mais áreas",
}

SEGMENT_NEXT_STEPS: dict[str, str] = {
    "clinicas": (
        "O próximo passo recomendado é mapear os repasses entre agenda, atendimento, "
        "faturamento e financeiro para identificar onde o processo perde velocidade."
    ),
    "industria": (
        "O próximo passo recomendado é destrinchar os repasses manuais entre operação, "
        "qualidade e backoffice para priorizar o gargalo com maior custo oculto."
    ),
    "advocacia": (
        "O próximo passo recomendado é detalhar as etapas com maior volume de prazos, "
        "documentos e validações para atacar o ponto de maior recorrência."
    ),
    "contabilidade": (
        "O próximo passo recomendado é revisar os fluxos de conferência, cobrança e fechamento "
        "que mais pressionam a rotina mensal da equipe."
    ),
    "varejo": (
        "O próximo passo recomendado é revisar os pontos de contato entre comercial, atendimento "
        "e backoffice para reduzir repasses e retrabalho."
    ),
    "servicos": (
        "O próximo passo recomendado é mapear as etapas recorrentes de coordenação e execução "
        "para priorizar o fluxo com maior consumo de horas."
    ),
}


def _coerce_float(value: object | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _format_number(value: object | None, *, decimals: int = 1) -> str:
    amount = _coerce_float(value)
    if amount is None:
        return "—"
    formatted = f"{amount:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def format_brl(value: object | None) -> str:
    amount = _coerce_float(value)
    if amount is None:
        return "—"
    return f"R$ {_format_number(amount, decimals=2)}"


def format_percent(value: object | None) -> str:
    amount = _coerce_float(value)
    if amount is None:
        return "—"
    return f"{_format_number(amount, decimals=1)}%"


def format_months(value: object | None) -> str:
    amount = _coerce_float(value)
    if amount is None:
        return "—"
    return f"{_format_number(amount, decimals=1)} meses"


def get_process_label(process_type: str | None) -> str:
    if process_type is None:
        return "Processo"
    return PROCESS_LABELS.get(process_type, process_type.replace("_", " ").title())


def get_role_label(role: str | None) -> str:
    if role is None:
        return "Perfil não informado"
    return ROLE_LABELS.get(role, role.replace("_", " ").title())


def get_segment_label(segment: str | None) -> str:
    if segment is None:
        return "Segmento não informado"
    return SEGMENT_LABELS.get(segment, segment.replace("_", " ").title())


def get_company_size_label(size: str | None) -> str:
    if size is None:
        return "Porte não informado"
    return COMPANY_SIZE_LABELS.get(size, size.replace("_", " ").title())


def get_process_area_label(area_span: str | None) -> str:
    if area_span is None:
        return "Escopo não informado"
    return PROCESS_AREA_LABELS.get(area_span, area_span)


def build_context_summary(result: ContentCalculatorResult) -> str:
    context_parts: list[str] = []
    if result.company_segment:
        context_parts.append(f"segmento de {get_segment_label(result.company_segment).lower()}")
    if result.company_size:
        size_label = COMPANY_SIZE_CONTEXT_LABELS.get(
            result.company_size,
            get_company_size_label(result.company_size).lower(),
        )
        context_parts.append(f"empresa de porte {size_label}")
    if result.process_area_span:
        context_parts.append(
            f"fluxo envolvendo {get_process_area_label(result.process_area_span).lower()}"
        )
    if result.tipo_processo:
        context_parts.append(f"processo {get_process_label(result.tipo_processo).lower()}")
    if not context_parts:
        return "Cenário analisado com base nos dados informados na calculadora pública."
    return "Cenário analisado: " + ", ".join(context_parts) + "."


def build_executive_summary(result: ContentCalculatorResult) -> str:
    company_segment = cast(
        CalculatorCompanySegment | None,
        next(
            (
                segment
                for segment in RESULT_MESSAGE_SEGMENT_LABELS
                if segment == result.company_segment
            ),
            None,
        ),
    )

    return build_result_message(
        custo_anual=_coerce_float(result.custo_anual) or 0.0,
        roi_estimado=_coerce_float(result.roi_estimado) or 0.0,
        payback_meses=_coerce_float(result.payback_meses) or 0.0,
        company_segment=company_segment,
    )


def build_next_step_recommendation(result: ContentCalculatorResult) -> str:
    segment = result.company_segment
    if segment is not None and segment in SEGMENT_NEXT_STEPS:
        return SEGMENT_NEXT_STEPS[segment]

    process_label = get_process_label(result.tipo_processo).lower()
    return (
        f"O próximo passo recomendado é detalhar o fluxo de {process_label} com maior volume "
        "de repasses manuais para refinar prioridade, escopo e retorno financeiro."
    )


def build_diagnosis_filename(result: ContentCalculatorResult) -> str:
    reference = result.company or result.name or "diagnostico"
    normalized = unicodedata.normalize("NFKD", reference).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-") or "diagnostico"
    result_ref = str(result.id)[:8] if result.id else "simulacao"
    return f"diagnostico-roi-{slug[:40]}-{result_ref}.pdf"


def build_calculator_diagnosis_pdf(
    result: ContentCalculatorResult,
    *,
    lead_magnet_title: str | None = None,
) -> tuple[str, bytes]:
    try:
        colors = importlib.import_module("reportlab.lib.colors")
        A4 = cast(tuple[float, float], importlib.import_module("reportlab.lib.pagesizes").A4)
        reportlab_utils = importlib.import_module("reportlab.lib.utils")
        ImageReader = reportlab_utils.ImageReader
        simpleSplit = reportlab_utils.simpleSplit
        canvas = cast(Any, importlib.import_module("reportlab.pdfgen.canvas"))
    except ImportError as exc:
        raise RuntimeError("Biblioteca reportlab não está disponível.") from exc

    width, height = A4
    margin = 40
    bottom_margin = 54
    buffer = io.BytesIO()
    pdf: Any = canvas.Canvas(buffer, pagesize=A4)

    brand_dark = colors.HexColor(COMPOSTO_WEB_PRIMARY)
    brand = colors.HexColor(COMPOSTO_WEB_SECONDARY)
    accent = colors.HexColor(COMPOSTO_WEB_ACCENT)
    brand_soft = colors.HexColor(COMPOSTO_WEB_SURFACE)
    border = colors.HexColor("#d9dfeb")
    text_primary = colors.HexColor(COMPOSTO_WEB_PRIMARY)
    text_secondary = colors.HexColor(COMPOSTO_WEB_TEXT)
    white = colors.HexColor(COMPOSTO_WEB_WHITE)
    success = colors.HexColor("#067647")
    danger = colors.HexColor("#B42318")

    logo_reader: Any | None = None
    logo_width = 210.0
    logo_height = 39.0
    try:
        logo_reader = ImageReader(str(COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH))
        if logo_reader is not None:
            original_width, original_height = cast(tuple[float, float], logo_reader.getSize())
            if original_width > 0:
                logo_height = logo_width * (original_height / original_width)
    except Exception:
        logo_reader = None

    y = height - 120

    def set_document_meta() -> None:
        pdf.setAuthor("Composto Web")
        pdf.setTitle("Diagnóstico de ROI da Automação | Composto Web")

    def draw_page_frame(*, primary: bool) -> None:
        nonlocal y
        header_compact = not primary
        current_logo_width = 182.0 if header_compact else logo_width
        current_logo_height = logo_height * (current_logo_width / logo_width)
        logo_y = height - (76 if header_compact else 86)
        pill_y_top = height - (44 if header_compact else 48)
        divider_y = height - (88 if header_compact else 100)
        pdf.setFillColor(white)
        pdf.rect(0, 0, width, height, fill=1, stroke=0)
        header_color = brand_dark if primary else brand
        pdf.setFillColor(header_color)
        pdf.rect(0, height - 16, width, 16, fill=1, stroke=0)
        pdf.setFillColor(accent)
        pdf.rect(0, height - 22, width, 6, fill=1, stroke=0)
        if logo_reader is not None:
            pdf.drawImage(
                logo_reader,
                margin,
                logo_y,
                width=current_logo_width,
                height=current_logo_height,
                mask="auto",
            )
        else:
            pdf.setFillColor(text_primary)
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(margin, height - 58, "COMPOSTO WEB")
        draw_centered_pill(
            x=width - margin - 176,
            y_top=pill_y_top,
            width_value=176,
            height_value=22,
            text="DIAGNÓSTICO EXECUTIVO",
            fill_color=accent,
            text_color=white,
        )
        pdf.setFillColor(text_secondary)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawRightString(
            width - margin,
            height - (76 if header_compact else 80),
            "ROI da automação e leitura inicial do cenário",
        )
        pdf.setStrokeColor(accent)
        pdf.line(margin, 30, width - margin, 30)
        pdf.setFillColor(text_secondary)
        pdf.setFont("Helvetica", 8.5)
        pdf.drawString(margin, 16, "Diagnóstico preparado pela equipe da Composto Web")
        pdf.drawRightString(width - margin, 16, f"Página {pdf.getPageNumber()}")
        pdf.setStrokeColor(border)
        pdf.line(margin, divider_y, width - margin, divider_y)
        y = height - (102 if header_compact else 126)

    def ensure_space(height_needed: float) -> None:
        nonlocal y
        if y - height_needed < bottom_margin:
            pdf.showPage()
            set_document_meta()
            draw_page_frame(primary=False)

    def split_lines(text: str, font_name: str, font_size: float, max_width: float) -> list[str]:
        return cast(list[str], simpleSplit(text, font_name, font_size, max_width))

    def draw_centered_pill(
        *,
        x: float,
        y_top: float,
        width_value: float,
        height_value: float,
        text: str,
        fill_color: Any,
        text_color: Any,
        font_name: str = "Helvetica-Bold",
        font_size: float = 8.5,
    ) -> None:
        pdf.setFillColor(fill_color)
        pdf.roundRect(
            x, y_top - height_value, width_value, height_value, height_value / 2, fill=1, stroke=0
        )
        pdf.setFillColor(text_color)
        pdf.setFont(font_name, font_size)
        text_y = y_top - (height_value / 2) - (font_size * 0.32)
        pdf.drawCentredString(x + (width_value / 2), text_y, text)

    def build_executive_highlight_runs(text: str) -> list[tuple[str, Any, str]]:
        pattern = re.compile(
            r"(R\$ [\d\.\,]+/ano|retorno estimado de\s+|\d[\d\.\,]*%|\d[\d\.\,]* meses?)",
            flags=re.IGNORECASE,
        )
        runs: list[tuple[str, Any, str]] = []
        for chunk in pattern.split(text):
            if not chunk:
                continue
            if pattern.fullmatch(chunk):
                normalized = chunk.strip().lower()
                if normalized.startswith("retorno estimado de"):
                    runs.append((chunk, success, "Helvetica-Bold"))
                    continue
                runs.append(
                    (
                        chunk,
                        danger if chunk.startswith("R$") else success,
                        "Helvetica-Bold",
                    )
                )
                continue
            for token in re.findall(r"\s+|\S+", chunk):
                if token:
                    runs.append((token, text_primary, "Helvetica"))
        return runs

    def layout_text_runs(
        runs: list[tuple[str, Any, str]],
        *,
        font_size: float,
        max_width: float,
    ) -> list[list[tuple[str, Any, str]]]:
        lines: list[list[tuple[str, Any, str]]] = []
        current_line: list[tuple[str, Any, str]] = []
        current_width = 0.0
        for text, color, font_name in runs:
            candidate = text
            candidate_width = pdf.stringWidth(candidate, font_name, font_size)
            if not candidate.strip() and not current_line:
                continue
            if current_line and current_width + candidate_width > max_width and candidate.strip():
                lines.append(current_line)
                current_line = []
                current_width = 0.0
                candidate = candidate.lstrip()
                candidate_width = pdf.stringWidth(candidate, font_name, font_size)
            if not candidate:
                continue
            current_line.append((candidate, color, font_name))
            current_width += candidate_width
        if current_line:
            lines.append(current_line)
        return lines

    def draw_text_run_lines(
        lines: list[list[tuple[str, Any, str]]],
        *,
        x: float,
        y_top: float,
        font_size: float,
        line_height: float,
    ) -> None:
        current_y = y_top
        for line in lines:
            current_x = x
            for text, color, font_name in line:
                pdf.setFillColor(color)
                pdf.setFont(font_name, font_size)
                pdf.drawString(current_x, current_y, text)
                current_x += pdf.stringWidth(text, font_name, font_size)
            current_y -= line_height

    def draw_section_heading(title: str) -> None:
        nonlocal y
        ensure_space(34)
        pdf.setFillColor(text_primary)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(margin, y, title)
        pdf.setFillColor(accent)
        pdf.roundRect(margin, y - 10, 52, 4, 2, fill=1, stroke=0)
        y -= 30

    def draw_highlight_box(title: str, text: str) -> None:
        nonlocal y
        summary_font_size = 12.0
        summary_line_height = 18.0
        summary_lines = layout_text_runs(
            build_executive_highlight_runs(text),
            font_size=summary_font_size,
            max_width=width - (margin * 2) - 80,
        )
        box_height = max(104.0, 54.0 + (len(summary_lines) * summary_line_height))
        ensure_space(box_height + 10)
        pdf.setFillColor(white)
        pdf.setStrokeColor(border)
        pdf.roundRect(
            margin, y - box_height, width - (margin * 2), box_height, 18, fill=1, stroke=1
        )
        pdf.setFillColor(accent)
        pdf.roundRect(margin + 20, y - box_height + 20, 7, box_height - 40, 3.5, fill=1, stroke=0)
        pdf.setFillColor(brand)
        pdf.setFont("Helvetica-Bold", 8.5)
        pdf.drawString(margin + 48, y - 28, title.upper())
        draw_text_run_lines(
            summary_lines,
            x=margin + 48,
            y_top=y - 58,
            font_size=summary_font_size,
            line_height=summary_line_height,
        )
        y -= box_height + 26

    def draw_metric_cards(cards: list[tuple[str, str]]) -> None:
        nonlocal y
        card_gap = 10
        card_width = (width - (margin * 2) - card_gap) / 2
        backgrounds = [white, brand_soft, white, brand_soft]
        prepared_cards: list[tuple[str, list[str], Any, float]] = []
        for index, (label, value) in enumerate(cards):
            value_lines = split_lines(value, "Helvetica-Bold", 12, card_width - 28)
            card_height = max(78.0, 52.0 + (len(value_lines) * 14.0))
            prepared_cards.append(
                (label, value_lines, backgrounds[index % len(backgrounds)], card_height)
            )

        for index in range(0, len(prepared_cards), 2):
            row_cards = prepared_cards[index : index + 2]
            row_height = max(card[3] for card in row_cards)
            ensure_space(row_height + 12)
            row_top = y
            for column, (label, value_lines, background, _) in enumerate(row_cards):
                card_x = margin + (column * (card_width + card_gap))
                card_y = row_top - row_height
                pdf.setFillColor(background)
                pdf.setStrokeColor(border)
                pdf.roundRect(card_x, card_y, card_width, row_height, 16, fill=1, stroke=1)
                pdf.setFillColor(accent)
                pdf.roundRect(card_x + 14, card_y + row_height - 12, 54, 4, 2, fill=1, stroke=0)
                pdf.setFillColor(text_secondary)
                pdf.setFont("Helvetica-Bold", 8.5)
                pdf.drawString(card_x + 14, card_y + row_height - 26, label.upper())
                pdf.setFillColor(text_primary)
                pdf.setFont("Helvetica-Bold", 12)
                value_y = card_y + row_height - 44
                for line in value_lines:
                    pdf.drawString(card_x + 14, value_y, line)
                    value_y -= 14
            y -= row_height + 12

        y -= 2

    def build_detail_panel_layout(
        rows: list[tuple[str, str]],
        *,
        panel_width: float,
    ) -> dict[str, Any]:
        content_padding_x = 18.0
        header_top_padding = 22.0
        header_gap = 26.0
        row_gap = 8.0
        bottom_padding = 18.0
        inner_width = panel_width - (content_padding_x * 2)
        label_width = min(156.0, max(92.0, inner_width * 0.28))
        value_x = content_padding_x + label_width + 12.0
        value_width = inner_width - label_width - 12.0
        row_specs: list[tuple[str, list[str], float, float]] = []
        for label, value in rows:
            wrapped = split_lines(value, "Helvetica", 10.5, value_width)
            text_block_height = max(len(wrapped), 1) * 14.0
            row_height = max(30.0, text_block_height + 6.0)
            row_specs.append((label, wrapped, row_height, text_block_height))
        panel_height = (
            header_top_padding
            + header_gap
            + sum(row_height for _, _, row_height, _ in row_specs)
            + (max(len(row_specs) - 1, 0) * row_gap)
            + bottom_padding
        )
        return {
            "content_padding_x": content_padding_x,
            "header_top_padding": header_top_padding,
            "header_gap": header_gap,
            "row_gap": row_gap,
            "panel_height": panel_height,
            "row_specs": row_specs,
            "value_x": value_x,
        }

    def draw_detail_panel_box(
        *,
        title: str,
        rows: list[tuple[str, str]],
        x: float,
        y_top: float,
        panel_width: float,
        background: Any,
    ) -> float:
        layout = build_detail_panel_layout(rows, panel_width=panel_width)
        panel_height = cast(float, layout["panel_height"])
        content_padding_x = cast(float, layout["content_padding_x"])
        header_top_padding = cast(float, layout["header_top_padding"])
        header_gap = cast(float, layout["header_gap"])
        row_gap = cast(float, layout["row_gap"])
        value_x = cast(float, layout["value_x"])
        row_specs = cast(list[tuple[str, list[str], float, float]], layout["row_specs"])

        pdf.setFillColor(background)
        pdf.setStrokeColor(border)
        pdf.roundRect(x, y_top - panel_height, panel_width, panel_height, 18, fill=1, stroke=1)

        label_x = x + content_padding_x
        value_x_abs = x + value_x
        inner_y = y_top - header_top_padding
        pdf.setFillColor(text_primary)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(label_x, inner_y, title)
        inner_y -= header_gap

        for index, (label, wrapped, row_height, text_block_height) in enumerate(row_specs):
            row_top = inner_y
            row_center = row_top - (row_height / 2)
            pdf.setFillColor(text_secondary)
            pdf.setFont("Helvetica-Bold", 9.5)
            pdf.drawString(label_x, row_center - (9.5 * 0.32), label)
            pdf.setFillColor(text_primary)
            pdf.setFont("Helvetica", 10.5)
            line_y = row_center + (text_block_height / 2) - 10.5
            for line in wrapped:
                pdf.drawString(value_x_abs, line_y, line)
                line_y -= 14
            inner_y -= row_height
            if index != len(row_specs) - 1:
                pdf.setStrokeColor(border)
                separator_y = inner_y - (row_gap / 2)
                pdf.line(label_x, separator_y, x + panel_width - content_padding_x, separator_y)
                inner_y -= row_gap

        return panel_height

    def draw_detail_panel(
        title: str,
        rows: list[tuple[str, str]],
        *,
        background: Any,
    ) -> None:
        nonlocal y
        panel_width = width - (margin * 2)
        panel_height = cast(
            float,
            build_detail_panel_layout(rows, panel_width=panel_width)["panel_height"],
        )
        ensure_space(panel_height + 10)
        draw_detail_panel_box(
            title=title,
            rows=rows,
            x=margin,
            y_top=y,
            panel_width=panel_width,
            background=background,
        )
        y -= panel_height + 14

    def draw_split_detail_panels(
        *,
        left_title: str,
        left_rows: list[tuple[str, str]],
        left_background: Any,
        right_title: str,
        right_rows: list[tuple[str, str]],
        right_background: Any,
    ) -> None:
        nonlocal y
        panel_gap = 12.0
        panel_width = (width - (margin * 2) - panel_gap) / 2
        left_height = cast(
            float,
            build_detail_panel_layout(left_rows, panel_width=panel_width)["panel_height"],
        )
        right_height = cast(
            float,
            build_detail_panel_layout(right_rows, panel_width=panel_width)["panel_height"],
        )
        row_height = max(left_height, right_height)
        ensure_space(row_height + 10)
        draw_detail_panel_box(
            title=left_title,
            rows=left_rows,
            x=margin,
            y_top=y,
            panel_width=panel_width,
            background=left_background,
        )
        draw_detail_panel_box(
            title=right_title,
            rows=right_rows,
            x=margin + panel_width + panel_gap,
            y_top=y,
            panel_width=panel_width,
            background=right_background,
        )
        y -= row_height + 14

    def build_story_panel_layout(
        blocks: list[tuple[str, str]],
        *,
        panel_width: float,
    ) -> dict[str, Any]:
        content_padding_x = 18.0
        header_top_padding = 22.0
        title_gap = 24.0
        block_gap = 16.0
        bottom_padding = 18.0
        text_width = panel_width - (content_padding_x * 2)
        block_specs: list[tuple[str, list[str], float]] = []
        for label, value in blocks:
            value_lines = split_lines(value, "Helvetica", 10.5, text_width)
            block_height = 18.0 + (len(value_lines) * 14.0) + 4.0
            block_specs.append((label, value_lines, block_height))
        panel_height = (
            header_top_padding
            + title_gap
            + sum(block_height for _, _, block_height in block_specs)
            + (max(len(block_specs) - 1, 0) * block_gap)
            + bottom_padding
        )
        return {
            "content_padding_x": content_padding_x,
            "header_top_padding": header_top_padding,
            "title_gap": title_gap,
            "block_gap": block_gap,
            "block_specs": block_specs,
            "panel_height": panel_height,
        }

    def draw_story_panel_box(
        *,
        title: str,
        blocks: list[tuple[str, str]],
        x: float,
        y_top: float,
        panel_width: float,
        background: Any,
    ) -> float:
        layout = build_story_panel_layout(blocks, panel_width=panel_width)
        content_padding_x = cast(float, layout["content_padding_x"])
        header_top_padding = cast(float, layout["header_top_padding"])
        title_gap = cast(float, layout["title_gap"])
        block_gap = cast(float, layout["block_gap"])
        block_specs = cast(list[tuple[str, list[str], float]], layout["block_specs"])
        panel_height = cast(float, layout["panel_height"])

        pdf.setFillColor(background)
        pdf.setStrokeColor(border)
        pdf.roundRect(x, y_top - panel_height, panel_width, panel_height, 18, fill=1, stroke=1)

        text_x = x + content_padding_x
        inner_y = y_top - header_top_padding
        pdf.setFillColor(text_primary)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(text_x, inner_y, title)
        inner_y -= title_gap

        for index, (label, value_lines, block_height) in enumerate(block_specs):
            pdf.setFillColor(text_secondary)
            pdf.setFont("Helvetica-Bold", 9.5)
            pdf.drawString(text_x, inner_y, label)
            pdf.setFillColor(text_primary)
            pdf.setFont("Helvetica", 10.5)
            line_y = inner_y - 18
            for line in value_lines:
                pdf.drawString(text_x, line_y, line)
                line_y -= 14
            inner_y -= block_height
            if index != len(block_specs) - 1:
                separator_y = inner_y - (block_gap / 2)
                pdf.setStrokeColor(border)
                pdf.line(text_x, separator_y, x + panel_width - content_padding_x, separator_y)
                inner_y -= block_gap

        return panel_height

    def draw_split_story_panels(
        *,
        left_title: str,
        left_blocks: list[tuple[str, str]],
        left_background: Any,
        right_title: str,
        right_blocks: list[tuple[str, str]],
        right_background: Any,
    ) -> None:
        nonlocal y
        panel_gap = 12.0
        panel_width = (width - (margin * 2) - panel_gap) / 2
        left_height = cast(
            float,
            build_story_panel_layout(left_blocks, panel_width=panel_width)["panel_height"],
        )
        right_height = cast(
            float,
            build_story_panel_layout(right_blocks, panel_width=panel_width)["panel_height"],
        )
        ensure_space(max(left_height, right_height) + 10)
        draw_story_panel_box(
            title=left_title,
            blocks=left_blocks,
            x=margin,
            y_top=y,
            panel_width=panel_width,
            background=left_background,
        )
        draw_story_panel_box(
            title=right_title,
            blocks=right_blocks,
            x=margin + panel_width + panel_gap,
            y_top=y,
            panel_width=panel_width,
            background=right_background,
        )
        y -= max(left_height, right_height) + 14

    set_document_meta()
    draw_page_frame(primary=True)

    company_ref = result.company or "Empresa não informada"
    contact_ref = result.name or "Contato não informado"
    process_ref = get_process_label(result.tipo_processo)
    material_ref = lead_magnet_title or "Diagnóstico da calculadora pública"
    context_summary = build_context_summary(result)
    executive_summary = build_executive_summary(result)
    next_step = build_next_step_recommendation(result)

    hero_title_lines = split_lines(
        "Diagnóstico de ROI da Automação",
        "Helvetica-Bold",
        19,
        width - (margin * 2) - 48,
    )
    subtitle_lines = split_lines(
        "Leitura estratégica do processo priorizado com base nas respostas enviadas à calculadora pública da Composto Web.",
        "Helvetica",
        9.6,
        width - (margin * 2) - 48,
    )
    meta_entries = [
        ("Empresa", company_ref),
        ("Contato", contact_ref),
        ("Processo", process_ref),
        ("Material", material_ref),
    ]
    meta_label_width = 54.0
    meta_font_size = 8.8
    meta_line_height = 10.0
    meta_value_width = width - (margin * 2) - 54 - 32 - meta_label_width
    meta_specs: list[tuple[str, list[str], float]] = []
    for label, value in meta_entries:
        wrapped = split_lines(value, "Helvetica", meta_font_size, meta_value_width)
        row_height = max(12.0, len(wrapped) * meta_line_height)
        meta_specs.append((label, wrapped, row_height))
    meta_strip_height = (
        18.0
        + sum(row_height for _, _, row_height in meta_specs)
        + (max(len(meta_specs) - 1, 0) * 6.0)
    )
    hero_height = max(
        128.0,
        42.0
        + (len(hero_title_lines) * 19.0)
        + (len(subtitle_lines) * 12.0)
        + 12.0
        + meta_strip_height,
    )
    ensure_space(hero_height + 12)
    pdf.setFillColor(brand_soft)
    pdf.setStrokeColor(border)
    pdf.roundRect(margin, y - hero_height, width - (margin * 2), hero_height, 24, fill=1, stroke=1)
    pdf.setFillColor(accent)
    pdf.roundRect(margin + 18, y - hero_height + 18, 7, hero_height - 36, 3.5, fill=1, stroke=0)
    title_y = y - 34
    pdf.setFillColor(text_primary)
    pdf.setFont("Helvetica-Bold", 19)
    for line in hero_title_lines:
        pdf.drawString(margin + 36, title_y, line)
        title_y -= 19
    subtitle_y = title_y - 4
    pdf.setFillColor(text_secondary)
    pdf.setFont("Helvetica", 9.6)
    for line in subtitle_lines:
        pdf.drawString(margin + 36, subtitle_y, line)
        subtitle_y -= 12
    meta_strip_x = margin + 36
    meta_strip_y = y - hero_height + 14
    meta_strip_width = width - (margin * 2) - 54
    pdf.setFillColor(white)
    pdf.roundRect(
        meta_strip_x, meta_strip_y, meta_strip_width, meta_strip_height, 14, fill=1, stroke=0
    )
    pdf.setStrokeColor(border)
    pdf.roundRect(
        meta_strip_x, meta_strip_y, meta_strip_width, meta_strip_height, 14, fill=0, stroke=1
    )
    pdf.setFillColor(text_primary)
    meta_y = meta_strip_y + meta_strip_height - 14
    for label, value_lines, row_height in meta_specs:
        pdf.setFont("Helvetica-Bold", 8.4)
        pdf.drawString(meta_strip_x + 16, meta_y, f"{label}:")
        pdf.setFont("Helvetica", meta_font_size)
        value_y = meta_y
        for line in value_lines:
            pdf.drawString(meta_strip_x + 16 + meta_label_width, value_y, line)
            value_y -= meta_line_height
        meta_y -= row_height + 6
    y -= hero_height + 16

    draw_highlight_box("Leitura executiva", executive_summary)

    draw_section_heading("Indicadores principais")
    draw_metric_cards(
        [
            ("Custo anual estimado", format_brl(result.custo_anual)),
            (
                "Faixa de investimento",
                f"{format_brl(result.investimento_estimado_min)} a {format_brl(result.investimento_estimado_max)}",
            ),
            ("ROI estimado", format_percent(result.roi_estimado)),
            ("Payback estimado", format_months(result.payback_meses)),
        ]
    )

    draw_split_story_panels(
        left_title="Contexto considerado",
        left_blocks=[
            ("Cenário", context_summary),
            ("Tipo de processo", process_ref),
            ("Material relacionado", material_ref),
        ],
        left_background=brand_soft,
        right_title="Próximo passo recomendado",
        right_blocks=[
            ("Recomendação", next_step),
            (
                "Como avançar",
                "Se fizer sentido, responda este e-mail com o processo prioritário para aprofundarmos o recorte técnico e comercial.",
            ),
        ],
        right_background=white,
    )

    draw_detail_panel(
        "Parâmetros usados",
        [
            ("Cargo predominante", get_role_label(result.cargo)),
            ("Pessoas envolvidas", str(int(result.pessoas))),
            ("Horas por semana", _format_number(result.horas_semana, decimals=1)),
            ("Retrabalho estimado", format_percent(result.retrabalho_pct)),
            ("Segmento", get_segment_label(result.company_segment)),
            ("Porte", get_company_size_label(result.company_size)),
            ("Áreas no fluxo", get_process_area_label(result.process_area_span)),
        ],
        background=white,
    )

    pdf.save()
    return build_diagnosis_filename(result), buffer.getvalue()
