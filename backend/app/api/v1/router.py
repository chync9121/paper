from fastapi import APIRouter

from app.api.v1.experiments import router as experiments_router
from app.api.v1.graph import router as graph_router
from app.api.v1.latex import router as latex_router
from app.api.v1.paper_editor import router as paper_editor_router
from app.api.v1.paper_generation import router as paper_generation_router
from app.api.v1.papers import router as papers_router
from app.api.v1.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(papers_router)
api_router.include_router(graph_router)
api_router.include_router(experiments_router)
api_router.include_router(latex_router)
api_router.include_router(reports_router)
api_router.include_router(paper_generation_router)
api_router.include_router(paper_editor_router)
