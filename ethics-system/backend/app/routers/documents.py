"""공문: 양식 → 자동 작성(미리보기) → 저장 → 결재 → 발송(메일 또는 수동 기록) → .docx"""
import json
import re
from datetime import date, datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .. import audit, db
from ..deps import client_ip, current_user, get_db, require_admin, require_staff
from ..services import case_service, doc_templates, docx_export, mailer, workflow
from ..services.doc_templates import COMMITTEE_NAMES, kdate, kdatetime
from ..services.reg_parser import cite

router = APIRouter(prefix="/api", tags=["documents"])


class PreviewIn(BaseModel):
    template_code: str
    case_id: int | None = None
    meeting_id: int | None = None
    extra: dict[str, str] = Field(default_factory=dict)


class DocIn(BaseModel):
    template_code: str | None = None
    case_id: int | None = None
    meeting_id: int | None = None
    doc_no: str | None = None
    subject: str = Field(min_length=1, max_length=300)
    recipient: str | None = None
    recipient_email: str | None = None
    body: str = Field(min_length=1)


class DocUpdate(BaseModel):
    doc_no: str | None = None
    subject: str | None = None
    recipient: str | None = None
    recipient_email: str | None = None
    body: str | None = None


class ApproveIn(BaseModel):
    note: str = Field(min_length=2, max_length=500)   # 결재권자·결재일 등


class SendIn(BaseModel):
    method: str = Field(pattern="^(SMTP|MANUAL)$")
    sent_at: str | None = None       # MANUAL: 실제 발송 일시
    sent_ref: str | None = None      # MANUAL: 그룹웨어 메일 제목/Message-ID/등기번호 등
    attach_docx: bool = True


class TemplateUpdate(BaseModel):
    name: str
    subject: str
    body: str


@router.get("/templates")
def list_templates(user=Depends(current_user), conn=Depends(get_db)):
    return db.rows(conn.execute("SELECT * FROM templates ORDER BY category, rowid"))


@router.put("/templates/{code}")
def update_template(code: str, body: TemplateUpdate, request: Request, admin=Depends(require_admin), conn=Depends(get_db)):
    if not conn.execute("SELECT 1 FROM templates WHERE code=?", (code,)).fetchone():
        raise HTTPException(404, "양식을 찾을 수 없습니다.")
    conn.execute("UPDATE templates SET name=?, subject=?, body=?, updated_at=datetime('now','localtime') WHERE code=?",
                 (body.name, body.subject, body.body, code))
    audit.log(conn, admin["id"], "template.update", "template", code, None, client_ip(request))
    return {"ok": True}


@router.post("/templates/{code}/reset")
def reset_template(code: str, admin=Depends(require_admin), conn=Depends(get_db)):
    t = next((t for t in doc_templates.DEFAULT_TEMPLATES if t["code"] == code), None)
    if not t:
        raise HTTPException(404, "기본 양식이 없습니다.")
    conn.execute("UPDATE templates SET name=?, subject=?, body=?, updated_at=datetime('now','localtime') WHERE code=?",
                 (t["name"], t["subject"], t["body"], code))
    return {"ok": True}


def _compact(d: str) -> str:
    return d.replace("-", ".")


def _case_values(conn, case: dict, settings: dict) -> dict:
    arts = db.rows(conn.execute(
        """SELECT a.*, ca.reason FROM case_articles ca JOIN articles a ON a.id=ca.article_id
           WHERE ca.case_id=? ORDER BY a.source, a.sort_order""", (case["id"],)))
    confirmed = db.rows(conn.execute(
        "SELECT * FROM ad_findings WHERE case_id=? AND (decision='CONFIRMED') ORDER BY id", (case["id"],)))
    pending = db.rows(conn.execute(
        "SELECT * FROM ad_findings WHERE case_id=? AND decision IS NULL ORDER BY id", (case["id"],)))
    findings = confirmed or pending
    evidence = db.rows(conn.execute("SELECT * FROM evidence WHERE case_id=? ORDER BY id", (case["id"],)))

    violation_lines = []
    for i, f in enumerate(findings):
        refs = json.loads(f["article_refs"])
        ref_txt = ", ".join(f"{r['article_no']}{r['item']}" for r in refs[:2])
        violation_lines.append(f"    ({i + 1}) '{f['matched_text']}' 표기 — {f['rule_label']} ({ref_txt})")
    if not violation_lines and case.get("facts"):
        violation_lines.append(f"    (1) {case['facts'].strip()[:400]}")
    rule_lines = [f"    ({i + 1}) {cite(a)}" for i, a in enumerate(arts)]
    sources = sorted({a["source_name"] for a in arts})
    ev = [f"{e['captured_at']} {e['url'] or e['file_name'] or '자료'}" for e in evidence]

    contact_owner = settings.get("ad_case_owner") if case["case_type"] == "AD" else settings.get("ethics_case_owner")
    values = {
        "case_no": case["case_no"],
        "case_type_label": "광고" if case["case_type"] == "AD" else "윤리",
        "respondent_office": case.get("respondent_office"),
        "respondent_name": case.get("respondent_name"),
        "respondent_reg_no": case.get("respondent_reg_no"),
        "complainant_name": case.get("complainant_name"),
        "received_date": kdate(case.get("received_at")),
        "explanation_due": kdate(case.get("explanation_due")) or kdate(workflow.add_days(None, int(settings.get("explanation_days", 14)))),
        "correction_due": kdate(case.get("correction_due")) or kdate(workflow.add_days(None, int(settings.get("correction_days", 30)))),
        "violation_lines": "\n".join(violation_lines),
        "rule_lines": "\n".join(rule_lines),
        "applied_rules": "·".join(f"「{s}」" for s in sources) if sources else None,
        "evidence_summary": (f"{len(ev)}건 (" + "; ".join(ev[:3]) + (" 외" if len(ev) > 3 else "") + ")") if ev else None,
        "source_phrase": {"MONITORING": "광고 모니터링 결과", "HOMEPAGE": "홈페이지를 통해 접수된 민원과 관련하여",
                          "PHONE": "유선으로 접수된 민원과 관련하여", "EMAIL": "전자우편으로 접수된 민원과 관련하여"}.get(case["source"], "접수된 민원과 관련하여"),
        "basis_phrase": "「변리사 광고에 관한 규정」 제12조제1항에 따라" if case["case_type"] == "AD" else "「윤리위원회 운영 규정」 제6조에 따라",
        "closed_reason": case.get("closed_reason"),
        "closed_date": kdate(date.today().isoformat()) if case["status"] == "CLOSED" else None,
        "contact_name": contact_owner,
        "recipient": case.get("respondent_office"),
        "history_summary": None,
    }
    events = db.rows(conn.execute("SELECT ts, to_status, note FROM case_events WHERE case_id=? AND type='STATUS' ORDER BY id", (case["id"],)))
    if events:
        values["history_summary"] = "; ".join(f"{e['ts'][:10]} {workflow.STATUSES.get(e['to_status'], '')}" for e in events)
    meeting = db.one(conn.execute(
        """SELECT m.*, i.decision, i.decision_note FROM meeting_items i JOIN meetings m ON m.id=i.meeting_id
           WHERE i.case_id=? ORDER BY m.scheduled_at DESC LIMIT 1""", (case["id"],)))
    if meeting:
        values.update({
            "committee_name": COMMITTEE_NAMES.get(meeting["committee"]),
            "meeting_date": kdatetime(meeting["scheduled_at"]),
            "meeting_location": meeting["location"],
            "decision_date": kdate(meeting["scheduled_at"]),
            "decision_text": meeting["decision_note"],
        })
    else:
        values["committee_name"] = "광고심사위원회" if case["case_type"] == "AD" else "윤리위원회"
    return values


def _meeting_values(conn, meeting: dict) -> dict:
    items = db.rows(conn.execute("SELECT * FROM meeting_items WHERE meeting_id=? ORDER BY seq", (meeting["id"],)))
    return {
        "committee_name": COMMITTEE_NAMES.get(meeting["committee"]),
        "meeting_title": meeting["title"],
        "meeting_date": kdatetime(meeting["scheduled_at"]),
        "meeting_location": meeting["location"],
        "agenda_lines": "\n".join(f"    ({it['seq']}) 제{it['seq']}호 안건: {it['title']}" for it in items),
        "recipient": f"{COMMITTEE_NAMES.get(meeting['committee'])} 위원",
    }


def build(conn, template_code: str, case_id: int | None, meeting_id: int | None, extra: dict) -> dict:
    t = db.one(conn.execute("SELECT * FROM templates WHERE code=?", (template_code,)))
    if not t:
        raise HTTPException(404, "양식을 찾을 수 없습니다.")
    settings = case_service.get_settings(conn)
    values = {
        "dept_name": settings.get("dept_name"), "contact_phone": settings.get("contact_phone"),
        "contact_email": settings.get("contact_email"), "approval_line": settings.get("approval_line"),
        "cooperation_line": settings.get("cooperation_line"),
        "issue_date_compact": _compact(date.today().isoformat()),
        "opinion_due": kdate(workflow.add_days(None, 7)), "reply_due": kdate(workflow.add_days(None, 5)),
        "supplement_due": kdate(workflow.add_days(None, 7)),
    }
    case = None
    if case_id:
        case = case_service.get_case(conn, case_id)
        values.update({k: v for k, v in _case_values(conn, case, settings).items() if v is not None})
    if meeting_id:
        m = db.one(conn.execute("SELECT * FROM meetings WHERE id=?", (meeting_id,)))
        if not m:
            raise HTTPException(404, "회의를 찾을 수 없습니다.")
        values.update({k: v for k, v in _meeting_values(conn, m).items() if v})
    values.update({k: v for k, v in extra.items() if v is not None and str(v).strip()})
    values.setdefault("doc_no", None)
    subject, miss1 = doc_templates.render(t["subject"], values)
    values["subject"] = subject
    body, miss2 = doc_templates.render(t["body"], values)
    missing = list(dict.fromkeys(miss1 + miss2))
    recipient_email = None
    if case:
        recipient_email = case.get("complainant_contact") if template_code in ("SUPPLEMENT_REQUEST", "COMPLAINANT_RESULT") else case.get("respondent_email")
        if recipient_email and "@" not in recipient_email:
            recipient_email = None
    return {"template_code": template_code, "subject": subject, "body": body, "missing": missing,
            "recipient": values.get("recipient"), "recipient_email": recipient_email}


@router.post("/documents/preview")
def preview(body: PreviewIn, user=Depends(current_user), conn=Depends(get_db)):
    return build(conn, body.template_code, body.case_id, body.meeting_id, body.extra)


@router.get("/documents")
def list_documents(case_id: int | None = None, status: str | None = None, user=Depends(current_user), conn=Depends(get_db)):
    where, args = [], []
    if case_id:
        where.append("d.case_id=?"); args.append(case_id)
    if status:
        where.append("d.status=?"); args.append(status)
    w = ("WHERE " + " AND ".join(where)) if where else ""
    return db.rows(conn.execute(
        f"""SELECT d.id, d.case_id, d.meeting_id, d.template_code, d.doc_no, d.subject, d.recipient, d.status,
                   d.sent_at, d.sent_via, d.created_at, c.case_no FROM documents d LEFT JOIN cases c ON c.id=d.case_id {w}
            ORDER BY d.id DESC LIMIT 300""", args))


@router.post("/documents")
def create_document(body: DocIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    if body.case_id:
        case_service.get_case(conn, body.case_id)
    with db.transaction(conn):
        did = conn.execute(
            """INSERT INTO documents(case_id, meeting_id, template_code, doc_no, subject, recipient, recipient_email, body, created_by)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (body.case_id, body.meeting_id, body.template_code, body.doc_no, body.subject, body.recipient,
             body.recipient_email, body.body, user["id"])).lastrowid
        if body.case_id:
            case_service.add_event(conn, body.case_id, user["id"], "DOC", f"공문 작성(초안): {body.subject}")
        audit.log(conn, user["id"], "document.create", "document", did, None, client_ip(request))
    return {"id": did}


def _get_doc(conn, did: int) -> dict:
    d = db.one(conn.execute("SELECT * FROM documents WHERE id=?", (did,)))
    if not d:
        raise HTTPException(404, "공문을 찾을 수 없습니다.")
    return d


@router.get("/documents/{did}")
def get_document(did: int, user=Depends(current_user), conn=Depends(get_db)):
    d = _get_doc(conn, did)
    d["missing"] = re.findall(r"\{\{확인 필요: ([^}]+)\}\}", d["body"])
    d["smtp_configured"] = mailer.configured()
    return d


@router.put("/documents/{did}")
def update_document(did: int, body: DocUpdate, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    d = _get_doc(conn, did)
    if d["status"] != "DRAFT":
        raise HTTPException(409, "결재 또는 발송된 공문은 수정할 수 없습니다. 새 공문으로 작성하세요.")
    data = body.model_dump(exclude_unset=True)
    if data:
        conn.execute(f"UPDATE documents SET {', '.join(k + '=?' for k in data)}, updated_at=datetime('now','localtime') WHERE id=?",
                     (*data.values(), did))
        audit.log(conn, user["id"], "document.update", "document", did, list(data), client_ip(request))
    return {"ok": True}


@router.post("/documents/{did}/approve")
def approve_document(did: int, body: ApproveIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    d = _get_doc(conn, did)
    if d["status"] != "DRAFT":
        raise HTTPException(409, "초안 상태에서만 결재 처리할 수 있습니다.")
    missing = re.findall(r"\{\{확인 필요: ([^}]+)\}\}", d["body"] + d["subject"])
    if missing:
        raise HTTPException(400, f"확인 필요 항목이 남아 있습니다: {', '.join(dict.fromkeys(missing))}")
    if not d["doc_no"]:
        raise HTTPException(400, "시행번호를 입력한 뒤 결재 처리하세요.")
    with db.transaction(conn):
        conn.execute("UPDATE documents SET status='APPROVED', approver_note=?, approved_by=?, approved_at=datetime('now','localtime') WHERE id=?",
                     (body.note, user["id"], did))
        if d["case_id"]:
            case_service.add_event(conn, d["case_id"], user["id"], "DOC", f"공문 결재 완료: {d['subject']} ({body.note})")
        audit.log(conn, user["id"], "document.approve", "document", did, body.note, client_ip(request))
    return {"ok": True}


@router.post("/documents/{did}/send")
def send_document(did: int, body: SendIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    d = _get_doc(conn, did)
    if d["status"] != "APPROVED":
        raise HTTPException(409, "결재 완료된 공문만 발송할 수 있습니다.")
    if body.method == "SMTP":
        if not d["recipient_email"]:
            raise HTTPException(400, "수신자 메일 주소가 없습니다.")
        attach = (f"{d['doc_no'] or '공문'}.docx", docx_export.text_to_docx(d["body"])) if body.attach_docx else None
        try:
            ref = mailer.send(d["recipient_email"], d["subject"], d["body"], attach)
        except mailer.MailError as e:
            raise HTTPException(502, str(e))
        sent_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        if not body.sent_ref or not body.sent_at:
            raise HTTPException(400, "수동 기록 시 실제 발송 일시와 발송 근거(메일 제목·Message-ID·등기번호 등)를 입력하세요.")
        ref, sent_at = body.sent_ref, body.sent_at
    with db.transaction(conn):
        conn.execute("UPDATE documents SET status='SENT', sent_at=?, sent_via=?, sent_ref=? WHERE id=?",
                     (sent_at, body.method, ref, did))
        if d["case_id"]:
            case_service.add_event(conn, d["case_id"], user["id"], "MAIL",
                                   f"공문 발송({'메일 자동' if body.method == 'SMTP' else '수동 기록'}): {d['subject']} → "
                                   f"{d['recipient_email'] or d['recipient'] or '-'} / {sent_at} / 근거 {ref}")
        audit.log(conn, user["id"], "document.send", "document", did, {"method": body.method, "ref": ref}, client_ip(request))
    return {"ok": True, "sent_ref": ref}


@router.post("/documents/{did}/cancel")
def cancel_document(did: int, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    d = _get_doc(conn, did)
    if d["status"] == "SENT":
        raise HTTPException(409, "발송된 공문은 취소할 수 없습니다(기록 보존).")
    conn.execute("UPDATE documents SET status='CANCELLED' WHERE id=?", (did,))
    audit.log(conn, user["id"], "document.cancel", "document", did, None, client_ip(request))
    return {"ok": True}


@router.get("/documents/{did}/docx")
def document_docx(did: int, user=Depends(current_user), conn=Depends(get_db)):
    d = _get_doc(conn, did)
    data = docx_export.text_to_docx(d["body"])
    name = f"{d['doc_no'] or 'draft'}_{d['subject'][:40]}.docx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})
