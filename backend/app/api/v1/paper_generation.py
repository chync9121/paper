from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.schemas.paper_generation import PaperGenerationRequest, PaperGenerationResponse
from app.services.paper_generation_service import TopTierPaperGenerator

router = APIRouter(prefix="/paper-generation", tags=["paper-generation"])


@router.post("/generate", response_model=PaperGenerationResponse)
def generate_paper(payload: PaperGenerationRequest, request: Request, db: Session = Depends(get_db)):
    if not payload.experiment_ids:
        raise HTTPException(status_code=400, detail="At least one experiment_id is required.")

    generator = TopTierPaperGenerator()
    try:
        result = generator.generate(db=db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    output_dir = Path(result["output_dir"])
    relative_dir = output_dir.relative_to(Path(settings.generated_papers_dir))
    output_url_base = f"{settings.generated_papers_mount_path}/{relative_dir.as_posix()}"
    backend_base = str(request.base_url).rstrip("/")

    result["output_url_base"] = f"{backend_base}{output_url_base}"
    result["tex_url"] = f"{backend_base}{output_url_base}/main.tex"
    result["context_snapshot_url"] = f"{backend_base}{output_url_base}/context_snapshot.json"
    result["pdf_url"] = f"{backend_base}{output_url_base}/main.pdf" if result.get("pdf_compiled") else None
    return result
