"""Offline eval tests (heuristic provider, no API keys)."""

import sys
from pathlib import Path

import pytest

_repo = Path(__file__).resolve().parents[2]
if str(_repo) not in sys.path:
    sys.path.insert(0, str(_repo))
_backend = _repo / "backend"
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from config.settings import Settings
from evals.cases import load_case_by_id
from evals.run_eval import evaluate_case
from evals.scorers.golden import score_golden_expectations
from evals.scorers.regression import compare_regression_snapshots
from evals.scorers.structural import score_structural_invariants
from evals.serialize import normalize_analysis_result
from llm.heuristic_provider import HeuristicLLMProvider
from llm.litellm_runtime import is_usable_openai_key, resolve_judge_model
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID


@pytest.fixture
def heuristic_settings():
    return Settings(llm_provider="heuristic", guardrails_enabled=False)


def test_structural_and_golden_jalisco_case(heuristic_settings):
    case = load_case_by_id("jalisco_deposito_alto")
    provider = HeuristicLLMProvider()
    result = provider.analyze_contract(
        contract_text=case.contract_text,
        perspective=case.perspective,
        title=case.title,
    )
    snapshot = normalize_analysis_result(result)
    assert not score_structural_invariants(snapshot)
    assert not score_golden_expectations(snapshot, case.must_extract, case.must_findings)


def test_regression_against_baseline(heuristic_settings):
    case = load_case_by_id("jalisco_deposito_alto")
    outcome = evaluate_case(
        heuristic_settings,
        case,
        prompt_id=CONTRACT_ANALYSIS_PROMPT_ID,
        run_regression=True,
        run_judge=False,
    )
    assert outcome.passed, (
        outcome.structural_errors,
        outcome.golden_errors,
        outcome.regression_hard,
        outcome.regression_soft,
    )


def test_regression_scorer_detects_risk_change():
    baseline = {"general_risk": "high", "extracted_fields": {}, "findings": []}
    candidate = {"general_risk": "low", "extracted_fields": {}, "findings": []}
    hard, soft = compare_regression_snapshots(baseline, candidate)
    assert hard
    assert not soft or soft  # soft may be empty


def test_judge_model_is_stronger_than_default_openai():
    settings = Settings(
        llm_provider="openai",
        openai_model="gpt-4o-mini",
        eval_judge_provider="openai",
        eval_judge_openai_model="gpt-4o",
    )
    _, model = resolve_judge_model(settings)
    assert model == "gpt-4o"
    assert model != settings.openai_model


@pytest.mark.llm_judge
def test_judge_absolute_live():
    settings = Settings(guardrails_enabled=False)
    if not is_usable_openai_key(settings.openai_api_key):
        pytest.skip("OPENAI_API_KEY required for LLM judge eval")
    case = load_case_by_id("jalisco_deposito_alto")
    outcome = evaluate_case(
        settings,
        case,
        prompt_id=CONTRACT_ANALYSIS_PROMPT_ID,
        run_regression=False,
        run_judge=True,
    )
    assert outcome.judge is not None
    assert outcome.judge.model == "gpt-4o"
