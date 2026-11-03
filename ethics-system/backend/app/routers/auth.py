"""로그인·세션·사용자 관리."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from .. import audit, config, db
from ..deps import SESSION_COOKIE, client_ip, current_user, get_db, require_admin
from ..security import (hash_password, new_token, now, now_str, plus_hours, token_hash,
                        validate_password_policy, verify_password, fmt)

router = APIRouter(prefix="/api", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(max_length=256)


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=40)
    role: str = Field(pattern="^(admin|staff|viewer)$")
    email: str | None = None
    password: str


class UserPatch(BaseModel):
    name: str | None = None
    role: str | None = Field(default=None, pattern="^(admin|staff|viewer)$")
    email: str | None = None
    active: bool | None = None
    reset_password: str | None = None


def _public(u: dict) -> dict:
    return {k: u[k] for k in ("id", "username", "name", "role", "email", "must_change_pw") if k in u}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, conn=Depends(get_db)):
    ip = client_ip(request)
    u = db.one(conn.execute("SELECT * FROM users WHERE username=?", (body.username,)))
    if u and u["locked_until"] and u["locked_until"] > now_str():
        raise HTTPException(423, f"로그인 시도 초과로 잠겼습니다. {u['locked_until'][11:16]} 이후 다시 시도하세요.")
    if not u or not u["active"] or not verify_password(body.password, u["password_hash"]):
        if u:
            fails = u["failed_attempts"] + 1
            locked = fmt(now() + timedelta(minutes=config.LOCK_MINUTES)) if fails >= config.MAX_LOGIN_FAILS else None
            conn.execute("UPDATE users SET failed_attempts=?, locked_until=? WHERE id=?",
                         (0 if locked else fails, locked, u["id"]))
        audit.log(conn, u["id"] if u else None, "auth.login_failed", "user", body.username, None, ip)
        raise HTTPException(401, "아이디 또는 비밀번호가 올바르지 않습니다.")
    token, csrf = new_token(), new_token()
    conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now_str(),))
    conn.execute("INSERT INTO sessions(token_hash, user_id, csrf_token, expires_at, ip, user_agent) VALUES (?,?,?,?,?,?)",
                 (token_hash(token), u["id"], csrf, plus_hours(config.SESSION_HOURS), ip,
                  (request.headers.get("user-agent") or "")[:200]))
    conn.execute("UPDATE users SET failed_attempts=0, locked_until=NULL, last_login_at=? WHERE id=?", (now_str(), u["id"]))
    audit.log(conn, u["id"], "auth.login", "user", u["id"], None, ip)
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict", secure=config.COOKIE_SECURE,
                        max_age=config.SESSION_HOURS * 3600, path="/")
    return {"user": _public(u), "csrf_token": csrf}


@router.post("/auth/logout")
def logout(request: Request, response: Response, user=Depends(current_user), conn=Depends(get_db)):
    conn.execute("DELETE FROM sessions WHERE token_hash=?", (user["token_hash"],))
    audit.log(conn, user["id"], "auth.logout", "user", user["id"], None, client_ip(request))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return {"user": _public(user), "csrf_token": user["csrf_token"]}


@router.post("/auth/password")
def change_password(body: PasswordIn, request: Request, user=Depends(current_user), conn=Depends(get_db)):
    row = db.one(conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)))
    if not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(400, "현재 비밀번호가 올바르지 않습니다.")
    if err := validate_password_policy(body.new_password):
        raise HTTPException(400, err)
    if body.new_password == body.current_password:
        raise HTTPException(400, "새 비밀번호가 기존 비밀번호와 같습니다.")
    conn.execute("UPDATE users SET password_hash=?, must_change_pw=0 WHERE id=?", (hash_password(body.new_password), user["id"]))
    # 다른 세션 모두 종료
    conn.execute("DELETE FROM sessions WHERE user_id=? AND token_hash<>?", (user["id"], user["token_hash"]))
    audit.log(conn, user["id"], "auth.password_changed", "user", user["id"], None, client_ip(request))
    return {"ok": True}


@router.get("/users")
def list_users(user=Depends(current_user), conn=Depends(get_db)):
    return db.rows(conn.execute(
        "SELECT id, username, name, role, email, active, last_login_at, created_at FROM users ORDER BY id"))


@router.post("/users")
def create_user(body: UserIn, request: Request, admin=Depends(require_admin), conn=Depends(get_db)):
    if err := validate_password_policy(body.password):
        raise HTTPException(400, err)
    if conn.execute("SELECT 1 FROM users WHERE username=?", (body.username,)).fetchone():
        raise HTTPException(409, "이미 사용 중인 아이디입니다.")
    uid = conn.execute("INSERT INTO users(username, name, role, email, password_hash, must_change_pw) VALUES (?,?,?,?,?,1)",
                       (body.username, body.name, body.role, body.email, hash_password(body.password))).lastrowid
    audit.log(conn, admin["id"], "user.create", "user", uid, {"username": body.username, "role": body.role}, client_ip(request))
    return {"id": uid}


@router.patch("/users/{uid}")
def update_user(uid: int, body: UserPatch, request: Request, admin=Depends(require_admin), conn=Depends(get_db)):
    target = db.one(conn.execute("SELECT * FROM users WHERE id=?", (uid,)))
    if not target:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    sets = {}
    for f in ("name", "role", "email"):
        v = getattr(body, f)
        if v is not None:
            sets[f] = v
    if body.active is not None:
        sets["active"] = 1 if body.active else 0
    if uid == admin["id"] and (sets.get("role", "admin") != "admin" or sets.get("active", 1) == 0):
        raise HTTPException(400, "자기 자신의 관리자 권한을 해제하거나 비활성화할 수 없습니다.")
    if body.reset_password:
        if err := validate_password_policy(body.reset_password):
            raise HTTPException(400, err)
        sets["password_hash"] = hash_password(body.reset_password)
        sets["must_change_pw"] = 1
        sets["failed_attempts"] = 0
        sets["locked_until"] = None
    if not sets:
        return {"ok": True}
    conn.execute(f"UPDATE users SET {', '.join(k + '=?' for k in sets)} WHERE id=?", (*sets.values(), uid))
    if "active" in sets and not sets["active"] or "password_hash" in sets:
        conn.execute("DELETE FROM sessions WHERE user_id=?", (uid,))
    audit.log(conn, admin["id"], "user.update", "user", uid,
              {k: v for k, v in sets.items() if k != "password_hash"}, client_ip(request))
    return {"ok": True}
