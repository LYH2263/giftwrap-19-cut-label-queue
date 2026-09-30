from fastapi import APIRouter, HTTPException
from app.repositories import history as repo
from app.services import labels as label_service

router = APIRouter()


@router.get("/runs")
def runs(limit: int = 50):
    return {"items": repo.list_runs(limit)}


@router.get("/runs/{run_id}")
def get_run(run_id: int):
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return run


@router.post("/runs/{run_id}/void", status_code=200)
def void_run(run_id: int):
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    if run["voided"]:
        raise HTTPException(409, "run already voided")
    repo.void_run(run_id)
    return repo.get_run(run_id)


@router.post("/runs/{run_id}/labels", status_code=201)
def issue_run_label(run_id: int):
    return label_service.issue_label(run_id)
