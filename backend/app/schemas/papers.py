from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PaperCreate(BaseModel):
    title: str
    venue: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None


class PaperRead(BaseModel):
    id: int
    title: str
    venue: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
