from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from app.core.config import settings
from app.schemas.paper_editor import PaperCompileResponse, PaperFileRead, PaperFileUpdate, PaperProjectSummary
from app.services.paper_generation_service import TopTierPaperGenerator

router = APIRouter(prefix="/paper-editor", tags=["paper-editor"])

EDITABLE_SUFFIXES = {".tex", ".bib"}


def _generated_root() -> Path:
    return Path(settings.generated_papers_dir).resolve()


def _project_dir(project_name: str) -> Path:
    candidate = (_generated_root() / project_name).resolve()
    if _generated_root() not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid project path.")
    if not candidate.exists() or not candidate.is_dir():
        raise HTTPException(status_code=404, detail="Project not found.")
    return candidate


def _project_url(request: Request, project_name: str) -> str:
    return f"{str(request.base_url).rstrip('/')}{settings.generated_papers_mount_path}/{project_name}"


def _read_title(main_tex: Path) -> str:
    if not main_tex.exists():
        return main_tex.parent.name
    content = main_tex.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"\\title\{\s*(.*?)\s*\}", content, re.DOTALL)
    return match.group(1).strip() if match else main_tex.parent.name


def _editable_files(project_dir: Path) -> list[str]:
    files = []
    for path in project_dir.rglob("*"):
        if path.is_file() and path.suffix in EDITABLE_SUFFIXES:
            files.append(path.relative_to(project_dir).as_posix())
    return sorted(files)


def _resolve_file(project_dir: Path, file_path: str) -> Path:
    candidate = (project_dir / file_path).resolve()
    if project_dir not in candidate.parents and candidate != project_dir:
        raise HTTPException(status_code=400, detail="Invalid file path.")
    if candidate.suffix not in EDITABLE_SUFFIXES:
        raise HTTPException(status_code=400, detail="Only .tex and .bib files are editable.")
    if not candidate.exists() or not candidate.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return candidate


@router.get("/projects", response_model=list[PaperProjectSummary])
def list_projects(request: Request):
    summaries: list[PaperProjectSummary] = []
    for project_dir in sorted(_generated_root().iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if not project_dir.is_dir():
            continue
        pdf_path = project_dir / "main.pdf"
        summaries.append(
            PaperProjectSummary(
                project_name=project_dir.name,
                title=_read_title(project_dir / "main.tex"),
                updated_at=datetime.fromtimestamp(project_dir.stat().st_mtime),
                pdf_exists=pdf_path.exists(),
                pdf_url=f"{_project_url(request, project_dir.name)}/main.pdf" if pdf_path.exists() else None,
                tex_url=f"{_project_url(request, project_dir.name)}/main.tex",
            )
        )
    return summaries


@router.get("/projects/{project_name}/files", response_model=list[str])
def list_project_files(project_name: str):
    project_dir = _project_dir(project_name)
    return _editable_files(project_dir)


@router.get("/projects/{project_name}/files/{file_path:path}", response_model=PaperFileRead)
def read_project_file(project_name: str, file_path: str):
    project_dir = _project_dir(project_name)
    target = _resolve_file(project_dir, file_path)
    return PaperFileRead(
        project_name=project_name,
        file_path=file_path,
        content=target.read_text(encoding="utf-8"),
        updated_at=datetime.fromtimestamp(target.stat().st_mtime),
    )


@router.put("/projects/{project_name}/files/{file_path:path}", response_model=PaperFileRead)
def update_project_file(project_name: str, file_path: str, payload: PaperFileUpdate):
    project_dir = _project_dir(project_name)
    target = _resolve_file(project_dir, file_path)
    target.write_text(payload.content, encoding="utf-8")
    return PaperFileRead(
        project_name=project_name,
        file_path=file_path,
        content=payload.content,
        updated_at=datetime.fromtimestamp(target.stat().st_mtime),
    )


@router.post("/projects/{project_name}/compile", response_model=PaperCompileResponse)
def compile_project(project_name: str, request: Request):
    project_dir = _project_dir(project_name)
    generator = TopTierPaperGenerator()
    result = generator.compile_project(project_dir)
    pdf_url = f"{_project_url(request, project_name)}/main.pdf" if result["success"] else None
    return PaperCompileResponse(
        project_name=project_name,
        success=bool(result["success"]),
        pdf_url=pdf_url,
        log=result["log"],
        compiled_at=datetime.now(),
    )
