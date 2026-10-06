"""Evaluation endpoints: experiments, dataset, runs and comparisons.

A run is executed by the real pipeline against the hand-labelled golden dataset.
Experiments that cannot run on this deployment (for example the vision-ablation
experiment with no vision endpoint configured) are stored with status
``unavailable`` and the reason, rather than being reported with empty metrics.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import ContainerDep, PrincipalDep, get_client_ip
from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.evaluation.runner import EvaluationRunner
from app.schemas.common import Page
from app.schemas.evaluation import (
    EvaluationComparisonOut,
    EvaluationRunDetailOut,
    EvaluationRunOut,
    EvaluationRunRequest,
    ExperimentInfoOut,
    GoldenQuestionOut,
)
from app.security import audit
from app.security.rbac import PERM_EVALUATION_READ, PERM_EVALUATION_RUN, Principal
from app.services import evaluation as service

router = APIRouter(tags=["evaluation"], prefix="/evaluation")


@router.get("/experiments", response_model=list[ExperimentInfoOut], summary="Available experiments")
async def list_experiments(
    container=ContainerDep,
    settings: Settings = Depends(get_settings),
    principal: Principal = PrincipalDep,
) -> list[ExperimentInfoOut]:
    principal.require(PERM_EVALUATION_READ)
    runner = EvaluationRunner(container, settings)
    return [ExperimentInfoOut(**info) for info in runner.experiment_infos()]


@router.get("/dataset", summary="Golden dataset summary and questions")
async def golden_dataset(
    container=ContainerDep,
    settings: Settings = Depends(get_settings),
    principal: Principal = PrincipalDep,
) -> dict:
    principal.require(PERM_EVALUATION_READ)
    runner = EvaluationRunner(container, settings)
    summary = runner.dataset_summary()
    from app.evaluation.dataset import load_golden_dataset

    dataset = load_golden_dataset(settings.evaluation_dir)
    summary["questions"] = [GoldenQuestionOut(**question.as_dict()).model_dump() for question in dataset.questions]
    return summary


@router.get("/runs", response_model=Page[EvaluationRunOut], summary="List evaluation runs")
async def list_runs(
    limit: int = 25,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Page[EvaluationRunOut]:
    principal.require(PERM_EVALUATION_READ)
    items, total = await service.list_runs(session, principal, limit=limit, offset=offset)
    return Page[EvaluationRunOut](
        items=[EvaluationRunOut(**item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        has_more=offset + len(items) < total,
    )


@router.post("/runs", response_model=list[EvaluationRunOut], summary="Run one or more experiments")
async def run_evaluation(
    payload: EvaluationRunRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
    container=ContainerDep,
    settings: Settings = Depends(get_settings),
) -> list[EvaluationRunOut]:
    principal.require(PERM_EVALUATION_RUN)
    runner = EvaluationRunner(container, settings)
    payloads = await runner.run(
        principal,
        experiments=payload.experiments,
        categories=payload.categories or None,
        max_questions=payload.max_questions,
        top_k=payload.top_k,
        name=payload.name,
    )
    await audit.record_principal_action(
        session,
        principal,
        action=audit.ACTION_EVALUATION_RUN,
        resource_type="evaluation_run",
        resource_id=",".join(run["id"] for run in payloads),
        ip_address=get_client_ip(request),
        detail={"experiments": payload.experiments, "runs": [run["status"] for run in payloads]},
    )
    return [EvaluationRunOut(**run) for run in payloads]


@router.get("/runs/{run_id}", response_model=EvaluationRunDetailOut, summary="Evaluation run detail")
async def run_detail(
    run_id: str,
    include_results: bool = True,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> EvaluationRunDetailOut:
    principal.require(PERM_EVALUATION_READ)
    payload = await service.evaluation_run_payload(
        session, principal, run_id, include_results=include_results
    )
    return EvaluationRunDetailOut(**payload)


@router.delete("/runs/{run_id}", status_code=204, summary="Delete an evaluation run")
async def delete_run(
    run_id: str,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> Response:
    principal.require(PERM_EVALUATION_RUN)
    await service.delete_run(session, principal, run_id)
    return Response(status_code=204)


@router.get("/compare", response_model=EvaluationComparisonOut, summary="Compare stored runs")
async def compare_runs(
    run_ids: str,
    session: AsyncSession = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> EvaluationComparisonOut:
    principal.require(PERM_EVALUATION_READ)
    ids = [value.strip() for value in run_ids.split(",") if value.strip()]
    payload = await service.compare_runs(session, principal, ids)
    return EvaluationComparisonOut(**payload)
