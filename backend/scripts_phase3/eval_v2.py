"""Phase 1: run the v2 golden evaluation against the real pipeline.

Usage (from the ``backend`` directory):

    python scripts_phase3/eval_v2.py --mode both

Environment it expects (all optional, with local defaults):

    EVAL_VAR_DIR      isolated data dir for the eval database/index (default backend/var/eval-v2)
    LLM_MODEL         generator model (default qwen2.5-coder:7b)
    LLM_BASE_URL      OpenAI-compatible endpoint (default the local Ollama server)

It writes ``data/evaluation/v2/baseline_<mode>_<model>.json`` for each mode and
prints the separate metric families plus the failure-taxonomy table.

The v2 questions are labelled in the repository, not generated here: this script
only *runs* them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
EVAL_DIR = PROJECT_ROOT / "data" / "evaluation" / "v2"

# ---------------------------------------------------------------- environment
EVAL_VAR_ROOT = Path(os.environ.get("EVAL_VAR_DIR", str(BACKEND_DIR / "var" / "eval-v2")))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(EVAL_VAR_ROOT / 'eval.db').as_posix()}")
os.environ.setdefault("VAR_DIR", (EVAL_VAR_ROOT / "var").as_posix())
os.environ.setdefault("LOCAL_STORAGE_DIR", (EVAL_VAR_ROOT / "storage").as_posix())
os.environ.setdefault("OCR_ENABLED", "false")
os.environ.setdefault("VLM_ENABLED", "false")
os.environ.setdefault("EMBEDDING_PROVIDER", "sentence_transformers")
os.environ.setdefault("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
os.environ.setdefault("RERANKER_ENABLED", "true")
os.environ.setdefault("RERANKER_PROVIDER", "cross_encoder")
os.environ.setdefault("ALLOW_PROVIDER_FALLBACK", "false")
os.environ.setdefault("LLM_PROVIDER", "openai_compatible")
os.environ.setdefault("LLM_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("LLM_API_KEY", "ollama")
os.environ.setdefault("LLM_MODEL", "qwen2.5-coder:7b")

sys.path.insert(0, str(BACKEND_DIR))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()


def _slug(value: str | None) -> str:
    return (value or "none").replace(":", "-").replace("/", "-").replace(" ", "")


async def _principal_from_db():
    from sqlalchemy import select

    from app.db.models import Tenant, User
    from app.db.session import session_scope
    from app.security.rbac import Principal

    async with session_scope() as session:
        tenant = (await session.execute(select(Tenant).limit(1))).scalar_one_or_none()
        if tenant is None:
            raise SystemExit("No tenant in the eval database. Run `python -m app.cli ingest ..\\data\\synthetic` first.")
        user = (
            await session.execute(select(User).where(User.tenant_id == tenant.id).limit(1))
        ).scalar_one_or_none()
    return Principal(
        user_id=user.id if user else "eval-runner",
        tenant_id=tenant.id,
        email=user.email if user else "eval@local",
        role=user.role if user else "admin",
    )


def _print_report(report: dict, *, title: str) -> None:
    run = report["run"]
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")
    print(f"mode={run['mode']}  model={run['llm_model']}  embedding={run['embedding_model']}")
    print(f"questions={report['dataset']['question_count']}  duration={run['duration_seconds']}s")
    print(f"generation modes: {run['generation_modes']}")

    def rate(block: dict | None) -> str:
        if not block:
            return "  n/a"
        return f"{block['rate']:.1%} [{block['low']:.1%}-{block['high']:.1%}] (n={block['total']})"

    r = report["retrieval"]
    print("\n-- retrieval (answerable questions with labelled sources) --")
    print(f"  questions          : {r['questions']}")
    print(f"  recall@5 / @10     : {r['recall_at_5']} / {r['recall_at_10']}")
    print(f"  MRR / nDCG@10      : {r['mrr']} / {r['ndcg_at_10']}")
    print(f"  page coverage      : {r['page_coverage']}")
    print(f"  hit rate @5        : {rate(r['hit_rate_at_5'])}")
    print(f"  hit rate @10       : {rate(r['hit_rate_at_10'])}")

    a = report["answer"]
    print("\n-- answer --")
    print(f"  questions          : {a['questions']}")
    print(f"  correctness        : {rate(a['correct'])}")
    print(f"  mean fact coverage : {a['mean_fact_coverage']}")

    f = report["refusal"]
    print("\n-- refusal (precision and recall reported separately) --")
    print(f"  precision          : {f['precision']}")
    print(f"  recall             : {f['recall']}")
    print(f"  confusion          : tp={f['tp']} fp={f['fp']} fn={f['fn']} tn={f['tn']}")
    print(f"  accuracy           : {rate(f['accuracy'])}")

    c = report["citation"]
    print("\n-- citation --")
    print(f"  questions          : {c['questions']}")
    print(f"  mean precision     : {c['mean_precision']}")
    print(f"  no unsupported     : {rate(c['no_unsupported_citations'])}")
    print(f"  verification pass  : {c['mean_validity']}")

    lat = report["latency_ms"]
    print("\n-- latency (ms, outliers kept) --")
    print(f"  p50={lat['p50']}  p95={lat['p95']}  max={lat['max']}  mean={lat['mean']}  n={lat['count']}")

    t = report["tokens"]
    print("\n-- tokens --")
    print(
        f"  prompt total={t['prompt_total']} (mean {t['prompt_mean']})  "
        f"completion total={t['completion_total']} (mean {t['completion_mean']})"
    )
    print(f"  cost: {t['cost_note']}")

    print("\n-- failure taxonomy --")
    print(f"  {'label':<24}{'count':>6}")
    for label, count in report["failure_taxonomy"].items():
        print(f"  {label:<24}{count:>6}")
    print(f"  {'TOTAL FAILURES':<24}{report['failures_total']:>6}")


def _taxonomy_markdown(reports: dict[str, dict]) -> str:
    lines = ["# Failure taxonomy (v2 baseline)", ""]
    lines.append(
        "Produced by `python scripts_phase3/eval_v2.py --mode both`. "
        "Every failed question carries exactly one label; the totals below are read straight "
        "from `data/evaluation/v2/baseline_*.json`."
    )
    lines.append("")
    lines.append("| failure label | current | oracle | meaning |")
    lines.append("| --- | ---: | ---: | --- |")
    meanings = {
        "retrieval_miss": "no labelled source reached the retrieved set",
        "wrong_context_selected": "a labelled source was retrieved but dropped before generation",
        "generation_error": "labelled evidence was present but the answer still missed the facts",
        "verification_miss": "wrong answer was reported as supported/verified",
        "refusal_failure": "answered something that should be refused, or refused something answerable",
        "error": "the question raised an exception",
    }
    for label in reports["current"]["failure_taxonomy"]:
        lines.append(
            f"| {label} | {reports['current']['failure_taxonomy'][label]} "
            f"| {reports['oracle']['failure_taxonomy'][label]} | {meanings[label]} |"
        )
    lines.append("")
    lines.append("| metric family | current | oracle |")
    lines.append("| --- | --- | --- |")

    def r(block):
        return "n/a" if not block else f"{block['rate']:.1%} ({block['low']:.1%}-{block['high']:.1%})"

    cur, ora = reports["current"], reports["oracle"]
    lines.append(
        f"| retrieval recall@10 | {cur['retrieval']['recall_at_10']} | {ora['retrieval']['recall_at_10']} |"
    )
    lines.append(f"| retrieval MRR | {cur['retrieval']['mrr']} | {ora['retrieval']['mrr']} |")
    lines.append(f"| answer correctness | {r(cur['answer']['correct'])} | {r(ora['answer']['correct'])} |")
    lines.append(f"| refusal precision | {cur['refusal']['precision']} | {ora['refusal']['precision']} |")
    lines.append(f"| refusal recall | {cur['refusal']['recall']} | {ora['refusal']['recall']} |")
    lines.append(f"| citation precision | {cur['citation']['mean_precision']} | {ora['citation']['mean_precision']} |")
    lines.append(f"| latency p50 (ms) | {cur['latency_ms']['p50']} | {ora['latency_ms']['p50']} |")
    lines.append(f"| latency p95 (ms) | {cur['latency_ms']['p95']} | {ora['latency_ms']['p95']} |")
    return "\n".join(lines) + "\n"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the v2 golden evaluation")
    parser.add_argument("--mode", choices=["current", "oracle", "both"], default="both")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--categories", nargs="*", default=None)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--strategy", default=None)
    parser.add_argument("--write-taxonomy", action="store_true")
    args = parser.parse_args()

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.evaluation.v2_runner import V2Runner

    settings = get_settings()
    print(f"DB        : {settings.database_url}")
    print(f"LLM       : {settings.llm_model} @ {settings.llm_base_url} (configured={settings.llm_configured})")
    print(f"Embedding : {settings.embedding_model}")
    print(f"Reranker  : {settings.reranker_enabled} ({settings.reranker_provider})")
    print(f"VLM       : {settings.vlm_configured}")

    container = get_container()
    await container.startup()
    if container.fallbacks:
        print(f"WARN: provider fallbacks active: {[note.as_dict() for note in container.fallbacks]}")

    principal = await _principal_from_db()
    print(f"Principal : {principal.user_id} / {principal.tenant_id} / role={principal.role}")

    runner = V2Runner(container, settings)
    modes = ["current", "oracle"] if args.mode == "both" else [args.mode]
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    reports: dict[str, dict] = {}

    for mode in modes:
        print(f"\n>>> running mode={mode} ...")

        def _progress(index: int, total: int, row: dict) -> None:
            flag = f"FAIL[{row['failure_label']}]" if row.get("failure_label") else "ok"
            print(
                f"  [{index:>3}/{total}] {row['id']:<14} {flag:<22} "
                f"status={row.get('status')} lat={row.get('latency_ms')}ms"
            )

        report = await runner.run(
            principal,
            mode=mode,
            strategy=args.strategy,
            top_k=args.top_k,
            categories=args.categories,
            max_questions=args.limit,
            on_row=_progress,
        )
        reports[mode] = report
        out = EVAL_DIR / f"baseline_{mode}_{_slug(settings.llm_model)}.json"
        out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(f"  saved {out.relative_to(PROJECT_ROOT)}")
        _print_report(report, title=f"v2 evaluation — {mode}")

    if args.write_taxonomy and len(reports) == 2:
        path = PROJECT_ROOT / "docs" / "results" / "failure-taxonomy.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_taxonomy_markdown(reports), encoding="utf-8")
        print(f"\nwrote {path.relative_to(PROJECT_ROOT)}")

    await container.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
