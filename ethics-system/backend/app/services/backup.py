"""SQLite 온라인 백업(운영 중 일관성 보장) + 첨부파일 아카이브 + 보존 개수 관리."""
import sqlite3
import tarfile
from datetime import datetime
from pathlib import Path

from .. import config


def create_backup(include_uploads: bool = True) -> dict:
    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    db_target = config.BACKUP_DIR / f"kpaa_ethics_{stamp}.db"
    src = sqlite3.connect(str(config.DB_PATH))
    dst = sqlite3.connect(str(db_target))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    result = {"db": db_target.name, "db_size": db_target.stat().st_size}
    if include_uploads and config.UPLOAD_DIR.exists():
        tar_target = config.BACKUP_DIR / f"uploads_{stamp}.tar.gz"
        with tarfile.open(tar_target, "w:gz") as tar:
            tar.add(str(config.UPLOAD_DIR), arcname="uploads")
        result["uploads"] = tar_target.name
        result["uploads_size"] = tar_target.stat().st_size
    prune()
    return result


def list_backups() -> list[dict]:
    if not config.BACKUP_DIR.exists():
        return []
    out = []
    for p in sorted(config.BACKUP_DIR.iterdir(), reverse=True):
        if p.is_file() and (p.suffix == ".db" or p.name.endswith(".tar.gz")):
            out.append({"name": p.name, "size": p.stat().st_size,
                        "created": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")})
    return out


def prune(keep: int | None = None) -> None:
    keep = keep or config.BACKUP_KEEP
    for pattern in ("kpaa_ethics_*.db", "uploads_*.tar.gz"):
        files = sorted(config.BACKUP_DIR.glob(pattern), reverse=True)
        for old in files[keep:]:
            old.unlink(missing_ok=True)


def backup_path(name: str) -> Path | None:
    p = (config.BACKUP_DIR / name).resolve()
    if p.parent != config.BACKUP_DIR.resolve() or not p.is_file():
        return None
    return p


if __name__ == "__main__":   # cron:  python -m app.services.backup
    print(create_backup())
