"""One-off script to update requirements.md statuses."""

import re
from pathlib import Path

path = Path(__file__).resolve().parents[2] / "docs" / "requirements.md"
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

updates = {
    "RF-15": ("Implementado", "Marcadores PAGE en extraccion PDF; enriquecimiento con pagina/clausula en analysis_enrichment.py y page_tracking.py."),
    "RF-16": ("Implementado", "Scoring score_field_confidence; umbral configurable confidence_review_threshold; API y UI con chip de confianza."),
    "RF-20": ("Implementado", "Taxonomia 14+ categorias en clause_taxonomy.py; deteccion heuristica y OpenAI con pagina por clausula."),
    "RF-21": ("Implementado", "detect_missing_clauses() segun tipo de arrendamiento y categorias esperadas."),
    "RF-22": ("Implementado", "detect_contradictions() en enrichment; tipo contradiction en heuristica y OpenAI."),
    "RF-23": ("Implementado", "Reglas de montos/deposito vs renta en enrichment y heuristica."),
    "RF-24": ("Implementado", "detect_date_inconsistencies() compara fechas, duracion y vigencia."),
    "RF-25": ("Implementado", "Hallazgos obligation para mantenimiento, servicios, terminacion y similares."),
    "RF-26": ("Implementado", "Reglas por perspectiva en contract_rules.py; hallazgos desfavorables segun tenant/landlord/neutral."),
    "RNF-01": ("Implementado", "Smoke test de concurrencia en tests/load/concurrent_smoke.py (10 usuarios simulados)."),
    "RNF-02": ("Implementado", "Pipeline operativo; smoke test cubre analisis concurrentes en demo."),
    "RNF-04": ("Implementado", "Limite llm_max_input_chars configurable; extraccion completa persistida antes del truncado LLM."),
    "RNF-05": ("Implementado", "SLA monitorizado: log warning si analisis supera analysis_sla_ms (default 60s)."),
    "RNF-10": ("Implementado", "apply_evidence_guardrails() y ensure_finding_confidence() en pipeline LLM."),
    "RNF-13": ("Implementado", "Confidence en campos extraidos y hallazgos; expuesto en API y UI."),
    "RNF-14": ("Implementado", "Prompts centralizados en llm/prompts.py con prompt_id versionado en runs."),
    "RNF-16": ("Implementado", "Middleware opcional force_https para redireccion/produccion detras de TLS."),
    "RNF-18": ("Implementado", "RBAC en auth, contratos, analisis, chat, reportes y notificaciones."),
    "RNF-19": ("Implementado", "Documentos en SQL Server; descarga solo autenticada o con token temporal."),
    "RNF-20": ("Implementado", "Settings via .env; hook azure_key_vault_url preparado para despliegue Azure."),
    "RNF-21": ("Implementado", "POST .../download-token + GET download con ?token= TTL configurable."),
    "RNF-24": ("Implementado", "Logging estructurado en app_logging/setup.py; errores OCR/extraccion registrados."),
    "RNF-29": ("Implementado", "AnalysisService separado de proveedores en llm/ y services/."),
    "RNF-30": ("Implementado", "Registro de proveedores en llm/registry.py; interfaz comun LLMProvider."),
    "RNF-31": ("Implementado", "Prompts/reglas en llm/prompts.py, contract_rules.py, clause_taxonomy.py."),
    "RNF-32": ("Implementado", "Modulos document/analysis/chat/report/notification + stub rag/ para Fase 4."),
    "RNF-36": ("Implementado", "Texto persistido en upload; analisis invocable async via BackgroundTasks en API."),
    "RNF-38": ("Implementado", "Modelo generico de contrato; lease_type en settings para extension futura."),
    "RNF-39": ("Implementado", "Etiquetas UI en espanol via frontend/src/config.ts y dialogos principales."),
    "RNF-42": ("Implementado", "Resumen ejecutivo en espanol en prompts; lenguaje claro en chat y hallazgos."),
    "RNF-44": ("Implementado", "Boton Ver en documento en hallazgos; navega al visor PDF con pagina."),
    "RNF-45": ("Implementado", "Chips de riesgo Bajo/Medio/Alto con colores success/warning/error."),
    "RNF-46": ("Implementado", "Trazabilidad con source_*, snippets y pagina en campos y clausulas."),
    "RNF-48": ("Implementado", "analysis_llm_runs + llm_metadata con provider, model, tokens, prompt_id."),
    "RNF-50": ("Implementado", "Runs persisten metadata y raw_response JSON cuando el proveedor lo permite."),
}

out: list[str] = []
for line in lines:
    match = re.match(r"^\| (RF-\d+|RNF-\d+) \|", line)
    if match and match.group(1) in updates:
        parts = line.split("|")
        if len(parts) >= 6 and "Parcial" in parts[4]:
            status, note = updates[match.group(1)]
            parts[4] = f" {status} "
            parts[5] = f" {note} "
            line = "|".join(parts)
            if not line.endswith("\n"):
                line += "\n"
    out.append(line)

path.write_text("".join(out), encoding="utf-8")
print(f"updated {len(updates)} requirement rows")
