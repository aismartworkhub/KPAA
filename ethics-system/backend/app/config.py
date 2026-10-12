"""환경변수 기반 설정. 모든 값은 .env 또는 실행 환경에서 덮어쓸 수 있다."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
PROJECT_DIR = BASE_DIR.parent                                # ethics-system/


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


DATA_DIR = Path(_env("KPAA_DATA_DIR", str(PROJECT_DIR / "data")))
DB_PATH = Path(_env("KPAA_DB_PATH", str(DATA_DIR / "kpaa_ethics.db")))
UPLOAD_DIR = DATA_DIR / "uploads"
BACKUP_DIR = Path(_env("KPAA_BACKUP_DIR", str(DATA_DIR / "backups")))
FRONTEND_DIR = Path(_env("KPAA_FRONTEND_DIR", str(PROJECT_DIR / "frontend")))
SEED_REGULATIONS = BASE_DIR / "seed" / "regulations.txt"

# 세션 / 보안
SESSION_HOURS = int(_env("KPAA_SESSION_HOURS", "10"))
COOKIE_SECURE = _env("KPAA_COOKIE_SECURE", "0") == "1"      # HTTPS 운영 시 1
MAX_LOGIN_FAILS = int(_env("KPAA_MAX_LOGIN_FAILS", "5"))
LOCK_MINUTES = int(_env("KPAA_LOCK_MINUTES", "15"))
MAX_UPLOAD_MB = int(_env("KPAA_MAX_UPLOAD_MB", "200"))
INITIAL_ADMIN_PASSWORD = os.environ.get("KPAA_ADMIN_PASSWORD")  # 최초 기동 시 관리자 비밀번호

# 백업
BACKUP_KEEP = int(_env("KPAA_BACKUP_KEEP", "30"))

# AI (선택). 키가 없으면 규칙·검색 기반 기능만 동작한다.
AI_ENABLED = _env("KPAA_AI_ENABLED", "1") == "1"
AI_MODEL = _env("KPAA_AI_MODEL", "claude-opus-5-5")
AI_EFFORT = _env("KPAA_AI_EFFORT", "high")

ALLOWED_UPLOAD_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".hwp", ".hwpx",
    ".txt", ".csv", ".docx", ".mp3", ".m4a", ".wav", ".mp4",
}

# 메일 발송(선택). 미설정 시 '발송 기록' 수동 입력 방식으로 동작한다.
SMTP_HOST = os.environ.get("KPAA_SMTP_HOST")
SMTP_PORT = int(_env("KPAA_SMTP_PORT", "587"))
SMTP_USER = os.environ.get("KPAA_SMTP_USER")
SMTP_PASSWORD = os.environ.get("KPAA_SMTP_PASSWORD")
SMTP_FROM = os.environ.get("KPAA_SMTP_FROM")
SMTP_STARTTLS = _env("KPAA_SMTP_STARTTLS", "1") == "1"
SMTP_BCC_SELF = _env("KPAA_SMTP_BCC_SELF", "1") == "1"   # 발신 근거 보관용 사본
