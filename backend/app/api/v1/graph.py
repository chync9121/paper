from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import KGEdge, KGNode
from app.schemas.graph import KGEdgeCreate, KGEdgeRead, KGNodeCreate, KGNodeRead, SubgraphResponse

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/nodes", response_model=KGNodeRead)
def create_node(payload: KGNodeCreate, db: Session = Depends(get_db)):
    node = KGNode(**payload.model_dump())
    db.add(node)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Node already exists.")
    db.refresh(node)
    return node


@router.get("/nodes", response_model=list[KGNodeRead])
def list_nodes(
    node_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(KGNode)
    if node_type:
        query = query.filter(KGNode.node_type == node_type)
    if q:
        query = query.filter(KGNode.name.ilike(f"%{q}%"))
    return query.order_by(KGNode.created_at.desc()).all()


@router.post("/edges", response_model=KGEdgeRead)
def create_edge(payload: KGEdgeCreate, db: Session = Depends(get_db)):
    edge = KGEdge(**payload.model_dump())
    db.add(edge)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Edge already exists.")
    db.refresh(edge)
    return edge


@router.get("/subgraph", response_model=SubgraphResponse)
def get_subgraph(node_ids: list[int] = Query(default=[]), db: Session = Depends(get_db)):
    if not node_ids:
        return SubgraphResponse(nodes=[], edges=[])
    nodes = db.query(KGNode).filter(KGNode.id.in_(node_ids)).all()
    edges = db.query(KGEdge).filter(
        KGEdge.source_node_id.in_(node_ids),
        KGEdge.target_node_id.in_(node_ids),
    ).all()
    return SubgraphResponse(nodes=nodes, edges=edges)
