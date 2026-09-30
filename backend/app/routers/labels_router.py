from fastapi import APIRouter
from app.services import labels as label_service

router = APIRouter()


@router.get("/labels")
def list_labels(run_id: int | None = None, limit: int = 100):
    return {"items": label_service.list_labels(run_id, limit)}


@router.get("/labels/{label_id}")
def get_label(label_id: int):
    return label_service.get_label(label_id)


@router.post("/labels/{label_id}/print", status_code=200)
def print_label(label_id: int):
    return label_service.print_label(label_id)
