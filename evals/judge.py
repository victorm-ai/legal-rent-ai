"""LLM-as-judge for analysis eval (uses stronger model via judge_completion)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from config.settings import Settings
from llm.litellm_runtime import judge_completion, resolve_judge_model

logger = logging.getLogger(__name__)

JUDGE_SYSTEM = """You are an expert evaluator for Mexican lease contract analysis outputs.
Score the candidate JSON against the contract text and perspective using the rubric.
Be strict about groundedness: penalize invented parties, amounts, or legal citations not supported by the contract.
Respond ONLY with valid JSON:
{
  "pass": true or false,
  "scores": {
    "groundedness": 1-5,
    "finding_quality": 1-5,
    "summary_clarity": 1-5
  },
  "fail_reasons": ["string"],
  "evidence": ["short quotes or field names supporting your verdict"]
}
pass is true only if groundedness >= 4 and finding_quality >= 3 and summary_clarity >= 3 and no critical hallucination."""

COMPARATIVE_USER_TEMPLATE = """Mode: comparative regression review.

Contract text:
{contract_text}

Analysis perspective: {perspective}

Baseline analysis JSON (reference):
{baseline_json}

Candidate analysis JSON (new):
{candidate_json}

Question: Is the candidate equal or better than the baseline on groundedness and finding_quality,
without a worse summary_clarity? If the candidate fixes errors, pass. If it regresses, fail."""

ABSOLUTE_USER_TEMPLATE = """Mode: absolute quality review.

Contract text:
{contract_text}

Analysis perspective: {perspective}

Candidate analysis JSON:
{candidate_json}

Evaluate whether this output is acceptable for production use from the selected perspective."""


@dataclass
class JudgeVerdict:
    pass_: bool
    scores: dict[str, int]
    fail_reasons: list[str]
    evidence: list[str]
    model: str
    raw: dict[str, Any]


def _parse_verdict(content: str, model: str) -> JudgeVerdict:
    payload = json.loads(content or "{}")
    scores_raw = payload.get("scores") or {}
    scores = {
        "groundedness": int(scores_raw.get("groundedness", 0)),
        "finding_quality": int(scores_raw.get("finding_quality", 0)),
        "summary_clarity": int(scores_raw.get("summary_clarity", 0)),
    }
    return JudgeVerdict(
        pass_=bool(payload.get("pass", False)),
        scores=scores,
        fail_reasons=[str(item) for item in payload.get("fail_reasons") or []],
        evidence=[str(item) for item in payload.get("evidence") or []],
        model=model,
        raw=payload,
    )


def run_judge_absolute(
    settings: Settings,
    *,
    contract_text: str,
    perspective: str,
    candidate_snapshot: dict[str, Any],
) -> JudgeVerdict:
    _, model_id = resolve_judge_model(settings)
    user = ABSOLUTE_USER_TEMPLATE.format(
        contract_text=contract_text[:80000],
        perspective=perspective,
        candidate_json=json.dumps(candidate_snapshot, ensure_ascii=False, indent=2),
    )
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user},
    ]
    content, _, model = judge_completion(settings=settings, messages=messages, temperature=0.0)
    return _parse_verdict(content, model or model_id)


def run_judge_comparative(
    settings: Settings,
    *,
    contract_text: str,
    perspective: str,
    baseline_snapshot: dict[str, Any],
    candidate_snapshot: dict[str, Any],
) -> JudgeVerdict:
    _, model_id = resolve_judge_model(settings)
    user = COMPARATIVE_USER_TEMPLATE.format(
        contract_text=contract_text[:80000],
        perspective=perspective,
        baseline_json=json.dumps(baseline_snapshot, ensure_ascii=False, indent=2),
        candidate_json=json.dumps(candidate_snapshot, ensure_ascii=False, indent=2),
    )
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": user},
    ]
    content, _, model = judge_completion(settings=settings, messages=messages, temperature=0.0)
    return _parse_verdict(content, model or model_id)
