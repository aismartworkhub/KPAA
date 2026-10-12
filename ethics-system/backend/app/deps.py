"""FastAPI 의존성: DB 연결, 인증 사용자, 권한, CSRF."""
from typing import Iterator

from fastapi import Depends, HTTPException, Request

from . import db
from .security import now_str, token_hash

SESSION_COOKIE = "kpaa_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def get_db() -> Iterator:
    conn = db.get_conn()
    try:
        yield conn
    finally:
        conn.close()


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def current_user(request: Request, conn=Depends(get_db)) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(401, "로그인이 필요합니다.")
    row = db.one(conn.execute(
        """SELECT u.id, u.username, u.name, u.role, u.email, u.active, u.must_change_pw,
                  s.csrf_token, s.expires_at, s.token_hash
           FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?""",
        (token_hash(token),)))
    if not row or row["expires_at"] < now_str() or not row["active"]:
        raise HTTPException(401, "세션이 만료되었습니다. 다시 로그인하세요.")
    if request.method not in SAFE_METHODS:
        sent = request.headers.get("X-CSRF-Token", "")
        if sent != row["csrf_token"]:
            raise HTTPException(403, "요청 검증(CSRF)에 실패했습니다. 새로고침 후 다시 시도하세요.")
    return row


def require_staff(user=Depends(current_user)) -> dict:
    if user["role"] not in ("admin", "staff"):
        raise HTTPException(403, "조회 전용 계정은 변경 작업을 할 수 없습니다.")
    return user


def require_admin(user=Depends(current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "관리자 권한이 필요합니다.")
    return user
