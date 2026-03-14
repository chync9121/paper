from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KGNodeCreate(BaseModel):
    node_type: str = Field(..., examples=["model", "dataset", "metric", "paper"])
    name: str
    canonical_name: str | None = None
    description: str | None = None
    paper_id: int | None = None
    extra: dict = Field(default_factory=dict)


class KGNodeRead(BaseModel):
    id: int
    node_type: str
    name: str
    canonical_name: str | None = None
    description: str | None = None
    paper_id: int | None = None
    extra: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KGEdgeCreate(BaseModel):
    source_node_id: int
    target_node_id: int
    relation_type: str
    paper_id: int | None = None
    confidence: float | None = None
    evidence_text: str | None = None


class KGEdgeRead(BaseModel):
    id: int
    source_node_id: int
    target_node_id: int
    relation_type: str
    paper_id: int | None = None
    confidence: float | None = None
    evidence_text: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubgraphResponse(BaseModel):
    nodes: list[KGNodeRead]
    edges: list[KGEdgeRead]
