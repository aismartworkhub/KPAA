"""위원회 회의: 일정·참석, 안건(사건 연결), 회의자료 자동 작성, 녹취 요약, 회의록, 결정 반영, 수당."""
import json
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .. import audit, db
from ..deps import client_ip, current_user, get_db, require_staff
from ..services import case_service, docx_export, llm, minutes, workflow
from ..services.doc_templates import COMMITTEE_NAMES, kdatetime
from ..services.reg_parser import cite

router = APIRouter(prefix="/api/meetings", tags=["meetings"])

DECISIONS = {"PENDING": "심의 중", "CORRECTION": "시정 요구", "WARNING": "경고", "DISCIPLINE_REFERRAL": "징계위원회 회부",
             "DISMISS": "종결", "DEFER": "보류", "EXTERNAL": "외부기관 이관"}
DECISION_TO_STATUS = {"CORRECTION": "CORRECTION_ORDERED", "DISCIPLINE_REFERRAL": "DISCIPLINE", "DISMISS": "CLOSED",
                      "WARNING": "CLOSED", "EXTERNAL": "EXTERNAL"}
CHECKLIST = ["위원장 일정 조율", "위원 참석 확인(투표)", "회의자료 사전 배포", "노트북·화상회의 시스템", "명패", "회규집",
             "녹화·녹음 준비", "회의록 작성", "위원장 전자결재", "수당 지급"]


class MeetingIn(BaseModel):
    committee: str = Field(pattern="^(AD_REVIEW|ETHICS|DISCIPLINE|STANDING_BOARD)$")
    title: str = Field(min_length=2, max_length=200)
    scheduled_at: str | None = None
    location: str | None = None
    members: list[dict] = Field(default_factory=list)


class MeetingPatch(BaseModel):
    title: str | None = None
    scheduled_at: str | None = None
    location: str | None = None
    status: str | None = Field(default=None, pattern="^(PLANNED|HELD|MINUTES_DRAFT|APPROVED|CANCELLED)$")
    members: list[dict] | None = None
    checklist: dict[str, bool] | None = None
    transcript: str | None = None
    minutes: str | None = None
    allowance_paid: bool | None = None


class ItemIn(BaseModel):
    case_id: int | None = None
    title: str | None = None


class ItemPatch(BaseModel):
    title: str | None = None
    decision: str | None = Field(default=None, pattern="^(PENDING|CORRECTION|WARNING|DISCIPLINE_REFERRAL|DISMISS|DEFER|EXTERNAL)$")
    decision_note: str | None = None
    vote_for: int | None = None
    vote_against: int | None = None


class SummarizeIn(BaseModel):
    transcript: str = Field(min_length=10, max_length=400000)
    use_ai: bool = False


def _get(conn, mid: int) -> dict:
    m = db.one(conn.execute("SELECT * FROM meetings WHERE id=?", (mid,)))
    if not m:
        raise HTTPException(404, "회의를 찾을 수 없습니다.")
    m["members_list"] = json.loads(m["members"] or "[]")
    m["checklist_map"] = json.loads(m["checklist"] or "{}")
    m["committee_label"] = COMMITTEE_NAMES.get(m["committee"])
    return m


def _items(conn, mid: int) -> list[dict]:
    items = db.rows(conn.execute(
        """SELECT i.*, c.case_no, c.status AS case_status, c.title AS case_title FROM meeting_items i
           LEFT JOIN cases c ON c.id=i.case_id WHERE meeting_id=? ORDER BY seq""", (mid,)))
    for it in items:
        it["decision_label"] = DECISIONS.get(it["decision"], it["decision"])
        it["case_status_label"] = workflow.STATUSES.get(it["case_status"]) if it["case_status"] else None
    return items


@router.get("")
def list_meetings(user=Depends(current_user), conn=Depends(get_db)):
    rows = db.rows(conn.execute(
        """SELECT m.*, (SELECT COUNT(*) FROM meeting_items i WHERE i.meeting_id=m.id) AS item_count
           FROM meetings m ORDER BY COALESCE(scheduled_at, created_at) DESC LIMIT 200"""))
    for m in rows:
        m["committee_label"] = COMMITTEE_NAMES.get(m["committee"])
        m.pop("transcript", None)
    return rows


@router.post("")
def create_meeting(body: MeetingIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    mid = conn.execute(
        "INSERT INTO meetings(committee, title, scheduled_at, location, members, checklist, created_by) VALUES (?,?,?,?,?,?,?)",
        (body.committee, body.title, body.scheduled_at, body.location, json.dumps(body.members, ensure_ascii=False),
         json.dumps({k: False for k in CHECKLIST}, ensure_ascii=False), user["id"])).lastrowid
    audit.log(conn, user["id"], "meeting.create", "meeting", mid, None, client_ip(request))
    return {"id": mid}


@router.get("/{mid}")
def get_meeting(mid: int, user=Depends(current_user), conn=Depends(get_db)):
    m = _get(conn, mid)
    m["items"] = _items(conn, mid)
    m["documents"] = db.rows(conn.execute("SELECT id, subject, status, sent_at FROM documents WHERE meeting_id=?", (mid,)))
    m["decisions"] = DECISIONS
    m["checklist_items"] = CHECKLIST
    m["candidates"] = db.rows(conn.execute(
        "SELECT id, case_no, title, status FROM cases WHERE status IN ('COMMITTEE','CORRECTION_ORDERED','DISCIPLINE','EXPLANATION_REVIEW') ORDER BY id"))
    return m


@router.patch("/{mid}")
def update_meeting(mid: int, body: MeetingPatch, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    _get(conn, mid)
    data = body.model_dump(exclude_unset=True)
    if "members" in data:
        data["members"] = json.dumps(data["members"], ensure_ascii=False)
    if "allowance_paid" in data:
        data["allowance_paid"] = 1 if data["allowance_paid"] else 0
    if "checklist" in data:
        data["checklist"] = json.dumps(data["checklist"], ensure_ascii=False)
    if data.get("status") == "APPROVED":
        data["approved_at"] = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if data:
        conn.execute(f"UPDATE meetings SET {', '.join(k + '=?' for k in data)}, updated_at=datetime('now','localtime') WHERE id=?",
                     (*data.values(), mid))
        audit.log(conn, user["id"], "meeting.update", "meeting", mid, [k for k in data if k != "transcript"], client_ip(request))
    return {"ok": True}


@router.post("/{mid}/items")
def add_item(mid: int, body: ItemIn, user=Depends(require_staff), conn=Depends(get_db)):
    _get(conn, mid)
    title = body.title
    if body.case_id:
        c = case_service.get_case(conn, body.case_id)
        title = title or f"{c['respondent_office'] or ''} {c['title']} ({c['case_no']})".strip()
        if conn.execute("SELECT 1 FROM meeting_items WHERE meeting_id=? AND case_id=?", (mid, body.case_id)).fetchone():
            raise HTTPException(409, "이미 안건으로 등록된 사건입니다.")
    if not title:
        raise HTTPException(400, "안건명 또는 사건을 지정하세요.")
    seq = conn.execute("SELECT COALESCE(MAX(seq),0)+1 FROM meeting_items WHERE meeting_id=?", (mid,)).fetchone()[0]
    iid = conn.execute("INSERT INTO meeting_items(meeting_id, case_id, seq, title) VALUES (?,?,?,?)",
                       (mid, body.case_id, seq, title)).lastrowid
    return {"id": iid}


@router.patch("/items/{iid}")
def update_item(iid: int, body: ItemPatch, user=Depends(require_staff), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM meeting_items WHERE id=?", (iid,)).fetchone():
        raise HTTPException(404, "안건을 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if data:
        conn.execute(f"UPDATE meeting_items SET {', '.join(k + '=?' for k in data)} WHERE id=?", (*data.values(), iid))
    return {"ok": True}


@router.delete("/items/{iid}")
def delete_item(iid: int, user=Depends(require_staff), conn=Depends(get_db)):
    conn.execute("DELETE FROM meeting_items WHERE id=?", (iid,))
    return {"ok": True}


def agenda_text(conn, m: dict) -> str:
    items = _items(conn, m["id"])
    lines = [f"{m['title']} 회의자료", "",
             f"일시: {kdatetime(m['scheduled_at']) or '-'}    장소: {m['location'] or '-'}", "",
             "※ 본 자료는 위원회 심의용 비공개 자료입니다(각 위원회 운영 규정상 비밀유지의무).", ""]
    for it in items:
        lines.append(f"[제{it['seq']}호 안건] {it['title']}")
        if not it["case_id"]:
            lines += ["", ""]
            continue
        c = case_service.get_case(conn, it["case_id"])
        arts = db.rows(conn.execute(
            "SELECT a.* FROM case_articles ca JOIN articles a ON a.id=ca.article_id WHERE ca.case_id=? ORDER BY a.source, a.sort_order",
            (c["id"],)))
        findings = db.rows(conn.execute(
            "SELECT * FROM ad_findings WHERE case_id=? AND (decision IS NULL OR decision='CONFIRMED')", (c["id"],)))
        precs = db.rows(conn.execute(
            "SELECT p.* FROM case_precedents cp JOIN precedents p ON p.id=cp.precedent_id WHERE cp.case_id=?", (c["id"],)))
        events = db.rows(conn.execute(
            "SELECT ts, type, to_status, note FROM case_events WHERE case_id=? AND type IN ('STATUS','MAIL') ORDER BY id", (c["id"],)))
        lines += [
            f"  1. 사건 개요: {c['case_no']} / {workflow.CASE_TYPES[c['case_type']]} / {workflow.SOURCES[c['source']]} 접수 {c['received_at']}",
            f"     피민원인: {c['respondent_office'] or '-'} {c['respondent_name'] or ''}" +
            ("" if c["respondent_is_member"] else " (미등록·비회원)"),
            "  2. 위반 사실",
            *[f"     - {ln}" for ln in (c["facts"] or "-").splitlines() if ln.strip()],
            *[f"     - 광고 표현 '{f['matched_text']}': {f['rule_label']}" for f in findings],
            "  3. 관련 규정",
            *([f"     - {cite(a)}" for a in arts] or ["     - (적용 조문 미지정)"]),
            "  4. 소명 내용",
            *[f"     - {ln}" for ln in (c["explanation_summary"] or "(소명서 미제출 또는 요약 미입력)").splitlines() if ln.strip()],
            "  5. 사무국 검토의견",
            *[f"     - {ln}" for ln in (c["review_opinion"] or "(미입력)").splitlines() if ln.strip()],
            "  6. 참고 선례",
            *([f"     - {p['title']} ({p['volume'] or ''} {p['case_ref'] or ''}) → {p['sanction_type'] or '-'}" for p in precs]
              or ["     - (연결된 선례 없음)"]),
            "  7. 처리 경과",
            *[f"     - {e['ts'][:10]} {workflow.STATUSES.get(e['to_status'], '') if e['type'] == 'STATUS' else '공문 발송'}"
              f"{(': ' + e['note'][:80]) if e['note'] else ''}" for e in events],
            "  8. 의결 요청 사항: 시정 요구 / 경고 / 징계위원회 회부 / 종결 중 의결", "",
        ]
    return "\n".join(lines)


@router.get("/{mid}/agenda")
def agenda(mid: int, user=Depends(current_user), conn=Depends(get_db)):
    m = _get(conn, mid)
    return {"text": agenda_text(conn, m)}


@router.get("/{mid}/agenda.docx")
def agenda_docx(mid: int, user=Depends(current_user), conn=Depends(get_db)):
    m = _get(conn, mid)
    data = docx_export.text_to_docx(agenda_text(conn, m))
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(m['title'] + '_회의자료.docx')}"})


@router.post("/{mid}/summarize")
def summarize(mid: int, body: SummarizeIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    m = _get(conn, mid)
    items = _items(conn, mid)
    agenda_titles = [f"제{i['seq']}호 {i['title']}" for i in items]
    conn.execute("UPDATE meetings SET transcript=?, updated_at=datetime('now','localtime') WHERE id=?", (body.transcript, mid))
    result = minutes.summarize(body.transcript, agenda_titles)
    if body.use_ai:
        if not llm.available():
            result["ai_error"] = "AI 기능이 설정되지 않았습니다. 규칙 기반 결과를 표시합니다."
        else:
            try:
                ai = llm.summarize_minutes(body.transcript, agenda_titles)
                result = {"method": "ai", "overview": ai["overview"], "speakers": ai["speakers"],
                          "resolutions": [{"speaker": "", "text": f"{r['agenda']}: {r['decision']} ({r['vote']})",
                                           "evidence_quote": r["evidence_quote"], "verified": r["verified"]} for r in ai["resolutions"]],
                          "follow_ups": [{"text": f} for f in ai["follow_ups"]], "agenda": agenda_titles,
                          "notice": "AI 요약입니다. '검증 실패' 표시된 의결사항은 녹취록에 근거 문장이 없으니 반드시 확인하세요."}
                audit.log(conn, user["id"], "ai.minutes", "meeting", mid, None, client_ip(request))
            except llm.LLMError as e:
                result["ai_error"] = str(e)
    result["draft"] = minutes.to_minutes_text(m, items, result)
    return result


@router.post("/{mid}/apply-decisions")
def apply_decisions(mid: int, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    """의결 결과를 사건 상태에 반영(위원회 상정 상태인 사건만)."""
    m = _get(conn, mid)
    items = _items(conn, mid)
    applied, skipped = [], []
    with db.transaction(conn):
        for it in items:
            target = DECISION_TO_STATUS.get(it["decision"])
            if not it["case_id"] or not target:
                continue
            c = case_service.get_case(conn, it["case_id"])
            if not workflow.can_transition(c["status"], target):
                skipped.append({"case_no": c["case_no"], "reason": f"현재 상태({workflow.STATUSES[c['status']]})에서 반영 불가"})
                continue
            note = f"{m['committee_label']} {(m['scheduled_at'] or '')[:10]} 의결: {DECISIONS[it['decision']]}"
            if it["vote_for"] is not None:
                note += f" (찬성 {it['vote_for']}, 반대 {it['vote_against'] or 0})"
            if it["decision_note"]:
                note += f" — {it['decision_note']}"
            case_service.transition(conn, c["id"], target, note, user, None, client_ip(request))
            applied.append({"case_no": c["case_no"], "to": workflow.STATUSES[target]})
    return {"applied": applied, "skipped": skipped}


@router.get("/{mid}/minutes.docx")
def minutes_docx(mid: int, user=Depends(current_user), conn=Depends(get_db)):
    m = _get(conn, mid)
    if not m["minutes"]:
        raise HTTPException(400, "저장된 회의록이 없습니다.")
    data = docx_export.text_to_docx(m["minutes"])
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(m['title'] + '_회의록.docx')}"})
