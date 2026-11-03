"""비밀번호 해시(PBKDF2-SHA256), 세션 토큰, 시간 유틸."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

PBKDF2_ITERATIONS = int(os.environ.get("KPAA_PBKDF2_ITERATIONS", "390000"))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def validate_password_policy(password: str) -> str | None:
    """정책 위반 시 사유 문자열, 통과 시 None."""
    if len(password) < 10:
        return "비밀번호는 10자 이상이어야 합니다."
    kinds = sum([
        any(c.isalpha() for c in password),
        any(c.isdigit() for c in password),
        any(not c.isalnum() for c in password),
    ])
    if kinds < 2:
        return "영문·숫자·특수문자 중 2종류 이상을 조합해야 합니다."
    return None


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def now_str() -> str:
    return now().strftime("%Y-%m-%d %H:%M:%S")


def fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def plus_hours(hours: int) -> str:
    return fmt(now() + timedelta(hours=hours))
