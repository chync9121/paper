from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExperimentCreate(BaseModel):
    name: str
    description: str | None = None
    task_name: str | None = None
    owner: str | None = None


class ExperimentRead(BaseModel):
    id: int
    name: str
    description: str | None = None
    task_name: str | None = None
    owner: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExperimentRunCreate(BaseModel):
    run_name: str | None = None
    model_node_id: int | None = None
    dataset_node_id: int | None = None
    split: str | None = None
    seed: int | None = None
    params: dict = Field(default_factory=dict)
    artifact_path: str | None = None


class ExperimentRunRead(BaseModel):
    id: int
    experiment_id: int
    run_name: str | None = None
    model_node_id: int | None = None
    dataset_node_id: int | None = None
    split: str | None = None
    seed: int | None = None
    params: dict
    artifact_path: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunMetricCreate(BaseModel):
    metric_node_id: int | None = None
    metric_name: str
    metric_value: float
    higher_is_better: bool = True
    unit: str | None = None
    stage: str | None = None


class RunMetricBatchCreate(BaseModel):
    metrics: list[RunMetricCreate]


class RunMetricRead(BaseModel):
    id: int
    run_id: int
    metric_node_id: int | None = None
    metric_name: str
    metric_value: float
    higher_is_better: bool
    unit: str | None = None
    stage: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExperimentMetricsRow(BaseModel):
    run_id: int
    run_name: str | None = None
    model_node_id: int | None = None
    dataset_node_id: int | None = None
    metric_name: str
    metric_value: float
    stage: str | None = None
