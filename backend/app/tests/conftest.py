import pytest
from app import db, seed


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """隔离临时库。必须 patch app.db.DB_PATH —— db.py 顶部已把名字绑定到自身命名空间。"""
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    seed.init_db()
    return db.DB_PATH
