"""Chat message scope: lease/contract topics only."""

from __future__ import annotations

import re

from guardrails.text_utils import normalize_text

_ON_TOPIC_PATTERNS = (
    r"\bcontrato\b",
    r"\barrend",
    r"\blease\b",
    r"\brental\b",
    r"\btenant\b",
    r"\blandlord\b",
    r"\bclausul",
    r"\bclause\b",
    r"\brenta\b",
    r"\brent\b",
    r"\bdeposit",
    r"\bdep[oó]sito\b",
    r"\bfiador\b",
    r"\bgarant",
    r"\binmueble\b",
    r"\bproperty\b",
    r"\briesgos?\b",
    r"\brisks?\b",
    r"\bhallazg",
    r"\bfinding\b",
    r"\banalis",
    r"\banalysis\b",
    r"\bresumen\b",
    r"\bsummary\b",
    r"\brecomend",
    r"\bobligaci",
    r"\bterminaci",
    r"\brenovaci",
    r"\brenewal\b",
    r"\bpenaliz",
    r"\bjurisdicci",
    r"\bmaintenance\b",
    r"\bmantenimiento\b",
    r"\bservicios\b",
    r"\banexo\b",
    r"\brevision\b",
    r"\bcompar",
    r"\bdiferencia\b",
    r"\bevidencia\b",
    r"\bexplica\b",
    r"\bexplain\b",
    r"\bque dice\b",
    r"\bwhat does\b",
    r"\bcuanto\b",
    r"\bhow much\b",
    r"\bplazo\b",
    r"\bduracion\b",
    r"\bpartes\b",
    r"\bparties\b",
)

_OFF_TOPIC_PATTERNS = (
    r"\bclima\b",
    r"\bweather\b",
    r"\breceta\b",
    r"\brecipe\b",
    r"\bcapital de\b",
    r"\bworld cup\b",
    r"\bmundial\b",
    r"\bbitcoin\b",
    r"\bcrypto\b",
    r"\bescribe(un)?\s+codigo\b",
    r"\bwrite\s+(me\s+)?a\s+(python|javascript|java)\b",
    r"\bhackear\b",
    r"\bmalware\b",
    r"\bporn\b",
    r"\bpoema\b",
    r"\bpoem\b",
)

_SHORT_FOLLOWUP = re.compile(
    r"^(s[ií]|no|ok|vale|thanks|thank you|gracias|why|how|more|mas|más|"
    r"continue|continua|continúa|detalle|detalles|amplify|expand|por que|por qué|"
    r"why\??|explain more|mas detalle|más detalle|"
    r"explicame|explícame|explain)[!.?\s]*(mas|más|more|detalle|detalles)?[!.?\s]*$",
    re.IGNORECASE,
)

_CONTEXTUAL_FOLLOWUP = re.compile(
    r"\b(esto|eso|esa|ese|aquello|this|that|it|there|ahi|all[ií])\b",
    re.IGNORECASE,
)


def is_on_topic_chat_message(
    message: str,
    history: list[dict[str, str]] | None = None,
) -> bool:
    normalized = normalize_text(message)
    if not normalized:
        return False

    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _OFF_TOPIC_PATTERNS):
        return False

    if any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _ON_TOPIC_PATTERNS):
        return True

    hist = history or []
    if hist and _SHORT_FOLLOWUP.match(normalized):
        return True
    if hist and len(normalized) <= 80 and _CONTEXTUAL_FOLLOWUP.search(normalized):
        return True

    return False
