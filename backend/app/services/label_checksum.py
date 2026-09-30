"""裁切签内容校验和：对签面关键字段做稳定（canonical）序列化后取 SHA-256。

签面 dict 本身不含 checksum（自指）；checksum 是签面的函数，单独成列。
"""
import hashlib
import json


def canonical_payload(face: dict) -> str:
    """键排序、紧凑分隔、中文不转义的确定性 JSON。"""
    return json.dumps(face, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def face_checksum(face: dict) -> str:
    return hashlib.sha256(canonical_payload(face).encode("utf-8")).hexdigest()
