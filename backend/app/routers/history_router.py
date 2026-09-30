from fastapi import APIRouter
from app.repositories import history as repo
from app.services import label_service
router = APIRouter()
@router.get("/runs")
def runs(limit: int = 50): return {"items": repo.list_runs(limit)}
@router.post("/runs/{run_id}/void")
def void_run(run_id: int): return label_service.void_run(run_id)
