from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportGenerateRequest(BaseModel):
    report_type: Literal["related_work", "experimental_analysis"]
    selected_node_ids: list[int] = Field(default_factory=list)
    selected_experiment_ids: list[int] = Field(default_factory=list)
    prompt: str | None = None
    title: str | None = None
    model_name: str | None = None
    temperature: float | None = None
    max_runs: int = 20
    max_metrics: int = 250


class ReportRead(BaseModel):
    id: int
    report_type: str
    title: str | None = None
    selected_node_ids: list[int]
    selected_run_ids: list[int]
    prompt: str | None = None
    context_snapshot: dict
    model_name: str | None = None
    output_markdown: str | None = None
    output_text: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
