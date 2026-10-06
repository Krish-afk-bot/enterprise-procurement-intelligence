"""Acceptance check: run the PRD's demonstration questions end to end.

Usage::

    python scripts/acceptance_check.py --questions 1 2 3 4 5 6 7

Prints the answer, the citations it used, the verification result and the
retrieval steps that actually ran. Nothing is hard-coded: if the evidence is
missing the script shows the refusal instead.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.agents.pipeline import AnswerPipeline  # noqa: E402
from app.config.container import get_container  # noqa: E402
from app.config.settings import get_settings  # noqa: E402
from app.db.session import dispose_engine, init_db, session_scope  # noqa: E402
from app.services import auth as auth_service  # noqa: E402

#: Windows consoles default to a legacy code page; keep printed output ASCII-safe.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass

QUESTIONS: dict[int, str] = {
    1: "What is Supplier A's current price for the Industrial Laptop X200?",
    2: "What changed between the original contract and Amendment 2?",
    3: "Compare Supplier A and Supplier B prices for the Industrial Laptop X200.",
    4: "Which supplier had the lowest price in 2025?",
    5: "What does the pricing table on page 4 say?",
    6: "What was Supplier C's price in 2030?",
    7: "Which suppliers hold ISO 9001 certification and what contract do they supply under?",
}


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run the acceptance questions")
    parser.add_argument("--questions", nargs="*", type=int, default=sorted(QUESTIONS))
    parser.add_argument("--email", default="admin@epi.local")
    parser.add_argument("--json", action="store_true", help="print the full answer payloads")
    args = parser.parse_args()

    settings = get_settings()
    container = get_container()
    await container.startup()
    await init_db()

    async with session_scope() as session:
        tenant = await auth_service.get_or_create_default_tenant(session, settings)
        user = await auth_service.get_user_by_email(session, tenant.id, args.email)
        if user is None:
            print(f"No user {args.email}: run `python -m app.cli ingest ...` first", file=sys.stderr)
            return 2
        principal = auth_service.principal_from_user(user)

    pipeline = AnswerPipeline(container, settings)
    payloads: dict[int, dict] = {}
    for number in args.questions:
        question = QUESTIONS.get(number)
        if question is None:
            print(f"Unknown question number {number}")
            continue
        result = await pipeline.answer(principal, question)
        payloads[number] = result.model_dump(mode="json")
        print("=" * 88)
        print(f"Q{number}. {question}")
        print("-" * 88)
        print(result.answer_text)
        print("-" * 88)
        print(
            f"status={result.status} generation_mode={result.generation_mode} "
            f"evidence_strength={result.evidence_strength.level} "
            f"grounding={result.grounding.supported_claims}/{result.grounding.total_claims} "
            f"({result.grounding.method}) citations={len(result.citations)} "
            f"degraded={result.degraded}"
        )
        if result.conflicts:
            print("conflicts:")
            for conflict in result.conflicts:
                print(f"  ! {conflict.description}")
                print(f"    -> {conflict.resolution}")
        print("retrieval steps:")
        for step in result.retrieval_steps:
            print(
                f"  - {step.name}: {step.status}, candidates={step.candidates}, "
                f"{step.latency_ms if step.latency_ms is not None else '-'} ms — {step.detail}"
            )
        print(f"timings: {result.timings}")
        print(f"evidence criteria: {json.dumps(result.evidence_strength.criteria, default=str)}")
        print(f"validation: {json.dumps(result.validation, default=str)}")
        print()

    if args.json:
        print(json.dumps(payloads, indent=2, default=str))

    await container.shutdown()
    await dispose_engine()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
