"""Deterministic evaluation used as a CI gate.

The full v2 run uses a local model and is not reproducible in CI. This script
uses the same 130 labelled questions but the deterministic stack: hashing
embeddings, the lexical reranker and extractive generation (no LLM endpoint).
Retrieval and refusal therefore measure the pipeline itself, not a model
sampling.

    python scripts_phase3/eval_ci.py --write-baseline   # once, commit the file
    python scripts_phase3/eval_ci.py                   # CI: fail on >3pt drop

Exit status 1 when any tracked metric falls more than three points below the
committed baseline.
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
CI_ROOT = Path(os.environ.get("EVAL_VAR_DIR", str(BACKEND_DIR / "var" / "eval-ci")))

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{(CI_ROOT / 'eval.db').as_posix()}")
os.environ.setdefault("VAR_DIR", (CI_ROOT / "var").as_posix())
os.environ.setdefault("LOCAL_STORAGE_DIR", (CI_ROOT / "storage").as_posix())
os.environ.setdefault("OCR_ENABLED", "false")
os.environ.setdefault("VLM_ENABLED", "false")
os.environ.setdefault("EMBEDDING_PROVIDER", "hashing")
os.environ.setdefault("RERANKER_PROVIDER", "lexical")
os.environ.setdefault("RERANKER_ENABLED", "true")
os.environ.setdefault("ALLOW_PROVIDER_FALLBACK", "false")
os.environ["LLM_BASE_URL"] = ""
os.environ["LLM_MODEL"] = ""

sys.path.insert(0, str(BACKEND_DIR))
from app.config.settings import reset_settings_cache  # noqa: E402

reset_settings_cache()

TRACKED = {
    "retrieval.recall_at_10": ("retrieval", "recall_at_10"),
    "retrieval.mrr": ("retrieval", "mrr"),
    "answer.correct": ("answer", "correct", "rate"),
    "refusal.precision": ("refusal", "precision"),
    "refusal.recall": ("refusal", "recall"),
    "citation.precision": ("citation", "mean_precision"),
}
TOLERANCE = 0.03


def _value(report: dict, path: tuple[str, ...]) -> float | None:
    node: object = report
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return None
        node = node[key]
    return float(node) if isinstance(node, (int, float)) else None


async def _principal():
    from sqlalchemy import select

    from app.db.models import Tenant, User
    from app.db.session import session_scope
    from app.security.rbac import Principal

    async with session_scope() as session:
        tenant = (await session.execute(select(Tenant).limit(1))).scalar_one_or_none()
        user = (
            await session.execute(select(User).where(User.tenant_id == tenant.id).limit(1))
        ).scalar_one_or_none()
    return Principal(
        user_id=user.id if user else "ci-runner",
        tenant_id=tenant.id,
        email=user.email if user else "ci@local",
        role=user.role if user else "admin",
    )


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    from app.config.container import get_container
    from app.config.settings import get_settings
    from app.evaluation.v2_runner import V2Runner

    settings = get_settings()
    if settings.llm_configured:
        raise SystemExit("CI evaluation must run without an LLM; LLM_BASE_URL/LLM_MODEL are set")
    print(f"DB={settings.database_url} embedding={settings.embedding_provider} reranker={settings.reranker_provider}")

    container = get_container()
    await container.startup()
    principal = await _principal()
    runner = V2Runner(container, settings)
    report = await runner.run(principal, mode="current", top_k=10, max_questions=args.limit)
    await container.shutdown()

    metrics = {name: _value(report, path) for name, path in TRACKED.items()}
    print(json.dumps(metrics, indent=2))
    out = EVAL_DIR / "ci_result.json"
    out.write_text(json.dumps({"metrics": metrics, "report": report}, indent=2, default=str), encoding="utf-8")

    if args.write_baseline:
        baseline = EVAL_DIR / "ci_baseline.json"
        baseline.write_text(
            json.dumps(
                {
                    "note": (
                        "Deterministic: hashing embeddings, lexical reranker, extractive generation. "
                        "Regenerate with `python scripts_phase3/eval_ci.py --write-baseline`."
                    ),
                    "metrics": metrics,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"wrote {baseline.relative_to(PROJECT_ROOT)}")
        return 0

    baseline_path = EVAL_DIR / "ci_baseline.json"
    if not baseline_path.exists():
        raise SystemExit(f"missing baseline {baseline_path}; run with --write-baseline")
    baseline_metrics = json.loads(baseline_path.read_text(encoding="utf-8"))["metrics"]

    failures: list[str] = []
    for name, current in metrics.items():
        previous = baseline_metrics.get(name)
        if current is None or previous is None:
            continue
        if current < previous - TOLERANCE:
            failures.append(f"{name}: {previous:.4f} -> {current:.4f} (drop {previous - current:.4f} > 0.03)")
        else:
            print(f"OK   {name}: baseline {previous:.4f} current {current:.4f}")
    if failures:
        print("\nCI gate failed:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nCI gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
