import json

import pytest

from app.db import connect
from app.modules import print_label
from app.repositories import history, labels as label_repo

try:
    from fastapi import HTTPException
    from app.services import label_service
    HAVE_FASTAPI = True
except ImportError:  # 仅装了标准库时，服务层用例跳过
    HAVE_FASTAPI = False


RESULT = {
    "box_surface": 0.27,
    "overlap": 1.15,
    "paper_m2": 0.31,
    "ribbon": {"wrap_style": "cross", "ribbon_m": 1.9},
    "box_id": 1,
}


@pytest.fixture
def db(tmp_path, monkeypatch):
    import app.db as dbmod
    path = tmp_path / "test.db"
    monkeypatch.setattr(dbmod, "DB_PATH", path)
    from app import seed
    seed.init_db()
    return path


def _run_count():
    c = connect()
    try:
        return c.execute("SELECT COUNT(*) n FROM calc_runs").fetchone()["n"]
    finally:
        c.close()


def test_checksum_is_stable_and_order_independent():
    face = {"box_name": "书型盒", "paper_m2": 0.31, "ribbon_m": 1.9}
    reordered = {"ribbon_m": 1.9, "box_name": "书型盒", "paper_m2": 0.31}
    assert print_label.checksum_of(face) == print_label.checksum_of(reordered)
    assert print_label.checksum_of(face) == print_label.checksum_of(face)
    changed = dict(face, paper_m2=0.32)
    assert print_label.checksum_of(changed) != print_label.checksum_of(face)


def test_issue_freezes_snapshot_without_new_run(db):
    run_id = history.insert_run(1, 1.15, dict(RESULT), "")
    before = _run_count()
    l1 = label_repo.issue_label(history.get_run(run_id))
    l2 = label_repo.issue_label(history.get_run(run_id))
    after = _run_count()
    # 出签不新增 calc_runs
    assert after == before == 1
    # 同一 run 可多次出签，队列行与 checksum 各自独立
    assert l1["id"] != l2["id"]
    assert l1["face"]["label_no"] == "L1"
    assert l2["face"]["label_no"] == "L2"
    assert l1["checksum"] != l2["checksum"]  # issued_at/label_no 不同
    assert l1["status"] == "queued"
    for lab in (l1, l2):
        assert lab["face"]["box_name"] == "书型盒"
        assert lab["face"]["paper_m2"] == 0.31
        assert lab["face"]["ribbon_m"] == 1.9
        # checksum 可由签面重算复核
        assert print_label.checksum_of(lab["face"]) == lab["checksum"]


def test_label_face_immutable_after_master_data_change(db):
    run_id = history.insert_run(1, 1.15, dict(RESULT), "")
    lab = label_repo.issue_label(history.get_run(run_id))
    snap_face, snap_checksum = json.loads(json.dumps(lab["face"], ensure_ascii=False)), lab["checksum"]

    # 之后改盒边（盒尺寸/盒名）与折边系数
    c = connect()
    c.execute("UPDATE boxes SET name=?, length=? WHERE id=1", ("改名盒", 0.99))
    c.execute("UPDATE calc_runs SET overlap=? WHERE id=?", (1.42, run_id))
    c.commit()
    c.close()

    again = label_repo.get_label(lab["id"])
    assert again["face"] == snap_face
    assert again["checksum"] == snap_checksum


def test_printed_is_terminal_and_body_readonly(db):
    run_id = history.insert_run(1, 1.15, dict(RESULT), "")
    lab = label_repo.issue_label(history.get_run(run_id))
    body_before, cs_before = json.dumps(lab["face"], ensure_ascii=False), lab["checksum"]

    printed, changed = label_repo.mark_printed(lab["id"])
    assert changed is True and printed["status"] == "printed" and printed["printed_at"]
    again, changed2 = label_repo.mark_printed(lab["id"])
    assert changed2 is False and again["status"] == "printed"  # 不可改回 queued
    assert json.dumps(again["face"], ensure_ascii=False) == body_before
    assert again["checksum"] == cs_before


def test_queue_and_detail_share_same_fields(db):
    run_id = history.insert_run(1, 1.15, dict(RESULT), "")
    lab = label_repo.issue_label(history.get_run(run_id))
    queued = [x for x in label_repo.list_labels() if x["id"] == lab["id"]][0]
    detail = label_repo.get_label(lab["id"])
    assert queued["face"] == detail["face"]
    assert queued["checksum"] == detail["checksum"] == print_label.checksum_of(detail["face"])
    assert detail["run_id"] == run_id  # 从签可回链用纸档


@pytest.mark.skipif(not HAVE_FASTAPI, reason="fastapi 未安装")
def test_voided_run_blocks_new_labels_but_keeps_printed_readable(db):
    run_id = history.insert_run(1, 1.15, dict(RESULT), "")
    lab = label_service.issue_label(run_id)
    label_service.print_label(lab["id"])
    label_service.void_run(run_id)

    with pytest.raises(HTTPException) as ei:
        label_service.issue_label(run_id)
    assert ei.value.status_code == 409

    kept = label_repo.get_label(lab["id"])
    assert kept["status"] == "printed"
    assert kept["voided"] is True  # 随 run 作废只作只读标记
    assert kept["face"]["paper_m2"] == 0.31
    assert history.get_run(run_id)["voided"] is True
