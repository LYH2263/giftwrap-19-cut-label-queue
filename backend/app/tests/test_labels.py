import json
import sqlite3
import pytest
from fastapi import HTTPException

from app import db
from app.repositories import history
from app.services import labels as svc
from app.services.estimate_service import run_estimate
from app.services.label_checksum import face_checksum


def make_run(box_id=1, wrap_style="cross"):
    return run_estimate(box_id, None, wrap_style, True, "")["run_id"]


def raw_conn():
    return sqlite3.connect(db.DB_PATH)


def table_count(table):
    c = raw_conn()
    try:
        return c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        c.close()


# ① 出签字段来源
def test_issue_label_fields(tmp_db):
    run_id = make_run(1)
    dto = svc.issue_label(run_id)
    assert dto["status"] == "queued"
    assert dto["printed_at"] is None
    assert dto["run_voided"] is False
    assert dto["box_name"] == "书型盒"
    assert dto["paper_m2"] == 0.31
    assert dto["ribbon_m"] == 2.2
    assert dto["wrap_style"] == "cross"
    assert dto["overlap"] == 1.15
    assert dto["run_id"] == run_id
    assert len(dto["checksum"]) == 64


# ② 出签不新增 calc_runs，cut_labels +1
def test_issue_does_not_create_run(tmp_db):
    run_id = make_run(1)
    before = table_count("calc_runs")
    labels_before = table_count("cut_labels")
    svc.issue_label(run_id)
    assert table_count("calc_runs") == before
    assert table_count("cut_labels") == labels_before + 1


# ③ 同一 run 多次出签：行与 checksum 独立
def test_multiple_labels_independent(tmp_db):
    run_id = make_run(1)
    a = svc.issue_label(run_id)
    b = svc.issue_label(run_id)
    assert a["id"] != b["id"]
    assert a["checksum"] != b["checksum"]


def test_face_holds_distinct_label_id_and_checksum_recomputes(tmp_db):
    run_id = make_run(1)
    a = svc.issue_label(run_id)
    b = svc.issue_label(run_id)
    c = raw_conn()
    try:
        fa = json.loads(c.execute("SELECT face_json FROM cut_labels WHERE id=?", (a["id"],)).fetchone()[0])
        fb = json.loads(c.execute("SELECT face_json FROM cut_labels WHERE id=?", (b["id"],)).fetchone()[0])
    finally:
        c.close()
    # ④ face 不含 checksum 自指；重算与列值一致
    assert "checksum" not in fa and "checksum" not in fb
    assert fa["label_id"] == a["id"] and fb["label_id"] == b["id"]
    assert face_checksum(fa) == a["checksum"]
    assert face_checksum(fb) == b["checksum"]


# ⑤ 打印状态机
def test_print_state_machine(tmp_db):
    run_id = make_run(1)
    lab = svc.issue_label(run_id)
    out = svc.print_label(lab["id"])
    assert out["status"] == "printed"
    assert out["printed_at"]
    with pytest.raises(HTTPException) as ei:
        svc.print_label(lab["id"])
    assert ei.value.status_code == 409
    with pytest.raises(HTTPException) as en:
        svc.print_label(999999)
    assert en.value.status_code == 404


# ⑥ printed 后正文逐字不变
def test_printed_face_immutable(tmp_db):
    run_id = make_run(1)
    lab = svc.issue_label(run_id)
    c = raw_conn()
    face_before = c.execute("SELECT face_json FROM cut_labels WHERE id=?", (lab["id"],)).fetchone()[0]
    c.close()
    svc.print_label(lab["id"])
    got = svc.get_label(lab["id"])
    assert got["box_name"] == lab["box_name"]
    assert got["paper_m2"] == lab["paper_m2"]
    assert got["ribbon_m"] == lab["ribbon_m"]
    assert got["checksum"] == lab["checksum"]
    c = raw_conn()
    assert c.execute("SELECT face_json FROM cut_labels WHERE id=?", (lab["id"],)).fetchone()[0] == face_before
    c.close()


# ⑦ 作废：禁止再出签；旧 printed 签只读可查且带 run_voided
def test_void_blocks_new_labels_but_keeps_old(tmp_db):
    run_id = make_run(1)
    lab = svc.issue_label(run_id)
    svc.print_label(lab["id"])
    assert history.void_run(run_id) is True
    with pytest.raises(HTTPException) as ei:
        svc.issue_label(run_id)
    assert ei.value.status_code == 409
    old = svc.get_label(lab["id"])
    assert old["status"] == "printed"
    assert old["run_voided"] is True
    assert old["checksum"] == lab["checksum"]
    # 重复作废 409，不存在 404（经由 router 同款校验在 service 无 void 规则，故直接验 router 仓储语义）
    assert history.void_run(run_id) is False


# ⑧ 快照隔离：出签后改盒边/盒名与 run 数据，签面不动
def test_snapshot_isolated_from_master_data(tmp_db):
    run_id = make_run(1)
    lab = svc.issue_label(run_id)
    c = raw_conn()
    try:
        c.execute("UPDATE boxes SET name=?, length=? WHERE id=1", ("被改名的盒", 9.9))
        c.execute("UPDATE calc_runs SET overlap=?, result_json=? WHERE id=?",
                  (2.5, json.dumps({"paper_m2": 9.99, "ribbon": {"wrap_style": "band", "ribbon_m": 8.88}}), run_id))
        c.commit()
    finally:
        c.close()
    for dto in (svc.get_label(lab["id"]), svc.list_labels()[0]):
        assert dto["box_name"] == "书型盒"
        assert dto["paper_m2"] == 0.31
        assert dto["ribbon_m"] == 2.2
        assert dto["wrap_style"] == "cross"
        assert dto["overlap"] == 1.15
        assert dto["checksum"] == lab["checksum"]


# ⑨ ribbon 裸数 / 缺失容错
def test_ribbon_tolerance(tmp_db):
    rid_raw = history.insert_run(1, 1.15, {"paper_m2": 0.5, "ribbon": 2.0}, "")
    dto = svc.issue_label(rid_raw)
    assert dto["ribbon_m"] == 2.0
    assert dto["wrap_style"] is None
    rid_none = history.insert_run(1, 1.15, {"paper_m2": 0.6}, "")
    dto2 = svc.issue_label(rid_none)
    assert dto2["ribbon_m"] is None
    assert dto2["wrap_style"] is None


# ⑩ 悬空 box_id：盒名缺失不崩
def test_dangling_box_name_none(tmp_db):
    run_id = history.insert_run(999999, 1.15, {"paper_m2": 0.4, "ribbon": {"wrap_style": "cross", "ribbon_m": 1.0}}, "")
    dto = svc.issue_label(run_id)
    assert dto["box_name"] is None
    assert dto["paper_m2"] == 0.4


# ⑪ 404 矩阵
def test_404_matrix(tmp_db):
    with pytest.raises(HTTPException) as e1:
        svc.issue_label(999999)
    assert e1.value.status_code == 404
    with pytest.raises(HTTPException) as e2:
        svc.get_label(999999)
    assert e2.value.status_code == 404
    assert history.get_run(999999) is None


# ⑫ 列表过滤与排序
def test_list_filter_and_order(tmp_db):
    r1, r2 = make_run(1), make_run(1)
    l1 = svc.issue_label(r1)
    l2 = svc.issue_label(r2)
    l3 = svc.issue_label(r1)
    ids_all = [d["id"] for d in svc.list_labels()]
    assert ids_all == sorted(ids_all, reverse=True)
    assert set(ids_all) == {l1["id"], l2["id"], l3["id"]}
    ids_r1 = [d["id"] for d in svc.list_labels(run_id=r1)]
    assert set(ids_r1) == {l1["id"], l3["id"]}
    assert svc.list_labels(run_id=888888) == []


# ⑬ 老库迁移：无 voided 列的 calc_runs 经 init_db 后补列、默认 0、可出签
def test_migration_old_db(tmp_path, monkeypatch):
    path = str(tmp_path / "old.db")
    c = sqlite3.connect(path)
    c.executescript("""
    CREATE TABLE boxes(id INTEGER PRIMARY KEY,name TEXT,length REAL,width REAL,height REAL,data_quality TEXT,note TEXT);
    INSERT INTO boxes(name,length,width,height,data_quality,note) VALUES ('老盒',0.3,0.2,0.15,'clean','');
    CREATE TABLE papers(id INTEGER PRIMARY KEY,name TEXT,roll_width REAL,data_quality TEXT,note TEXT);
    CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE calc_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,box_id INT,overlap REAL,result_json TEXT,note TEXT,created_at TEXT);
    INSERT INTO calc_runs(box_id,overlap,result_json,note,created_at)
      VALUES (1,1.15,'{"paper_m2":0.31,"ribbon":{"wrap_style":"cross","ribbon_m":2.2}}','','2026-01-01T00:00:00+00:00');
    """)
    c.commit()
    c.close()
    monkeypatch.setattr(db, "DB_PATH", path)
    from app import seed
    seed.init_db()
    cols = {r[1] for r in raw_conn().execute("PRAGMA table_info(calc_runs)").fetchall()}
    assert "voided" in cols
    run = history.get_run(1)
    assert run["voided"] is False
    assert run["box_name"] == "老盒"
    dto = svc.issue_label(1)
    assert dto["box_name"] == "老盒"
    assert dto["paper_m2"] == 0.31
