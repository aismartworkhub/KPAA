"""업로드 파일 저장(무결성 해시 기록, 경로 조작 방지)."""
import hashlib
import mimetypes
import re
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile

from .. import config


def safe_name(name: str) -> str:
    name = Path(name or "file").name
    name = re.sub(r"[^\w.\-가-힣 ()\[\]]+", "_", name).strip() or "file"
    return name[:150]


async def save_upload(file: UploadFile, subdir: str, allowed: set[str] | None = None) -> dict:
    allowed = allowed or config.ALLOWED_UPLOAD_EXT
    original = safe_name(file.filename or "file")
    ext = Path(original).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"허용되지 않는 파일 형식입니다: {ext or '(확장자 없음)'}")
    target_dir = config.UPLOAD_DIR / subdir / datetime.now().strftime("%Y%m")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid.uuid4().hex}{ext}"
    h = hashlib.sha256()
    size = 0
    limit = config.MAX_UPLOAD_MB * 1024 * 1024
    with open(target, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(413, f"파일이 너무 큽니다(최대 {config.MAX_UPLOAD_MB}MB).")
            h.update(chunk)
            out.write(chunk)
    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(400, "빈 파일입니다.")
    return {
        "file_name": original,
        "stored_path": str(target.relative_to(config.UPLOAD_DIR)),
        "size": size,
        "sha256": h.hexdigest(),
        "mime": file.content_type or mimetypes.guess_type(original)[0] or "application/octet-stream",
    }


def resolve(stored_path: str) -> Path:
    p = (config.UPLOAD_DIR / stored_path).resolve()
    if config.UPLOAD_DIR.resolve() not in p.parents or not p.is_file():
        raise HTTPException(404, "파일을 찾을 수 없습니다.")
    return p
