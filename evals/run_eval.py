"""Orchestrate regression and judge for one or all cases."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import Settings, get_settings
from evals.cases import AnalysisEvalCase, load_all_cases, load_case_by_id
from evals.judge import JudgeVerdict, run_judge_absolute, run_judge_comparative
from evals.paths import baseline_dir
from evals.provider import get_eval_llm_provider
from evals.scorers.golden import score_golden_expectations
from evals.scorers.regression import compare_regression_snapshots
from evals.scorers.structural import score_structural_invariants
from evals.serialize import normalize_analysis_result
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID


@dataclass
class CaseEvalResult:
    case_id: str
    passed: bool
    structural_errors: list[str] = field(default_factory=list)
    golden_errors: list[str] = field(default_factory=list)
    regression_hard: list[str] = field(default_factory=list)
    regression_soft: list[str] = field(default_factory=list)
    judge: JudgeVerdict | None = None
    snapshot: dict[str, Any] | None = None


@dataclass
class EvalReport:
    prompt_id: str
    provider: str
    model: str
    started_at: str
    cases: list[CaseEvalResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(item.passed for item in self.cases)


def _run_analysis(settings: Settings, case: AnalysisEvalCase):
    provider = get_eval_llm_provider(settings)
    return provider.analyze_contract(
        contract_text=case.contract_text,
        perspective=case.perspective,
        title=case.title,
    )


def _load_baseline_snapshot(prompt_id: str, case_id: str) -> dict[str, Any] | None:
    path = baseline_dir(prompt_id) / f"{case_id}.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_case(
    settings: Settings,
    case: AnalysisEvalCase,
    *,
    prompt_id: str,
    run_regression: bool,
    run_judge: bool,
    candidate_snapshot: dict[str, Any] | None = None,
) -> CaseEvalResult:
    if candidate_snapshot is None:
        result = _run_analysis(settings, case)
        candidate_snapshot = normalize_analysis_result(result)
        model = result.model or ""
    else:
        model = str(candidate_snapshot.get("model") or "")

    structural = score_structural_invariants(candidate_snapshot)
    golden = score_golden_expectations(
        candidate_snapshot,
        case.must_extract,
        case.must_findings,
    )
    regression_hard: list[str] = []
    regression_soft: list[str] = []
    baseline_snapshot: dict[str, Any] | None = None

    if run_regression:
        baseline_snapshot = _load_baseline_snapshot(prompt_id, case.id)
        if baseline_snapshot is None:
            regression_hard.append(f"missing baseline: {prompt_id}/{case.id}.json")
        else:
            regression_hard, regression_soft = compare_regression_snapshots(
                baseline_snapshot, candidate_snapshot
            )

    judge_verdict: JudgeVerdict | None = None
    should_judge = run_judge or case.judge_required
    if should_judge:
        if case.judge_mode == "comparative" and baseline_snapshot is None:
            baseline_snapshot = _load_baseline_snapshot(prompt_id, case.id)
        if case.judge_mode == "comparative" and baseline_snapshot is not None:
            judge_verdict = run_judge_comparative(
                settings,
                contract_text=case.contract_text,
                perspective=case.perspective,
                baseline_snapshot=baseline_snapshot,
                candidate_snapshot=candidate_snapshot,
            )
        else:
            judge_verdict = run_judge_absolute(
                settings,
                contract_text=case.contract_text,
                perspective=case.perspective,
                candidate_snapshot=candidate_snapshot,
            )
        if not judge_verdict.pass_:
            golden.append("judge: verdict pass=false")

    passed = (
        not structural
        and not golden
        and not regression_hard
        and (judge_verdict is None or judge_verdict.pass_)
    )

    _ = model  # reserved for report enrichment
    return CaseEvalResult(
        case_id=case.id,
        passed=passed,
        structural_errors=structural,
        golden_errors=golden,
        regression_hard=regression_hard,
        regression_soft=regression_soft,
        judge=judge_verdict,
        snapshot=candidate_snapshot,
    )


def run_evaluation(
    *,
    settings: Settings | None = None,
    prompt_id: str | None = None,
    case_id: str | None = None,
    mode: str = "regression",
) -> EvalReport:
    settings = settings or get_settings()
    prompt_id = prompt_id or CONTRACT_ANALYSIS_PROMPT_ID
    cases = [load_case_by_id(case_id)] if case_id else load_all_cases()
    if not cases:
        raise RuntimeError("No eval cases found under evals/datasets/analysis/")

    run_regression = mode in {"regression", "all"}
    run_judge = mode in {"judge", "all"}

    provider = settings.llm_provider.strip().lower()

    report = EvalReport(
        prompt_id=prompt_id,
        provider=provider,
        model="",
        started_at=datetime.now(timezone.utc).isoformat(),
    )

    for case in cases:
        report.cases.append(
            evaluate_case(
                settings,
                case,
                prompt_id=prompt_id,
                run_regression=run_regression,
                run_judge=run_judge,
            )
        )

    if report.cases and report.cases[0].snapshot:
        report.model = str(report.cases[0].snapshot.get("model") or "")

    return report


def write_report(report: EvalReport, settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    out_dir = settings.eval_runs_path() / report.started_at.replace(":", "-")
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "prompt_id": report.prompt_id,
        "provider": report.provider,
        "model": report.model,
        "started_at": report.started_at,
        "passed": report.passed,
        "cases": [
            {
                "case_id": item.case_id,
                "passed": item.passed,
                "structural_errors": item.structural_errors,
                "golden_errors": item.golden_errors,
                "regression_hard": item.regression_hard,
                "regression_soft": item.regression_soft,
                "judge": None
                if item.judge is None
                else {
                    "pass": item.judge.pass_,
                    "scores": item.judge.scores,
                    "fail_reasons": item.judge.fail_reasons,
                    "evidence": item.judge.evidence,
                    "model": item.judge.model,
                },
            }
            for item in report.cases
        ],
    }
    path = out_dir / "report.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_baseline(
    settings: Settings,
    prompt_id: str,
    case_id: str | None = None,
) -> list[Path]:
    """Persist normalized snapshots as regression baselines (manual approval workflow)."""
    cases = [load_case_by_id(case_id)] if case_id else load_all_cases()
    target = baseline_dir(prompt_id)
    target.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for case in cases:
        result = _run_analysis(settings, case)
        snapshot = normalize_analysis_result(result)
        path = target / f"{case.id}.json"
        path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        written.append(path)
    manifest = {
        "prompt_id": prompt_id,
        "provider": settings.llm_provider,
        "case_ids": [case.id for case in cases],
    }
    manifest_path = target / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    written.append(manifest_path)
    return written
