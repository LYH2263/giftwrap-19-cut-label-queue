from fastapi import HTTPException

from app.repositories import history, labels


def issue_label(run_id: int):
    run = history.get_run(run_id)
    if not run:
        raise HTTPException(404, "run not found")
    if run["voided"]:
        # run 一旦作废，禁止再出新签；已出签仍只读可查
        raise HTTPException(409, "run 已作废，禁止出签")
    return labels.issue_label(run)


def print_label(label_id: int):
    label = labels.get_label(label_id)
    if not label:
        raise HTTPException(404, "label not found")
    label, _changed = labels.mark_printed(label_id)
    return label


def void_run(run_id: int):
    if not history.void_run(run_id):
        raise HTTPException(404, "run not found")
    return history.get_run(run_id)
