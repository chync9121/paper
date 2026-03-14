from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import KGNode, Paper
from app.schemas.papers import PaperCreate, PaperRead

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("", response_model=PaperRead)
def create_paper(payload: PaperCreate, db: Session = Depends(get_db)):
    paper = Paper(**payload.model_dump())
    db.add(paper)
    db.flush()

    # Create a companion paper node so graph and bibliography stay connected.
    node = KGNode(
        node_type="paper",
        name=payload.title,
        canonical_name=payload.title,
        description=payload.abstract,
        paper_id=paper.id,
        extra={"venue": payload.venue, "year": payload.year},
    )
    db.add(node)
    db.commit()
    db.refresh(paper)
    return paper


@router.get("", response_model=list[PaperRead])
def list_papers(db: Session = Depends(get_db)):
    return db.query(Paper).order_by(Paper.created_at.desc()).all()
