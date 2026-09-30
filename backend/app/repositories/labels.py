import json
import sqlite3
from datetime import datetime, timezone

from app.db import connect
from app.modules import print_label


def _now():
    return datetime.now(timezone.utc).isoformat()


def _row_to_label(row):
    d = dict(row)
    d["face"] = json.loads(d.pop("face_json"))
    d["voided"] = d.get("run_voided") == "voided"
    return d


def issue_label(run):
    """对一个未落库校验过的 run 出签：冻结快照、算 checksum、入队。

    允许同一 run 多次出签，每次 label_seq 递增、checksum/issued_at 各自独立。
    出签本身不写 calc_runs。
    """
    c = connect()
    try:
        for _ in range(5):
            nxt = c.execute(
                "SELECT COALESCE(MAX(label_seq),0)+1 s FROM cut_labels WHERE run_id=?",
                (run["id"],),
            ).fetchone()["s"]
            face = print_label.build_face(
                run=run, box_name=run.get("box_name"), label_seq=nxt, issued_at=_now()
            )
            checksum = print_label.checksum_of(face)
            try:
                cur = c.execute(
                    "INSERT INTO cut_labels(run_id,label_seq,face_json,checksum,status,issued_at)"
                    " VALUES (?,?,?,?,?,?)",
                    (
                        run["id"],
                        nxt,
                        print_label.canonical_json(face),
                        checksum,
                        "queued",
                        face["issued_at"],
                    ),
                )
                c.commit()
                return get_label(int(cur.lastrowid), conn=c)
            except sqlite3.IntegrityError:
                # 并发下 label_seq 撞号，重取序号重试
                c.rollback()
        raise sqlite3.IntegrityError("could not allocate label_seq")
    finally:
        c.close()


def list_labels(status=None):
    c = connect()
    try:
        sql = (
            "SELECT l.*, r.voided run_voided, b.name box_name"
            " FROM cut_labels l"
            " JOIN calc_runs r ON r.id=l.run_id"
            " LEFT JOIN boxes b ON b.id=r.box_id"
        )
        params = ()
        if status in ("queued", "printed"):
            sql += " WHERE l.status=?"
            params = (status,)
        sql += " ORDER BY l.id DESC"
        return [_row_to_label(r) for r in c.execute(sql, params).fetchall()]
    finally:
        c.close()


def get_label(label_id, conn=None):
    own = conn is None
    c = conn or connect()
    try:
        row = c.execute(
            "SELECT l.*, r.voided run_voided, b.name box_name"
            " FROM cut_labels l"
            " JOIN calc_runs r ON r.id=l.run_id"
            " LEFT JOIN boxes b ON b.id=r.box_id"
            " WHERE l.id=?",
            (label_id,),
        ).fetchone()
        return _row_to_label(row) if row else None
    finally:
        if own:
            c.close()


def mark_printed(label_id):
    """queued -> printed，单向。printed 不可改回 queued。

    返回 (label, changed)：changed=False 表示本来就是 printed（正文仍只读）。
    """
    c = connect()
    try:
        row = c.execute("SELECT status FROM cut_labels WHERE id=?", (label_id,)).fetchone()
        if not row:
            return None, False
        if row["status"] == "printed":
            return get_label(label_id, conn=c), False
        c.execute(
            "UPDATE cut_labels SET status='printed', printed_at=? WHERE id=? AND status='queued'",
            (_now(), label_id),
        )
        c.commit()
        return get_label(label_id, conn=c), True
    finally:
        c.close()
