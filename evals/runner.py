"""CLI entrypoint for offline LLM evaluation."""

from __future__ import annotations

import argparse
import sys

from config.settings import Settings, get_settings
from evals.run_eval import run_evaluation, write_baseline, write_report
from llm.prompts import CONTRACT_ANALYSIS_PROMPT_ID


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run LLM evals (regression and/or LLM-as-judge) outside production traffic.",
    )
    parser.add_argument(
        "--mode",
        choices=("regression", "judge", "all"),
        default="regression",
        help="regression=deterministic+baseline; judge=LLM judge; all=both",
    )
    parser.add_argument(
        "--baseline",
        default=CONTRACT_ANALYSIS_PROMPT_ID,
        help="Baseline folder name under evals/baselines/",
    )
    parser.add_argument("--case", dest="case_id", default=None, help="Single case id (filename stem)")
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Write evals/baselines/<prompt_id>/*.json from current provider (no judge)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="Override LLM_PROVIDER for this eval run (e.g. heuristic, openai)",
    )
    args = parser.parse_args(argv)
    get_settings.cache_clear()
    settings = Settings()
    if args.provider:
        settings = settings.model_copy(update={"llm_provider": args.provider.strip().lower()})

    if args.write_baseline:
        paths = write_baseline(settings, args.baseline, args.case_id)
        for path in paths:
            print(f"Wrote {path}")
        return 0

    report = run_evaluation(
        settings=settings,
        prompt_id=args.baseline,
        case_id=args.case_id,
        mode=args.mode,
    )
    out = write_report(report, settings)
    print(f"Report: {out}")
    print(f"Overall pass: {report.passed}")
    for case in report.cases:
        status = "PASS" if case.passed else "FAIL"
        print(f"  [{status}] {case.case_id}")
        for bucket, label in (
            (case.structural_errors, "structural"),
            (case.golden_errors, "golden"),
            (case.regression_hard, "regression"),
        ):
            for msg in bucket:
                print(f"    {label}: {msg}")
        for msg in case.regression_soft:
            print(f"    regression (soft): {msg}")
        if case.judge is not None:
            print(
                f"    judge ({case.judge.model}): pass={case.judge.pass_} scores={case.judge.scores}"
            )
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
