import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("KPAA_PBKDF2_ITERATIONS", "1000")   # 테스트 속도용
os.environ.pop("ANTHROPIC_API_KEY", None)

ADMIN_PW = "Admin!2345pw"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app import config
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(config, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(config, "INITIAL_ADMIN_PASSWORD", ADMIN_PW)
    from app.services import search
    search.clear_cache()
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def login(client, username="admin", password=ADMIN_PW) -> dict:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": r.json()["csrf_token"]}


@pytest.fixture()
def admin(client):
    return login(client)
