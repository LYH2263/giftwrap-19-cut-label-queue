import json
from datetime import datetime, timezone
from app.db import connect

def _row_to_run(row):
    d = dict(row)
    d["result"] = json.loads(d.pop("result_json"))
    d["voided"] = d.get("voided") == "voided"
    return d

def insert_run(box_id, overlap, result, note=""):
    c = connect()
    try:
        cur = c.execute(
            "INSERT INTO calc_runs(box_id,overlap,result_json,note,created_at) VALUES (?,?,?,?,?)",
            (box_id, overlap, json.dumps(result, ensure_ascii=False), note, datetime.now(timezone.utc).isoformat()),
        )
        c.commit()
        return int(cur.lastrowid)
    finally:
        c.close()

def get_run(run_id):
    c = connect()
    try:
        row = c.execute(
            "SELECT r.*, b.name box_name FROM calc_runs r LEFT JOIN boxes b ON b.id=r.box_id WHERE r.id=?",
            (run_id,),
        ).fetchone()
        return _row_to_run(row) if row else None
    finally:
        c.close()

def list_runs(limit=50):
    c = connect()
    try:
        rows = c.execute(
            """SELECT r.*, b.name box_name FROM calc_runs r LEFT JOIN boxes b ON b.id=r.box_id ORDER BY r.id DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [_row_to_run(r) for r in rows]
    finally:
        c.close()

def void_run(run_id):
    """作废 run：幂等。返回 True 表示存在（无论先前是否已作废）。"""
    c = connect()
    try:
        cur = c.execute("UPDATE calc_runs SET voided='voided' WHERE id=?", (run_id,))
        c.commit()
        return cur.rowcount > 0
    finally:
        c.close()
