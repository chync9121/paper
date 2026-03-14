from pydantic import BaseModel, Field


class PaperGenerationRequest(BaseModel):
    title: str
    experiment_ids: list[int] = Field(default_factory=list)
    selected_node_ids: list[int] = Field(default_factory=list)
    target_venue: str = "CVPR"
    main_metric_names: list[str] = Field(default_factory=list)
    primary_dataset_names: list[str] = Field(default_factory=list)
    prompt: str | None = None
    model_name: str | None = None
    use_llm: bool = True
    try_compile_pdf: bool = True


class PaperGenerationResponse(BaseModel):
    title: str
    target_venue: str
    output_dir: str
    tex_path: str
    figure_paths: list[str]
    table_paths: list[str]
    used_llm: bool
    pdf_compiled: bool
    pdf_path: str | None = None
    pdf_url: str | None = None
    output_url_base: str | None = None
    tex_url: str | None = None
    context_snapshot_url: str | None = None
    compile_log: str | None = None
    sections: dict[str, str]
