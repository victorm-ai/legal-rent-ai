"""Field extraction patterns for lease contracts (RF-14)."""

from __future__ import annotations

RF14_FIELD_NAMES: tuple[str, ...] = (
    "arrendador",
    "arrendatario",
    "fiador",
    "obligado_solidario",
    "representante_arrendador",
    "representante_arrendatario",
    "inmueble_direccion",
    "inmueble_uso",
    "renta_mensual",
    "deposito",
    "garantia",
    "forma_pago",
    "impuestos",
    "incremento_renta",
    "penalizacion",
    "mantenimiento",
    "servicios",
    "renovacion",
    "terminacion",
    "fecha_inicio",
    "fecha_fin",
    "duracion_meses",
    "jurisdiccion",
)

CLAUSE_CATEGORY_FIELD_MAP: dict[str, str] = {
    "maintenance": "mantenimiento",
    "services": "servicios",
    "renewal": "renovacion",
    "termination": "terminacion",
    "guarantees": "garantia",
    "penalties": "penalizacion",
    "rent": "renta_mensual",
    "deposit": "deposito",
    "term": "duracion_meses",
    "jurisdiction": "jurisdiccion",
    "object": "inmueble_uso",
}

FIELD_SPECS: dict[str, list[str]] = {
    "arrendador": [
        r"(?:ARRENDADOR(?:A)?|EL ARRENDADOR)[:\s\-]+([^\n\r]{3,120})",
        r"arrendador(?:a)?(?:\s+es)?[:\s]+([^\n\r]{3,120})",
    ],
    "arrendatario": [
        r"(?:ARRENDATARIO(?:A)?|EL ARRENDATARIO)[:\s\-]+([^\n\r]{3,120})",
        r"arrendatario(?:a)?(?:\s+es)?[:\s]+([^\n\r]{3,120})",
    ],
    "fiador": [
        r"(?:FIADOR(?:A)?|EL FIADOR)[:\s\-]+([^\n\r]{3,120})",
        r"fiador(?:a)?(?:\s+es)?[:\s]+([^\n\r]{3,120})",
    ],
    "obligado_solidario": [
        r"(?:OBLIGADO SOLIDARIO|OBLIGADA SOLIDARIA)[:\s\-]+([^\n\r]{3,120})",
        r"((?:obligad[oa]\s+solidari[oa])[^\n\r]{3,120})",
    ],
    "representante_arrendador": [
        r"representante\s+(?:legal\s+)?(?:del\s+)?arrendador[:\s\-]+([^\n\r]{3,120})",
    ],
    "representante_arrendatario": [
        r"representante\s+(?:legal\s+)?(?:del\s+)?arrendatario[:\s\-]+([^\n\r]{3,120})",
    ],
    "inmueble_direccion": [
        r"(?:INMUEBLE|PROPIEDAD|DOMICILIO DEL INMUEBLE)[:\s\-]+([^\n\r]{5,200})",
        r"ubicad[oa]\s+en[:\s]+([^\n\r]{5,200})",
    ],
    "inmueble_uso": [
        r"(?:USO|DESTINO)\s+(?:DEL INMUEBLE|PERMITIDO)[:\s\-]+([^\n\r]{3,120})",
        r"((?:uso\s+(?:del inmueble|habitacional|comercial|oficinas?))[^\n\r]{0,80})",
    ],
    "renta_mensual": [
        r"renta\s+mensual[^$\d\n]{0,40}(\$?\s*\d[\d,.]*(?:\.\d{2})?)",
        r"(\$?\s*\d[\d,.]*(?:\.\d{2})?)\s*(?:MXN|pesos)[^\n]{0,30}mensual",
    ],
    "deposito": [
        r"dep[oó]sito(?:\s+en\s+garant[ií]a)?(?:\s+de)?[^$\d\n]{0,40}(\$?\s*\d[\d,.]*(?:\.\d{2})?)",
    ],
    "garantia": [
        r"((?:garant[ií]a(?:\s+adicional)?)[^$\d\n]{0,40}(?:\$?\s*\d[\d,.]*(?:\.\d{2})?|[^\n\r]{5,120}))",
    ],
    "forma_pago": [
        r"forma\s+de\s+pago[:\s\-]+([^\n\r]{5,120})",
        r"((?:transferencia|dep[oó]sito bancario|cheque|efectivo)[^\n\r]{0,80})",
    ],
    "impuestos": [
        r"((?:impuestos?|IVA|ISR)[^.\n]{0,40}(?:a\s+cargo\s+de|pagar[aá]|corresponde)[^\n\r]{0,80})",
        r"((?:IVA|ISR|impuesto)[^\n\r]{5,120})",
    ],
    "incremento_renta": [
        r"((?:incremento(?:\s+anual)?)[^.\n]{0,40}(?:\d+\s*%|INPC|[ií]ndice)[^\n\r]{0,40})",
    ],
    "penalizacion": [
        r"((?:pena\s+convencional|penalizaci[oó]n)[^$\d\n]{0,40}(?:\$?\s*\d[\d,.]*(?:\.\d{2})?|\d+\s*meses)[^\n\r]{0,40})",
    ],
    "mantenimiento": [
        r"(mantenimiento[^.\n]{0,60}(?:a\s+cargo\s+de|obligaci[oó]n)[^\n\r]{0,120})",
        r"((?:reparaciones|conservaci[oó]n)[^.\n]{0,80}(?:a\s+cargo\s+de|arrendat)[^\n\r]{0,80})",
    ],
    "servicios": [
        r"((?:servicios\s+(?:de\s+)?(?:agua|luz|gas|internet)|agua|luz|gas)[^\n\r]{0,120})",
    ],
    "renovacion": [
        r"((?:renovaci[oó]n(?:\s+autom[aá]tica)?)[^.\n]{0,120})",
    ],
    "terminacion": [
        r"((?:terminaci[oó]n(?:\s+anticipada)?)[^.\n]{0,120})",
    ],
    "fecha_inicio": [
        r"fecha\s+de\s+inicio[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"inicia(?:r[aá]|ndo)?\s+el\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ],
    "fecha_fin": [
        r"fecha\s+de\s+(?:t[eé]rmino|fin|vencimiento)[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
    ],
    "duracion_meses": [
        r"vigencia\s+de\s+(\d+)\s+meses",
        r"plazo\s+de\s+(\d+)\s+meses",
    ],
    "jurisdiccion": [
        r"(?:Estado de|Ciudad de)\s+([A-Za-zÁÉÍÓÚáéíóúñ\s]+?)(?:\.|\n|$)",
        r"tribunales del Estado de\s+([A-Za-zÁÉÍÓÚáéíóúñ\s]+?)(?:\.|\n|$)",
        r"foro\s+(?:de|en)\s+(?:los tribunales del )?(?:Estado de\s+)?([A-Za-zÁÉÍÓÚáéíóúñ\s]+?)(?:\.|\n|$)",
    ],
}

PARTY_FIELD_MAP: dict[str, str] = {
    "arrendador": "landlord",
    "arrendatario": "tenant",
    "fiador": "guarantor",
    "obligado_solidario": "joint_obligor",
    "representante_arrendador": "landlord_representative",
    "representante_arrendatario": "tenant_representative",
}
