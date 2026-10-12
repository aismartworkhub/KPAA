"""사건(민원·모니터링) 관리, 대시보드, 근거 분석."""
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .. import audit, db
from ..deps import client_ip, current_user, get_db, require_staff
from ..services import case_service, llm, matcher, workflow
from ..services.reg_parser import cite

router = APIRouter(prefix="/api", tags=["cases"])

EDITABLE = ["title", "priority", "respondent_office", "respondent_name", "respondent_reg_no", "respondent_email",
            "respondent_is_member", "complainant_name", "complainant_contact", "facts", "review_opinion",
            "explanation_summary", "violation_date", "assignee_id", "explanation_due", "correction_due",
            "objection_due"]


class CaseIn(BaseModel):
    case_type: str = Field(pattern="^(AD|ETHICS)$")
    source: str = Field(pattern="^(MONITORING|HOMEPAGE|PHONE|EMAIL|OTHER)$")
    title: str = Field(min_length=2, max_length=200)
    priority: str = Field(default="NORMAL", pattern="^(NORMAL|SERIOUS)$")
    respondent_office: str | None = None
    respondent_name: str | None = None
    respondent_reg_no: str | None = None
    respondent_email: str | None = None
    respondent_is_member: bool = True
    complainant_name: str | None = None
    complainant_contact: str | None = None
    facts: str | None = None
    violation_date: str | None = None
    received_at: str | None = None
    assignee_id: int | None = None


class CasePatch(BaseModel):
    title: str | None = None
    priority: str | None = Field(default=None, pattern="^(NORMAL|SERIOUS)$")
    respondent_office: str | None = None
    respondent_name: str | None = None
    respondent_reg_no: str | None = None
    respondent_email: str | None = None
    respondent_is_member: bool | None = None
    complainant_name: str | None = None
    complainant_contact: str | None = None
    facts: str | None = None
    review_opinion: str | None = None
    explanation_summary: str | None = None
    violation_date: str | None = None
    assignee_id: int | None = None
    explanation_due: str | None = None
    correction_due: str | None = None
    objection_due: str | None = None


class TransitionIn(BaseModel):
    to: str
    note: str | None = None
    due_date: str | None = None


class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=5000)


class LinkArticleIn(BaseModel):
    article_id: int
    reason: str | None = None


class LinkPrecedentIn(BaseModel):
    precedent_id: int
    note: str | None = None


class AnalyzeIn(BaseModel):
    use_ai: bool = False
    facts: str | None = None


class FindingPatch(BaseModel):
    decision: str | None = Field(default=None, pattern="^(CONFIRMED|REJECTED)$")


def _valid_date(v: str | None, label: str):
    if v:
        try:
            date.fromisoformat(v[:10])
        except ValueError:
            raise HTTPException(400, f"{label} 형식이 올바르지 않습니다(YYYY-MM-DD).")


def _decorate(c: dict, settings: dict) -> dict:
    c["status_label"] = workflow.STATUSES.get(c["status"], c["status"])
    c["type_label"] = workflow.CASE_TYPES.get(c["case_type"], c["case_type"])
    c["source_label"] = workflow.SOURCES.get(c["source"], c["source"])
    c["alerts"] = workflow.alerts_for(c, settings)
    return c


@router.get("/meta")
def meta(user=Depends(current_user), conn=Depends(get_db)):
    return {
        "statuses": workflow.STATUSES, "transitions": workflow.TRANSITIONS, "note_required": workflow.NOTE_REQUIRED,
        "sources": workflow.SOURCES, "case_types": workflow.CASE_TYPES,
        "settings": case_service.get_settings(conn), "ai_available": llm.available(),
        "users": db.rows(conn.execute("SELECT id, name, role FROM users WHERE active=1 ORDER BY name")),
    }


@router.get("/dashboard")
def dashboard(user=Depends(current_user), conn=Depends(get_db)):
    settings = case_service.get_settings(conn)
    by_status = {r["status"]: r["n"] for r in conn.execute("SELECT status, COUNT(*) n FROM cases GROUP BY status")}
    by_type = {r["case_type"]: r["n"] for r in conn.execute(
        "SELECT case_type, COUNT(*) n FROM cases WHERE status<>'CLOSED' GROUP BY case_type")}
    open_cases = db.rows(conn.execute(
        "SELECT c.*, u.name AS assignee_name FROM cases c LEFT JOIN users u ON u.id=c.assignee_id WHERE status<>'CLOSED'"))
    alerts = []
    for c in open_cases:
        for a in workflow.alerts_for(c, settings):
            alerts.append({**a, "case_id": c["id"], "case_no": c["case_no"], "title": c["title"]})
    order = {"danger": 0, "warn": 1, "info": 2}
    alerts.sort(key=lambda a: order[a["level"]])
    recent = db.rows(conn.execute(
        """SELECT e.*, c.case_no, c.title, u.name AS user_name FROM case_events e
           JOIN cases c ON c.id=e.case_id LEFT JOIN users u ON u.id=e.user_id ORDER BY e.id DESC LIMIT 15"""))
    unassigned_evidence = conn.execute("SELECT COUNT(*) FROM evidence WHERE case_id IS NULL").fetchone()[0]
    upcoming = db.rows(conn.execute(
        "SELECT id, committee, title, scheduled_at, status FROM meetings WHERE status IN ('PLANNED','HELD','MINUTES_DRAFT') ORDER BY scheduled_at LIMIT 5"))
    drafts = conn.execute("SELECT COUNT(*) FROM documents WHERE status IN ('DRAFT','APPROVED')").fetchone()[0]
    return {"by_status": by_status, "by_type": by_type, "alerts": alerts, "recent": recent,
            "open_count": len(open_cases), "unassigned_evidence": unassigned_evidence,
            "upcoming_meetings": upcoming, "unsent_documents": drafts, "statuses": workflow.STATUSES}


@router.get("/cases")
def list_cases(status: str | None = None, case_type: str | None = None, q: str | None = None,
               assignee_id: int | None = None, include_closed: bool = True, page: int = 1, size: int = 50,
               user=Depends(current_user), conn=Depends(get_db)):
    where, args = [], []
    if status:
        where.append("c.status=?"); args.append(status)
    elif not include_closed:
        where.append("c.status<>'CLOSED'")
    if case_type:
        where.append("c.case_type=?"); args.append(case_type)
    if assignee_id:
        where.append("c.assignee_id=?"); args.append(assignee_id)
    if q:
        like = f"%{q}%"
        where.append("(c.case_no LIKE ? OR c.title LIKE ? OR c.respondent_office LIKE ? OR c.respondent_name LIKE ? OR c.facts LIKE ?)")
        args += [like] * 5
    w = ("WHERE " + " AND ".join(where)) if where else ""
    size = max(1, min(size, 200))
    total = conn.execute(f"SELECT COUNT(*) FROM cases c {w}", args).fetchone()[0]
    items = db.rows(conn.execute(
        f"""SELECT c.*, u.name AS assignee_name FROM cases c LEFT JOIN users u ON u.id=c.assignee_id {w}
            ORDER BY c.id DESC LIMIT ? OFFSET ?""", (*args, size, (max(page, 1) - 1) * size)))
    settings = case_service.get_settings(conn)
    return {"total": total, "items": [_decorate(c, settings) for c in items]}


@router.post("/cases")
def create_case(body: CaseIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    _valid_date(body.violation_date, "위반일")
    _valid_date(body.received_at, "접수일")
    with db.transaction(conn):
        no = workflow.next_case_no(conn, body.case_type)
        data = body.model_dump()
        data["respondent_is_member"] = 1 if body.respondent_is_member else 0
        data["received_at"] = body.received_at or date.today().isoformat()
        cols = list(data.keys())
        cid = conn.execute(
            f"INSERT INTO cases(case_no, created_by, {', '.join(cols)}) VALUES (?,?,{','.join('?' * len(cols))})",
            (no, user["id"], *data.values())).lastrowid
        conn.execute("INSERT INTO case_events(case_id, user_id, type, to_status, note) VALUES (?,?,?,?,?)",
                     (cid, user["id"], "CREATED", "RECEIVED", f"{workflow.SOURCES[body.source]} 접수"))
        audit.log(conn, user["id"], "case.create", "case", cid, {"case_no": no}, client_ip(request))
    return {"id": cid, "case_no": no}


@router.get("/cases/{cid}")
def get_case(cid: int, user=Depends(current_user), conn=Depends(get_db)):
    c = case_service.get_case(conn, cid)
    settings = case_service.get_settings(conn)
    _decorate(c, settings)
    c["allowed_transitions"] = [{"to": t, "label": workflow.STATUSES[t], "note_required": workflow.note_requirement(c["status"], t)}
                                for t in workflow.TRANSITIONS.get(c["status"], [])]
    c["events"] = db.rows(conn.execute(
        "SELECT e.*, u.name AS user_name FROM case_events e LEFT JOIN users u ON u.id=e.user_id WHERE case_id=? ORDER BY e.id", (cid,)))
    c["evidence"] = db.rows(conn.execute("SELECT * FROM evidence WHERE case_id=? ORDER BY id", (cid,)))
    findings = db.rows(conn.execute("SELECT * FROM ad_findings WHERE case_id=? ORDER BY id", (cid,)))
    for f in findings:
        f["refs"] = json.loads(f.pop("article_refs"))
    c["findings"] = findings
    arts = db.rows(conn.execute(
        """SELECT a.*, ca.reason FROM case_articles ca JOIN articles a ON a.id=ca.article_id
           WHERE ca.case_id=? ORDER BY a.source, a.sort_order""", (cid,)))
    for a in arts:
        a["citation"] = cite(a)
    c["articles"] = arts
    c["precedents"] = db.rows(conn.execute(
        """SELECT p.*, cp.note FROM case_precedents cp JOIN precedents p ON p.id=cp.precedent_id WHERE cp.case_id=?""", (cid,)))
    c["documents"] = db.rows(conn.execute(
        "SELECT id, template_code, doc_no, subject, status, sent_at, created_at FROM documents WHERE case_id=? ORDER BY id", (cid,)))
    c["meetings"] = db.rows(conn.execute(
        """SELECT m.id, m.title, m.committee, m.scheduled_at, i.decision FROM meeting_items i JOIN meetings m ON m.id=i.meeting_id
           WHERE i.case_id=? ORDER BY m.scheduled_at""", (cid,)))
    return c


@router.patch("/cases/{cid}")
def update_case(cid: int, body: CasePatch, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    case_service.get_case(conn, cid)
    data = body.model_dump(exclude_unset=True)
    for k in ("violation_date", "explanation_due", "correction_due", "objection_due"):
        _valid_date(data.get(k), k)
    if "respondent_is_member" in data and data["respondent_is_member"] is not None:
        data["respondent_is_member"] = 1 if data["respondent_is_member"] else 0
    data = {k: v for k, v in data.items() if k in EDITABLE}
    if not data:
        return {"ok": True}
    with db.transaction(conn):
        conn.execute(f"UPDATE cases SET {', '.join(k + '=?' for k in data)}, updated_at=datetime('now','localtime') WHERE id=?",
                     (*data.values(), cid))
        audit.log(conn, user["id"], "case.update", "case", cid, list(data.keys()), client_ip(request))
    return {"ok": True}


@router.post("/cases/{cid}/transition")
def transition(cid: int, body: TransitionIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    _valid_date(body.due_date, "기한")
    with db.transaction(conn):
        c = case_service.transition(conn, cid, body.to, body.note, user, body.due_date, client_ip(request))
    return {"ok": True, "status": c["status"]}


@router.post("/cases/{cid}/notes")
def add_note(cid: int, body: NoteIn, user=Depends(require_staff), conn=Depends(get_db)):
    case_service.get_case(conn, cid)
    case_service.add_event(conn, cid, user["id"], "NOTE", body.note)
    return {"ok": True}


@router.post("/cases/{cid}/articles")
def link_article(cid: int, body: LinkArticleIn, user=Depends(require_staff), conn=Depends(get_db)):
    case_service.get_case(conn, cid)
    art = db.one(conn.execute("SELECT * FROM articles WHERE id=?", (body.article_id,)))
    if not art:
        raise HTTPException(404, "조문을 찾을 수 없습니다.")
    with db.transaction(conn):
        conn.execute("INSERT OR REPLACE INTO case_articles(case_id, article_id, reason, added_by) VALUES (?,?,?,?)",
                     (cid, body.article_id, body.reason, user["id"]))
        case_service.add_event(conn, cid, user["id"], "ARTICLE", f"적용 조문 추가: {cite(art)}")
    return {"ok": True}


@router.delete("/cases/{cid}/articles/{aid}")
def unlink_article(cid: int, aid: int, user=Depends(require_staff), conn=Depends(get_db)):
    conn.execute("DELETE FROM case_articles WHERE case_id=? AND article_id=?", (cid, aid))
    return {"ok": True}


@router.post("/cases/{cid}/precedents")
def link_precedent(cid: int, body: LinkPrecedentIn, user=Depends(require_staff), conn=Depends(get_db)):
    case_service.get_case(conn, cid)
    p = db.one(conn.execute("SELECT title FROM precedents WHERE id=?", (body.precedent_id,)))
    if not p:
        raise HTTPException(404, "선례를 찾을 수 없습니다.")
    with db.transaction(conn):
        conn.execute("INSERT OR REPLACE INTO case_precedents(case_id, precedent_id, note) VALUES (?,?,?)",
                     (cid, body.precedent_id, body.note))
        case_service.add_event(conn, cid, user["id"], "ARTICLE", f"참고 선례 추가: {p['title']}")
    return {"ok": True}


@router.delete("/cases/{cid}/precedents/{pid}")
def unlink_precedent(cid: int, pid: int, user=Depends(require_staff), conn=Depends(get_db)):
    conn.execute("DELETE FROM case_precedents WHERE case_id=? AND precedent_id=?", (cid, pid))
    return {"ok": True}


@router.patch("/findings/{fid}")
def decide_finding(fid: int, body: FindingPatch, user=Depends(require_staff), conn=Depends(get_db)):
    f = db.one(conn.execute("SELECT * FROM ad_findings WHERE id=?", (fid,)))
    if not f:
        raise HTTPException(404, "스크리닝 결과를 찾을 수 없습니다.")
    conn.execute("UPDATE ad_findings SET decision=? WHERE id=?", (body.decision, fid))
    return {"ok": True}


def _case_text(conn, c: dict) -> str:
    parts = [c["title"], c.get("facts") or ""]
    for e in conn.execute("SELECT ad_text, note FROM evidence WHERE case_id=?", (c["id"],)):
        parts += [e["ad_text"] or "", e["note"] or ""]
    return "\n".join(p for p in parts if p)


@router.post("/cases/{cid}/analyze")
def analyze_case(cid: int, body: AnalyzeIn, request: Request, user=Depends(current_user), conn=Depends(get_db)):
    c = case_service.get_case(conn, cid)
    text = body.facts or _case_text(conn, c)
    if not text.strip():
        raise HTTPException(400, "분석할 사실관계(또는 채증 광고문구)가 없습니다.")
    return run_analysis(conn, text, c["case_type"], body.use_ai, user, request, case_id=cid)


def run_analysis(conn, text: str, case_type: str | None, use_ai: bool, user, request, case_id: int | None = None) -> dict:
    result = matcher.match_articles(conn, text, top_k=8, case_type=case_type)
    result["precedents"] = matcher.match_precedents(conn, text, top_k=5)
    result["book_passages"] = matcher.search_chunks(conn, text, top_k=5)
    result["ai"] = None
    if use_ai:
        if not llm.available():
            result["ai_error"] = "AI 기능이 설정되지 않았습니다(ANTHROPIC_API_KEY 미설정). 규칙·검색 결과만 표시합니다."
        else:
            try:
                result["ai"] = llm.grounded_analysis(text, result["articles"], result["precedents"])
                audit.log(conn, user["id"], "ai.analysis", "case", case_id,
                          {"issues": len(result["ai"]["issues"]), "rejected": len(result["ai"]["rejected"])}, client_ip(request))
            except llm.LLMError as e:
                result["ai_error"] = str(e)
    return result
