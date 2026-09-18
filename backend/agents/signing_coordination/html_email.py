"""HTML email body for signing coordination."""

from __future__ import annotations

import html
from typing import Any

SIGNING_PROCESS_MESSAGE = (
    "Su expediente fue cerrado en la plataforma. Revise la comparación entre el contrato "
    "original y la versión editada aprobada. Después, use el enlace seguro para elegir fecha "
    "y hora de la firma presencial con su abogado (y coordinación con el arrendador). "
    "La reserva en línea es orientativa; su abogado confirmará la cita."
)


def build_comparison_table_html(comparison: dict[str, Any]) -> str:
    rows = comparison.get("rows") or []
    if not rows:
        changes = comparison.get("changes") or []
        if changes:
            header = (
                "<tr><th>Tipo</th><th>Categoría</th><th>Valor anterior</th>"
                "<th>Valor nuevo</th><th>Descripción</th></tr>"
            )
            body_rows = []
            for change in changes:
                body_rows.append(
                    "<tr>"
                    f"<td>{html.escape(str(change.get('change_type') or ''))}</td>"
                    f"<td>{html.escape(str(change.get('category') or ''))}</td>"
                    f"<td>{html.escape(str(change.get('old_value') or ''))}</td>"
                    f"<td>{html.escape(str(change.get('new_value') or ''))}</td>"
                    f"<td>{html.escape(str(change.get('description') or ''))}</td>"
                    "</tr>"
                )
            return (
                "<table border=\"1\" cellpadding=\"6\" cellspacing=\"0\" "
                "style=\"border-collapse:collapse;width:100%\">"
                f"{header}{''.join(body_rows)}</table>"
            )
        return "<p><em>No hay filas de comparación registradas.</em></p>"

    header = (
        "<tr><th>Elemento</th><th>Tipo</th><th>Original</th>"
        "<th>Editado</th><th>Diferencia</th></tr>"
    )
    body_rows = []
    for row in rows:
        body_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row.get('item_key') or ''))}</td>"
            f"<td>{html.escape(str(row.get('item_type') or ''))}</td>"
            f"<td>{html.escape(str(row.get('original_value') or ''))}</td>"
            f"<td>{html.escape(str(row.get('new_value') or ''))}</td>"
            f"<td>{html.escape(str(row.get('difference') or row.get('change_type') or ''))}</td>"
            "</tr>"
        )
    return (
        "<table border=\"1\" cellpadding=\"6\" cellspacing=\"0\" "
        "style=\"border-collapse:collapse;width:100%\">"
        f"{header}{''.join(body_rows)}</table>"
    )


def build_signing_coordination_html(
    *,
    contract_title: str | None,
    narrative_summary: str,
    comparison: dict[str, Any],
    schedule_url: str,
    closure_notes: str,
    process_message: str | None = None,
) -> str:
    title = html.escape(contract_title or "Contrato de arrendamiento")
    narrative = html.escape(narrative_summary).replace("\n", "<br/>")
    notes = html.escape(closure_notes).replace("\n", "<br/>")
    process_text = html.escape(process_message or SIGNING_PROCESS_MESSAGE)
    table = build_comparison_table_html(comparison)
    link = html.escape(schedule_url)

    return f"""<!DOCTYPE html>
<html lang="es">
<body style="font-family:Segoe UI,Arial,sans-serif;color:#111;line-height:1.5;max-width:720px">
  <h2>Coordinación de firma — {title}</h2>
  <p>{narrative}</p>
  <h3>Próximos pasos</h3>
  <p>{process_text}</p>
  <h3>Notas finales del abogado</h3>
  <p>{notes}</p>
  <h3>Comparación final (original vs versión editada)</h3>
  {table}
  <h3>Firma presencial</h3>
  <p>Seleccione fecha y hora en el enlace seguro (calendario de los próximos 30 días hábiles, 09:00–18:00 CDMX):</p>
  <p><a href="{link}" style="font-weight:600">Agendar firma presencial</a></p>
  <p style="word-break:break-all;font-size:13px;color:#444">{link}</p>
  <p style="color:#555;font-size:12px">Mensaje generado por Legal Rent AI. La firma formal se realiza fuera del sistema.</p>
</body>
</html>"""
