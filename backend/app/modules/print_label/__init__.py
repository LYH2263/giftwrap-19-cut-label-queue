"""裁切签（cut label）：出签瞬间的 run 快照 + 内容校验和。

签面字段在「出签」那一刻从 run 及其当时盒名冻结为 face_json；之后无论
盒边/折边（overlap）如何修改、run 是否作废，都不回算、不改写已出签面——
签面快照与现场主数据是双源取舍。

checksum = sha256(canonical_json(face))：键排序、紧凑分隔、ensure_ascii=False，
仅依赖签面字段本身，保证算法自洽、可重算、可测试。
"""
import hashlib
import json

# 签面关键字段：顺序仅为可读性，哈希前一律按键名排序
FACE_FIELDS = (
    "label_no",
    "run_id",
    "box_name",
    "paper_m2",
    "ribbon_m",
    "overlap",
    "wrap_style",
    "issued_at",
)


def canonical_json(face: dict) -> str:
    """稳定序列化：同一内容（不论键序）必得同一字符串。"""
    return json.dumps(face, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def checksum_of(face: dict) -> str:
    return hashlib.sha256(canonical_json(face).encode("utf-8")).hexdigest()


def build_face(*, run: dict, box_name, label_seq: int, issued_at: str) -> dict:
    """从 run 行（result 已解析）冻结出一份签面。只读 run，不碰现场主数据。"""
    result = run["result"]
    ribbon = result.get("ribbon") or {}
    return {
        "label_no": f"L{label_seq}",
        "run_id": run["id"],
        "box_name": box_name,
        "paper_m2": result["paper_m2"],
        "ribbon_m": ribbon.get("ribbon_m"),
        "overlap": result.get("overlap", run.get("overlap")),
        "wrap_style": ribbon.get("wrap_style"),
        "issued_at": issued_at,
    }
