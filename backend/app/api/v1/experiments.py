from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Experiment, ExperimentRun, RunMetric
from app.schemas.experiments import (
    ExperimentCreate,
    ExperimentMetricsRow,
    ExperimentRead,
    ExperimentRunCreate,
    ExperimentRunRead,
    RunMetricBatchCreate,
    RunMetricRead,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("", response_model=ExperimentRead)
def create_experiment(payload: ExperimentCreate, db: Session = Depends(get_db)):
    item = Experiment(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[ExperimentRead])
def list_experiments(db: Session = Depends(get_db)):
    return db.query(Experiment).order_by(Experiment.created_at.desc()).all()


@router.post("/{experiment_id}/runs", response_model=ExperimentRunRead)
def create_run(experiment_id: int, payload: ExperimentRunCreate, db: Session = Depends(get_db)):
    exists = db.query(Experiment.id).filter(Experiment.id == experiment_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    run = ExperimentRun(experiment_id=experiment_id, **payload.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/{experiment_id}/runs", response_model=list[ExperimentRunRead])
def list_runs(experiment_id: int, db: Session = Depends(get_db)):
    exists = db.query(Experiment.id).filter(Experiment.id == experiment_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return (
        db.query(ExperimentRun)
        .filter(ExperimentRun.experiment_id == experiment_id)
        .order_by(ExperimentRun.created_at.desc())
        .all()
    )


@router.post("/runs/{run_id}/metrics/batch", response_model=list[RunMetricRead])
def add_metrics(run_id: int, payload: RunMetricBatchCreate, db: Session = Depends(get_db)):
    run_exists = db.query(ExperimentRun.id).filter(ExperimentRun.id == run_id).first()
    if not run_exists:
        raise HTTPException(status_code=404, detail="Run not found.")
    created = []
    for metric in payload.metrics:
        row = RunMetric(run_id=run_id, **metric.model_dump())
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


@router.get("/{experiment_id}/metrics", response_model=list[ExperimentMetricsRow])
def get_experiment_metrics(experiment_id: int, db: Session = Depends(get_db)):
    runs = db.query(ExperimentRun).filter(ExperimentRun.experiment_id == experiment_id).all()
    run_map = {r.id: r for r in runs}
    if not run_map:
        return []

    metrics = db.query(RunMetric).filter(RunMetric.run_id.in_(list(run_map.keys()))).all()
    rows = []
    for metric in metrics:
        run = run_map[metric.run_id]
        rows.append(
            ExperimentMetricsRow(
                run_id=run.id,
                run_name=run.run_name,
                model_node_id=run.model_node_id,
                dataset_node_id=run.dataset_node_id,
                metric_name=metric.metric_name,
                metric_value=metric.metric_value,
                stage=metric.stage,
            )
        )
    return rows
