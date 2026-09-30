from app.services.label_checksum import canonical_payload, face_checksum


def test_canonical_sorts_keys_and_compact():
    assert canonical_payload({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_known_vector_simple():
    assert face_checksum({"b": 2, "a": 1}) == \
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"


def test_checksum_independent_of_key_order():
    assert face_checksum({"a": 1, "b": 2}) == face_checksum({"b": 2, "a": 1})


def test_known_vector_full_face():
    face = {
        "label_id": 7,
        "run_id": 12,
        "box_name": "书型盒",
        "paper_m2": 0.31,
        "ribbon_m": 2.0,
        "wrap_style": "cross",
        "overlap": 1.15,
        "issued_at": "2026-09-30T08:00:00+00:00",
    }
    assert canonical_payload(face) == (
        '{"box_name":"书型盒","issued_at":"2026-09-30T08:00:00+00:00",'
        '"label_id":7,"overlap":1.15,"paper_m2":0.31,"ribbon_m":2.0,'
        '"run_id":12,"wrap_style":"cross"}'
    )
    assert face_checksum(face) == \
        "c6a71efe6917989ae6bdfe173120e7ee417dbf11f880d77f0d92fb4719a18fec"


def test_null_is_stable():
    a = {"box_name": None, "ribbon_m": None}
    assert canonical_payload(a) == '{"box_name":null,"ribbon_m":null}'
    assert face_checksum(a) == face_checksum(a)
