"""설정·백업·감사로그·시스템 상태."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .. import __version__, audit, config, db
from ..deps import client_ip, current_user, get_db, require_admin
from ..services import backup, case_service, llm, mailer

router = APIRouter(prefix="/api/admin", tags=["admin"])

SETTING_KEYS = {"org_name", "dept_name", "explanation_days", "correction_days", "discipline_after_days", "objection_days",
                "limitation_years", "doc_no_prefix", "ad_case_owner", "ethics_case_owner", "contact_phone",
                "contact_email", "approval_line", "cooperation_line"}
INT_KEYS = {"explanation_days", "correction_days", "discipline_after_days", "objection_days", "limitation_years"}


class SettingsIn(BaseModel):
    values: dict[str, str]


@router.get("/status")
def status(user=Depends(current_user), conn=Depends(get_db)):
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("cases", "evidence", "articles", "precedents", "source_documents", "doc_chunks", "documents", "meetings", "users")}
    return {"version": __version__, "ai_available": llm.available(), "ai_model": config.AI_MODEL if llm.available() else None,
            "smtp_configured": mailer.configured(), "counts": counts, "db_path": str(config.DB_PATH) if user["role"] == "admin" else None}


@router.get("/settings")
def get_settings(user=Depends(current_user), conn=Depends(get_db)):
    return case_service.get_settings(conn)


@router.put("/settings")
def put_settings(body: SettingsIn, request: Request, admin=Depends(require_admin), conn=Depends(get_db)):
    bad = set(body.values) - SETTING_KEYS
    if bad:
        raise HTTPException(400, f"알 수 없는 설정: {', '.join(bad)}")
    for k, v in body.values.items():
        if k in INT_KEYS and (not v.isdigit() or not 0 < int(v) < 10000):
            raise HTTPException(400, f"{k} 는 양의 정수여야 합니다.")
    with db.transaction(conn):
        for k, v in body.values.items():
            conn.execute("INSERT INTO settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
        audit.log(conn, admin["id"], "settings.update", "settings", None, body.values, client_ip(request))
    return {"ok": True}


@router.get("/backups")
def list_backups(admin=Depends(require_admin)):
    return backup.list_backups()


@router.post("/backups")
def create_backup(request: Request, admin=Depends(require_admin), conn=Depends(get_db)):
    r = backup.create_backup()
    audit.log(conn, admin["id"], "backup.create", "backup", r["db"], r, client_ip(request))
    return r


@router.get("/backups/{name}")
def download_backup(name: str, request: Request, admin=Depends(require_admin), conn=Depends(get_db)):
    p = backup.backup_path(name)
    if not p:
        raise HTTPException(404, "백업 파일을 찾을 수 없습니다.")
    audit.log(conn, admin["id"], "backup.download", "backup", name, None, client_ip(request))
    return FileResponse(p, filename=name, media_type="application/octet-stream")


@router.get("/audit")
def audit_log(limit: int = 200, action: str | None = None, admin=Depends(require_admin), conn=Depends(get_db)):
    limit = max(1, min(limit, 1000))
    if action:
        return db.rows(conn.execute(
            "SELECT a.*, u.name AS user_name FROM audit_log a LEFT JOIN users u ON u.id=a.user_id WHERE action LIKE ? ORDER BY a.id DESC LIMIT ?",
            (f"{action}%", limit)))
    return db.rows(conn.execute(
        "SELECT a.*, u.name AS user_name FROM audit_log a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT ?", (limit,)))
