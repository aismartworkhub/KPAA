"""사건 상태 전이 공통 로직(사건 화면·위원회 결정 반영에서 함께 사용)."""
from fastapi import HTTPException

from .. import audit, db
from . import workflow


def get_settings(conn) -> dict:
    return {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")}


def get_case(conn, case_id: int) -> dict:
    c = db.one(conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)))
    if not c:
        raise HTTPException(404, "사건을 찾을 수 없습니다.")
    return c


def transition(conn, case_id: int, to: str, note: str | None, user: dict, due_date: str | None = None,
               ip: str | None = None) -> dict:
    """트랜잭션 안에서 호출할 것."""
    case = get_case(conn, case_id)
    cur = case["status"]
    if to not in workflow.STATUSES:
        raise HTTPException(400, "알 수 없는 상태입니다.")
    if not workflow.can_transition(cur, to):
        raise HTTPException(409, f"'{workflow.STATUSES[cur]}'에서 '{workflow.STATUSES[to]}'(으)로 바로 변경할 수 없습니다.")
    key = f"{cur}->{to}"
    if key in workflow.ADMIN_ONLY and user["role"] != "admin":
        raise HTTPException(403, "종결 사건 재개는 관리자만 할 수 있습니다.")
    need = workflow.note_requirement(cur, to)
    if need and not (note and note.strip()):
        raise HTTPException(400, f"이 단계 변경에는 사유 기재가 필요합니다: {need}")
    settings = get_settings(conn)
    sets = {"status": to}
    if to == "EXPLANATION_REQUESTED":
        sets["explanation_due"] = due_date or workflow.add_days(None, int(settings.get("explanation_days", 14)))
    elif to == "CORRECTION_ORDERED":
        sets["correction_due"] = due_date or workflow.add_days(None, int(settings.get("correction_days", 30)))
    elif to == "DISCIPLINE" and due_date:
        sets["objection_due"] = due_date
    elif to == "CLOSED":
        sets["closed_reason"] = note
    if to == "REVIEW" and cur == "CLOSED":
        sets["closed_reason"] = None
    cols = ", ".join(f"{k}=?" for k in sets)
    conn.execute(f"UPDATE cases SET {cols}, updated_at=datetime('now','localtime') WHERE id=?", (*sets.values(), case_id))
    extra = ""
    if "explanation_due" in sets:
        extra = f" (소명 기한 {sets['explanation_due']})"
    elif "correction_due" in sets:
        extra = f" (시정 기한 {sets['correction_due']})"
    conn.execute("INSERT INTO case_events(case_id, user_id, type, from_status, to_status, note) VALUES (?,?,?,?,?,?)",
                 (case_id, user["id"], "STATUS", cur, to, (note or "") + extra))
    audit.log(conn, user["id"], "case.transition", "case", case_id, {"from": cur, "to": to}, ip)
    return get_case(conn, case_id)


def add_event(conn, case_id: int, user_id: int, type_: str, note: str) -> None:
    conn.execute("INSERT INTO case_events(case_id, user_id, type, note) VALUES (?,?,?,?)", (case_id, user_id, type_, note))
