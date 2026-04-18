import pytest

@pytest.fixture(autouse=True)
def set_test_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DB_PATH", db_path)
    import db.database as dbmod
    monkeypatch.setattr(dbmod, "DB_PATH", db_path)
    return db_path
