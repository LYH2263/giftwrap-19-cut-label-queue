"""裁切签业务规则：出签快照、状态机、统一 DTO。"""
import json
from fastapi import HTTPException
from app.repositories import history, labels as label_repo

# 签面快照字段（不含 checksum 自身）
FACE_KEYS = ("label_id", "run_id", "box_name", "paper_m2", "ribbon_m",
             "wrap_style", "overlap", "issued_at")


def _ribbon_fields(result):
    """result.ribbon 可能是 dict（正常）、裸数（历史数据）或缺失。缺失用 None，不用 0 顶替。"""
    r = (result or {}).get("ribbon")
    if isinstance(r, dict):
        return r.get("ribbon_m"), r.get("wrap_style")
    if isinstance(r, (int, float)):
        return float(r), None
    return None, None


def build_face(label_id, run_row, issued_at):
    """纯组装：把出签瞬间的 run 现场值冻结成签面 dict。无 IO。"""
    result = run_row.get("result") or {}
    ribbon_m, wrap_style = _ribbon_fields(result)
    overlap = run_row.get("overlap")
    if overlap is None:
        overlap = result.get("overlap")
    return {
        "label_id": label_id,
        "run_id": run_row["id"],
        "box_name": run_row.get("box_name"),  # LEFT JOIN 可能缺失（悬空 box_id），允许 None
        "paper_m2": result.get("paper_m2"),
        "ribbon_m": ribbon_m,
        "wrap_style": wrap_style,
        "overlap": overlap,
        "issued_at": issued_at,
    }


def to_label_dto(row):
    """列表/详情唯一出口：签面字段全部钉自 face_json；run_voided 是显式命名的当前态附标。"""
    face = json.loads(row["face_json"])
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "status": row["status"],
        "issued_at": row["issued_at"],
        "printed_at": row["printed_at"],
        "checksum": row["checksum"],
        "box_name": face.get("box_name"),
        "paper_m2": face.get("paper_m2"),
        "ribbon_m": face.get("ribbon_m"),
        "wrap_style": face.get("wrap_style"),
        "overlap": face.get("overlap"),
        "run_voided": bool(row["run_voided"]),
    }


def issue_label(run_id):
    run = history.get_run(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    if run.get("voided"):
        raise HTTPException(409, "run voided")
    row = label_repo.create_label(run_id, run)
    return to_label_dto(row)


def print_label(label_id):
    outcome = label_repo.mark_printed(label_id)
    if outcome == "missing":
        raise HTTPException(404, "label not found")
    if outcome == "conflict":
        raise HTTPException(409, "label already printed")
    return to_label_dto(label_repo.get_label(label_id))


def get_label(label_id):
    row = label_repo.get_label(label_id)
    if row is None:
        raise HTTPException(404, "label not found")
    return to_label_dto(row)


def list_labels(run_id=None, limit=100):
    return [to_label_dto(r) for r in label_repo.list_labels(run_id, limit)]
