"""Automatic document type classification (RF-08)."""

from dataclasses import dataclass
import re
import unicodedata

from document.text_extractor import extract_text_preview

DOCUMENT_TYPE_MAIN = "main_contract"
DOCUMENT_TYPE_ANNEX = "annex"
DOCUMENT_TYPE_OTHER = "other"
DOCUMENT_TYPE_LAWYER_REVISION = "lawyer_revision"

ALLOWED_DOCUMENT_TYPES = {
    DOCUMENT_TYPE_MAIN,
    DOCUMENT_TYPE_ANNEX,
    DOCUMENT_TYPE_OTHER,
    DOCUMENT_TYPE_LAWYER_REVISION,
}

ANNEX_FILENAME_PATTERNS = (
    r"\banexo\b",
    r"\bannex\b",
    r"\baddendum\b",
    r"\bapendice\b",
    r"\bappendix\b",
    r"\bexhibit\b",
    r"\banex\b",
    r"\brider\b",
)

MAIN_FILENAME_PATTERNS = (
    r"\bcontrato\b",
    r"\blease\b",
    r"\barrendamiento\b",
    r"\blocacion\b",
    r"\blocation\b",
    r"\brental\b",
    r"\btenancy\b",
)

OTHER_FILENAME_PATTERNS = (
    r"\bidentificacion\b",
    r"\bidentification\b",
    r"\brecibo\b",
    r"\breceipt\b",
    r"\bcarta\b",
    r"\bletter\b",
    r"\bpoder\b",
    r"\bpower of attorney\b",
    r"\bcertificado\b",
    r"\bcertificate\b",
    r"\bfianza\b",
    r"\bgarantia\b",
    r"\binsurance\b",
    r"\bpoliza\b",
)

ANNEX_CONTENT_PATTERNS = (
    r"\banexo\s+(al|del)\s+contrato\b",
    r"\bannex\s+(to|of)\s+(the\s+)?(lease|contract|agreement)\b",
    r"\baddendum\s+(to|of)\b",
    r"\bapendice\s+(al|del)\s+contrato\b",
    r"\bappendix\s+(to|of)\b",
)

MAIN_CONTENT_PATTERNS = (
    r"\bcontrato de arrendamiento\b",
    r"\bcontrato de locacion\b",
    r"\blease agreement\b",
    r"\brental agreement\b",
    r"\btenancy agreement\b",
    r"\bcontrato de arrendamiento de inmueble\b",
)

OTHER_CONTENT_PATTERNS = (
    r"\bidentificacion oficial\b",
    r"\bcomprobante de domicilio\b",
    r"\bcarta poder\b",
    r"\brecibo de\b",
    r"\bpoliza de\b",
    r"\bcertificado de\b",
)


@dataclass(frozen=True)
class DocumentClassification:
    """Result of automatic document type detection."""

    document_type: str
    confidence: float
    source: str


def classify_document(
    file_name: str,
    content: bytes,
    mime_type: str,
    is_first_document: bool,
) -> DocumentClassification:
    """Identify whether a file is a main contract, annex, or other document."""
    normalized_name = _normalize_filename(file_name)
    text_preview = extract_text_preview(content, mime_type)
    normalized_content = _normalize_text(text_preview)

    scores = {
        DOCUMENT_TYPE_MAIN: 0.0,
        DOCUMENT_TYPE_ANNEX: 0.0,
        DOCUMENT_TYPE_OTHER: 0.0,
    }
    sources: list[str] = []

    annex_filename_score = _pattern_score(normalized_name, ANNEX_FILENAME_PATTERNS, weight=0.65)
    main_filename_score = _pattern_score(normalized_name, MAIN_FILENAME_PATTERNS, weight=0.55)
    other_filename_score = _pattern_score(normalized_name, OTHER_FILENAME_PATTERNS, weight=0.60)

    if annex_filename_score:
        scores[DOCUMENT_TYPE_ANNEX] += annex_filename_score
        sources.append("filename")
    if main_filename_score:
        scores[DOCUMENT_TYPE_MAIN] += main_filename_score
        sources.append("filename")
    if other_filename_score:
        scores[DOCUMENT_TYPE_OTHER] += other_filename_score
        sources.append("filename")

    if normalized_content:
        annex_content_score = _pattern_score(normalized_content, ANNEX_CONTENT_PATTERNS, weight=0.75)
        main_content_score = _pattern_score(normalized_content, MAIN_CONTENT_PATTERNS, weight=0.70)
        other_content_score = _pattern_score(normalized_content, OTHER_CONTENT_PATTERNS, weight=0.65)

        if annex_content_score:
            scores[DOCUMENT_TYPE_ANNEX] += annex_content_score
            sources.append("content")
        if main_content_score:
            scores[DOCUMENT_TYPE_MAIN] += main_content_score
            sources.append("content")
        if other_content_score:
            scores[DOCUMENT_TYPE_OTHER] += other_content_score
            sources.append("content")

    if is_first_document:
        scores[DOCUMENT_TYPE_MAIN] += 0.25
        sources.append("context")
    else:
        scores[DOCUMENT_TYPE_ANNEX] += 0.15
        sources.append("context")

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score < 0.25:
        best_type = DOCUMENT_TYPE_MAIN if is_first_document else DOCUMENT_TYPE_OTHER
        best_score = 0.45
        sources.append("default")

    confidence = min(round(best_score, 4), 0.99)
    source = "+".join(dict.fromkeys(sources))
    return DocumentClassification(
        document_type=best_type,
        confidence=confidence,
        source=source,
    )


def _normalize_filename(value: str) -> str:
    """Normalize a filename so token boundaries work with underscores and hyphens."""
    stem = value.rsplit(".", 1)[0] if "." in value else value
    spaced = re.sub(r"[_\-\.]+", " ", stem)
    return _normalize_text(spaced)


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", stripped).strip()


def _pattern_score(text: str, patterns: tuple[str, ...], weight: float) -> float:
    if not text:
        return 0.0

    matches = sum(1 for pattern in patterns if re.search(pattern, text))
    if matches == 0:
        return 0.0

    return min(weight * matches, 1.0)
