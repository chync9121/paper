from datetime import datetime

from pydantic import BaseModel


class PaperProjectSummary(BaseModel):
    project_name: str
    title: str
    updated_at: datetime
    pdf_exists: bool
    pdf_url: str | None = None
    tex_url: str | None = None


class PaperFileRead(BaseModel):
    project_name: str
    file_path: str
    content: str
    updated_at: datetime


class PaperFileUpdate(BaseModel):
    content: str


class PaperCompileResponse(BaseModel):
    project_name: str
    success: bool
    pdf_url: str | None = None
    log: str
    compiled_at: datetime
