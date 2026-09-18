"""Clause category keywords (RF-20, RNF-31)."""

from __future__ import annotations

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "object": ("objeto", "inmueble", "destino", "uso"),
    "rent": ("renta", "pago mensual", "contraprestacion"),
    "deposit": ("deposito", "garantia", "aval"),
    "term": ("vigencia", "duracion", "plazo", "termino"),
    "maintenance": ("mantenimiento", "reparaciones", "conservacion"),
    "services": ("servicios", "agua", "luz", "internet", "gas"),
    "sublease": ("subarrend", "cesion", "sublet"),
    "guarantees": ("garantia", "fiador", "obligado solidario"),
    "insurance": ("seguro", "poliza"),
    "renewal": ("renovacion", "prorroga"),
    "termination": ("terminacion", "rescision", "vencimiento"),
    "penalties": ("penalizacion", "pena convencional", "multa"),
    "liability": ("responsabilidad", "indemnizacion"),
    "jurisdiction": ("jurisdiccion", "jurisdic", "foro", "competencia", "tribunales"),
}

ALL_CATEGORIES: frozenset[str] = frozenset(CATEGORY_KEYWORDS.keys())

# RF-20: categorías contractuales detectables sobre texto nativo (PDF/DOCX, sin OCR).
RF20_RELEVANT_CATEGORIES: frozenset[str] = ALL_CATEGORIES

RF20_CATEGORY_LABELS_ES: dict[str, str] = {
    "object": "objeto",
    "rent": "renta",
    "deposit": "depósito",
    "term": "vigencia",
    "maintenance": "mantenimiento",
    "services": "servicios",
    "sublease": "subarrendamiento",
    "guarantees": "garantías",
    "insurance": "seguros",
    "renewal": "renovación",
    "termination": "terminación",
    "penalties": "penalizaciones",
    "liability": "responsabilidad",
    "jurisdiction": "jurisdicción",
}
