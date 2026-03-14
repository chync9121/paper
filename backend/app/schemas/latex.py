from pydantic import BaseModel, Field


class LatexTableRequest(BaseModel):
    experiment_ids: list[int] = Field(default_factory=list)
    metric_names: list[str] = Field(default_factory=list)
    model_node_ids: list[int] = Field(default_factory=list)
    dataset_node_ids: list[int] = Field(default_factory=list)
    caption: str = "Main results."
    label: str = "tab:main-results"
    note: str | None = None
    placement: str = "t"
    precision: int = 2
    highlight_best: bool = True
    highlight_second: bool = True
    use_resizebox: bool = True
    compact: bool = True
    show_std: bool = True
    omit_zero_std: bool = True
    use_threeparttable: bool = True
    table_environment: str = "table"
    column_group_by: str = "dataset"


class LatexTableResponse(BaseModel):
    latex_code: str
    model_names: list[str]
    dataset_names: list[str]
    metric_names: list[str]
    num_runs: int
    num_metrics: int
    packages_hint: list[str]
    guideline_notes: list[str]
