import json
from datetime import datetime, timezone
from app.db import connect
from app.services.label_checksum import face_checksum

_LABEL_SELECT = """SELECT l.*, COALESCE(r.voided,0) run_voided
                   FROM cut_labels l LEFT JOIN calc_runs r ON r.id=l.run_id"""


def create_label(run_id, run_row):
    """单连接单提交：先插占位行拿 label_id，再回填签面快照与 checksum。

    盒名只在此刻随 get_run 的 LEFT JOIN 读一次并冻进 face_json；
    之后 boxes / calc_runs 的任何变动都不触达快照。
    """
    from app.services.labels import build_face  # 局部导入规避 repo↔service 环

    c = connect()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = c.execute(
            "INSERT INTO cut_labels(run_id,face_json,checksum,status,issued_at,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (run_id, "", "", "queued", now, now),
        )
        label_id = int(cur.lastrowid)
        face = build_face(label_id, run_row, now)
        c.execute(
            "UPDATE cut_labels SET face_json=?, checksum=? WHERE id=?",
            (json.dumps(face, ensure_ascii=False, sort_keys=True),
             face_checksum(face), label_id),
        )
        c.commit()
        row = c.execute(_LABEL_SELECT + " WHERE l.id=?", (label_id,)).fetchone()
        return dict(row)
    finally:
        c.close()

def list_labels(run_id=None, limit=100):
    c = connect()
    try:
        if run_id is None:
            rows = c.execute(
                _LABEL_SELECT + " ORDER BY l.id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = c.execute(
                _LABEL_SELECT + " WHERE l.run_id=? ORDER BY l.id DESC LIMIT ?",
                (run_id, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        c.close()

def get_label(label_id):
    c = connect()
    try:
        row = c.execute(_LABEL_SELECT + " WHERE l.id=?", (label_id,)).fetchone()
        return dict(row) if row else None
    finally:
        c.close()

def mark_printed(label_id):
    """queued→printed 单向流转。返回 'missing' | 'conflict' | 'printed'。

    只更新 status/printed_at，绝不触碰 face_json/checksum。
    """
    c = connect()
    try:
        if c.execute("SELECT id FROM cut_labels WHERE id=?", (label_id,)).fetchone() is None:
            return "missing"
        now = datetime.now(timezone.utc).isoformat()
        cur = c.execute(
            "UPDATE cut_labels SET status='printed', printed_at=? WHERE id=? AND status='queued'",
            (now, label_id),
        )
        c.commit()
        if cur.rowcount == 1:
            return "printed"
        return "conflict"
    finally:
        c.close()
