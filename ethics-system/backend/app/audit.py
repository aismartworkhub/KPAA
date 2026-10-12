"""감사 로그 기록. 모든 변경 작업은 여기를 거친다."""
import json
import sqlite3


def log(conn: sqlite3.Connection, user_id: int | None, action: str, entity: str | None = None,
        entity_id=None, detail=None, ip: str | None = None) -> None:
    if detail is not None and not isinstance(detail, str):
        detail = json.dumps(detail, ensure_ascii=False, default=str)
    conn.execute(
        "INSERT INTO audit_log(user_id, action, entity, entity_id, detail, ip) VALUES (?,?,?,?,?,?)",
        (user_id, action, entity, None if entity_id is None else str(entity_id), detail, ip),
    )
