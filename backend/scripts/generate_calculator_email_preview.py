from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from core.branding import (
    COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_CID,
    COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH,
    COMPOSTO_WEB_SURFACE,
)
from models.content_calculator_result import ContentCalculatorResult
from services.content.calculator_report import build_calculator_diagnosis_pdf
from services.notification import build_calculator_diagnosis_email_payload


def main() -> None:
    output_dir = BACKEND_ROOT / "preview"
    output_dir.mkdir(parents=True, exist_ok=True)

    result = ContentCalculatorResult(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        pessoas=5,
        horas_semana=16,
        custo_hora=145,
        cargo="gerente",
        retrabalho_pct=18,
        tipo_processo="financeiro",
        company_segment="industria",
        company_size="media",
        process_area_span="2-3",
        custo_mensal=50228.00,
        custo_retrabalho=13561.56,
        custo_total_mensal=63789.56,
        custo_anual=765474.72,
        investimento_estimado_min=26160.00,
        investimento_estimado_max=65400.00,
        roi_estimado=1387.40,
        payback_meses=0.7,
        name="Adriano Teste",
        email="adriano@compostoweb.com.br",
        company="Composto Web",
        role="Diretor Comercial",
        phone="(11) 99999-0000",
    )

    filename, pdf_bytes = build_calculator_diagnosis_pdf(
        result,
        lead_magnet_title="Diagnóstico de Processos Financeiros",
    )
    payload = build_calculator_diagnosis_email_payload(
        result=result,
        lead_magnet_title="Diagnóstico de Processos Financeiros",
        filename=filename,
        pdf_bytes=pdf_bytes,
    )
    preview_logo_name = COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH.name
    preview_logo_path = output_dir / preview_logo_name
    preview_logo_src = f"cid:{COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_CID}"
    if COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH.exists():
        preview_logo_path.write_bytes(COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_PATH.read_bytes())
        preview_logo_src = preview_logo_name
    preview_html = payload["html"].replace(
        f"cid:{COMPOSTO_WEB_LOGO_PRIMARY_TRANSPARENT_CID}",
        preview_logo_src,
    )
    html_document = f"""<!DOCTYPE html>
<html lang=\"pt-BR\">
    <head>
        <meta charset=\"utf-8\" />
        <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
        <title>{payload["subject"]}</title>
    </head>
    <body style=\"margin:0;padding:32px;background:{COMPOSTO_WEB_SURFACE};\">
        {preview_html}
    </body>
</html>
"""

    pdf_path = output_dir / filename
    html_path = output_dir / "calculator_diagnosis_email_preview.html"
    metadata_path = output_dir / "calculator_diagnosis_email_preview.json"

    pdf_path.write_bytes(pdf_bytes)
    html_path.write_text(html_document, encoding="utf-8")
    metadata_path.write_text(
        json.dumps(
            {
                "recipient_email": payload["recipient_email"],
                "subject": payload["subject"],
                "reply_to": payload["reply_to"],
                "pdf_path": str(pdf_path),
                "html_path": str(html_path),
                "logo_path": str(preview_logo_path) if preview_logo_path.exists() else None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "pdf": str(pdf_path),
                "html": str(html_path),
                "metadata": str(metadata_path),
                "subject": payload["subject"],
                "recipient": payload["recipient_email"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
