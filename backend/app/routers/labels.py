from fastapi import APIRouter, HTTPException, Query

from app.services import label_service
from app.repositories import labels as labels_repo

router = APIRouter()


@router.get("/labels")
def list_labels(status: str | None = Query(default=None)):
    """裁切签队列；status 仅取 queued/printed，缺省返回全部。"""
    return {"items": labels_repo.list_labels(status)}


@router.get("/labels/{label_id}")
def get_label(label_id: int):
    label = labels_repo.get_label(label_id)
    if not label:
        raise HTTPException(404, "label not found")
    return label


@router.post("/runs/{run_id}/labels")
def issue_label(run_id: int):
    """对已落库且未作废的 run 出签；不新增 calc_runs。"""
    return label_service.issue_label(run_id)


@router.post("/labels/{label_id}/print")
def print_label(label_id: int):
    """queued -> printed，单向。"""
    return label_service.print_label(label_id)
