from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ExperimentRun, KGNode, RunMetric
from app.schemas.latex import LatexTableRequest, LatexTableResponse
from app.services.latex_service import guideline_notes, latex_package_hints, normalize_orders, render_latex_table

router = APIRouter(prefix="/latex", tags=["latex"])


@router.post("/generate", response_model=LatexTableResponse)
def generate_latex_table(payload: LatexTableRequest, db: Session = Depends(get_db)):
    if not payload.experiment_ids:
        raise HTTPException(status_code=400, detail="At least one experiment_id is required.")

    run_query = db.query(ExperimentRun).filter(ExperimentRun.experiment_id.in_(payload.experiment_ids))
    if payload.model_node_ids:
        run_query = run_query.filter(ExperimentRun.model_node_id.in_(payload.model_node_ids))
    if payload.dataset_node_ids:
        run_query = run_query.filter(ExperimentRun.dataset_node_id.in_(payload.dataset_node_ids))

    runs = run_query.order_by(ExperimentRun.created_at.desc()).all()
    if not runs:
        raise HTTPException(status_code=404, detail="No runs found for the selected filters.")

    run_ids = [run.id for run in runs]
    metrics_query = db.query(RunMetric).filter(RunMetric.run_id.in_(run_ids))
    if payload.metric_names:
        metrics_query = metrics_query.filter(RunMetric.metric_name.in_(payload.metric_names))
    metrics = metrics_query.order_by(RunMetric.created_at.desc()).all()
    if not metrics:
        raise HTTPException(status_code=404, detail="No metrics found for the selected filters.")

    node_ids = {
        run.model_node_id
        for run in runs
        if run.model_node_id is not None
    } | {
        run.dataset_node_id
        for run in runs
        if run.dataset_node_id is not None
    }
    nodes = db.query(KGNode).filter(KGNode.id.in_(list(node_ids))).all() if node_ids else []
    node_map = {node.id: node.name for node in nodes}

    cell_values: dict[tuple[str, str, str], list[float]] = {}
    metric_directions: dict[str, bool] = {}
    model_names: list[str] = []
    dataset_names: list[str] = []
    metric_names: list[str] = []

    run_map = {run.id: run for run in runs}
    for metric in metrics:
        run = run_map.get(metric.run_id)
        if run is None or run.model_node_id is None or run.dataset_node_id is None:
            continue
        model_name = node_map.get(run.model_node_id, f"model-{run.model_node_id}")
        dataset_name = node_map.get(run.dataset_node_id, f"dataset-{run.dataset_node_id}")
        key = (model_name, dataset_name, metric.metric_name)
        cell_values.setdefault(key, []).append(metric.metric_value)
        metric_directions.setdefault(metric.metric_name, metric.higher_is_better)
        model_names.append(model_name)
        dataset_names.append(dataset_name)
        metric_names.append(metric.metric_name)

    requested_model_names = [node_map.get(node_id) for node_id in payload.model_node_ids if node_map.get(node_id)]
    requested_dataset_names = [node_map.get(node_id) for node_id in payload.dataset_node_ids if node_map.get(node_id)]
    final_models, final_datasets, final_metrics = normalize_orders(
        model_names=model_names,
        dataset_names=dataset_names,
        metric_names=metric_names,
        requested_models=requested_model_names or None,
        requested_datasets=requested_dataset_names or None,
        requested_metrics=payload.metric_names or None,
    )

    try:
        latex_code = render_latex_table(
            model_order=final_models,
            dataset_order=final_datasets,
            metric_order=final_metrics,
            cell_values=cell_values,
            metric_directions=metric_directions,
            caption=payload.caption,
            label=payload.label,
            note=payload.note,
            placement=payload.placement,
            precision=payload.precision,
            highlight_best=payload.highlight_best,
            highlight_second=payload.highlight_second,
            use_resizebox=payload.use_resizebox,
            compact=payload.compact,
            show_std=payload.show_std,
            omit_zero_std=payload.omit_zero_std,
            use_threeparttable=payload.use_threeparttable,
            table_environment=payload.table_environment,
            column_group_by=payload.column_group_by,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LatexTableResponse(
        latex_code=latex_code,
        model_names=final_models,
        dataset_names=final_datasets,
        metric_names=final_metrics,
        num_runs=len(runs),
        num_metrics=len(metrics),
        packages_hint=latex_package_hints(
            use_threeparttable=payload.use_threeparttable,
            use_resizebox=payload.use_resizebox,
        ),
        guideline_notes=guideline_notes(),
    )
