"""채증 자료 등록·광고 스크리닝·모니터링 지원."""
import csv
import io
import json
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .. import audit, db
from ..deps import client_ip, current_user, get_db, require_staff
from ..services import ad_rules, case_service, matcher, storage, workflow
from ..services.reg_parser import cite

router = APIRouter(prefix="/api", tags=["evidence"])

MONITOR_KEYWORDS = [
    ("최상급 표현", ["변리사 최고", "특허사무소 1위", "상표등록 업계 최초", "특허 국내 유일"]),
    ("결과 보장·성공률", ["상표등록 보장", "특허 등록률 %", "상표 등록 100%", "미등록시 환불 변리사"]),
    ("보수 관련", ["상표출원 최저가", "특허 출원 할인 이벤트", "상표등록 무료", "변리사 견적 비교"]),
    ("명칭·자격", ["국제변리사", "특허전문가 상담", "상표전문가 무료상담"]),
    ("결과 예측·플랫폼", ["상표 등록 가능성 AI 진단", "특허 등록 확률 예측", "변리사 매칭 플랫폼"]),
]


class ScreenIn(BaseModel):
    text: str = Field(min_length=1, max_length=50000)


class AssignIn(BaseModel):
    case_id: int


class CaseFromEvidenceIn(BaseModel):
    title: str | None = None
    respondent_name: str | None = None
    respondent_email: str | None = None


def _enrich(conn, findings: list[dict]) -> list[dict]:
    for f in findings:
        for r in f["refs"]:
            art = matcher.article_by_ref(conn, r["source"], r["article_no"])
            r["citation"] = (cite(art) if art else f"{r['source']} {r['article_no']}") + (f" {r['item']}" if r["item"] else "")
            r["article_id"] = art["id"] if art else None
            r["body"] = art["body"] if art else None
    return findings


def _store_findings(conn, case_id, evidence_id, findings):
    conn.execute("DELETE FROM ad_findings WHERE evidence_id=?", (evidence_id,))
    for f in findings:
        conn.execute(
            """INSERT INTO ad_findings(case_id, evidence_id, rule_code, rule_label, article_refs, matched_text, context, confidence)
               VALUES (?,?,?,?,?,?,?,?)""",
            (case_id, evidence_id, f["rule_code"], f["rule_label"],
             json.dumps([{k: r[k] for k in ("source", "article_no", "item")} for r in f["refs"]], ensure_ascii=False),
             f["matched_text"], f["context"], f["confidence"]))


@router.post("/screen")
def screen(body: ScreenIn, user=Depends(current_user), conn=Depends(get_db)):
    return {"findings": _enrich(conn, ad_rules.screen(body.text)),
            "notice": "규칙 기반 1차 스크리닝 결과입니다. 위반 여부는 담당자 검토와 위원회 심의로 확정합니다."}


@router.get("/screen/rules")
def rules(user=Depends(current_user)):
    return ad_rules.rule_catalog()


@router.get("/monitoring/keywords")
def monitoring_keywords(user=Depends(current_user)):
    out = []
    for group, words in MONITOR_KEYWORDS:
        out.append({"group": group, "queries": [{
            "q": w,
            "naver": f"https://search.naver.com/search.naver?query={quote(w)}",
            "naver_blog": f"https://search.naver.com/search.naver?ssc=tab.blog.all&query={quote(w)}",
            "google": f"https://www.google.com/search?q={quote(w)}",
            "daum": f"https://search.daum.net/search?q={quote(w)}",
            "instagram": f"https://www.instagram.com/explore/search/keyword/?q={quote(w)}",
        } for w in words]})
    return out


@router.post("/screen/batch")
async def screen_batch(file: UploadFile = File(...), save: bool = Form(False), request: Request = None,
                       user=Depends(current_user), conn=Depends(get_db)):
    """모니터링 결과 CSV 일괄 스크리닝. 열: url, office_name, ad_text (헤더 필수, UTF-8 또는 CP949)"""
    raw = await file.read()
    if len(raw) > 20 * 1024 * 1024:
        raise HTTPException(413, "CSV는 20MB 이하만 가능합니다.")
    text = None
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(400, "CSV 인코딩을 판별할 수 없습니다.")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "ad_text" not in [f.strip() for f in reader.fieldnames]:
        raise HTTPException(400, "CSV 머리행에 ad_text 열이 필요합니다(선택: url, office_name).")
    if save and user["role"] not in ("admin", "staff"):
        raise HTTPException(403, "조회 전용 계정은 저장할 수 없습니다.")
    results = []
    with db.transaction(conn):
        for i, row in enumerate(reader, start=1):
            row = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            ad_text = row.get("ad_text", "")
            if not ad_text:
                continue
            findings = ad_rules.screen(ad_text)
            item = {"row": i, "url": row.get("url"), "office_name": row.get("office_name"), "ad_text": ad_text[:300],
                    "finding_count": len(findings),
                    "max_confidence": findings[0]["confidence"] if findings else None,
                    "labels": sorted({f["rule_label"] for f in findings})}
            if save and findings:
                eid = conn.execute(
                    "INSERT INTO evidence(url, office_name, ad_text, captured_at, note, created_by) VALUES (?,?,?,?,?,?)",
                    (row.get("url"), row.get("office_name"), ad_text, date.today().isoformat(), "CSV 일괄 스크리닝", user["id"])).lastrowid
                _store_findings(conn, None, eid, findings)
                item["evidence_id"] = eid
            results.append(item)
        if save:
            audit.log(conn, user["id"], "evidence.batch", "evidence", None, {"rows": len(results)}, client_ip(request))
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, None: 3}
    results.sort(key=lambda r: (order[r["max_confidence"]], -r["finding_count"]))
    return {"total": len(results), "flagged": sum(1 for r in results if r["finding_count"]), "items": results}


@router.post("/evidence")
async def create_evidence(request: Request,
                          case_id: int | None = Form(None), url: str | None = Form(None),
                          office_name: str | None = Form(None), ad_text: str | None = Form(None),
                          captured_at: str | None = Form(None), note: str | None = Form(None),
                          file: UploadFile | None = File(None),
                          user=Depends(require_staff), conn=Depends(get_db)):
    if not (url or ad_text or (file and file.filename)):
        raise HTTPException(400, "URL, 광고 문구, 캡처 파일 중 하나 이상을 입력하세요.")
    if case_id:
        case_service.get_case(conn, case_id)
    meta = await storage.save_upload(file, "evidence") if file and file.filename else {}
    captured = captured_at or date.today().isoformat()
    with db.transaction(conn):
        eid = conn.execute(
            """INSERT INTO evidence(case_id, url, office_name, ad_text, captured_at, file_name, stored_path, mime, size, sha256, note, created_by)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (case_id, url, office_name, ad_text, captured, meta.get("file_name"), meta.get("stored_path"), meta.get("mime"),
             meta.get("size"), meta.get("sha256"), note, user["id"])).lastrowid
        findings = ad_rules.screen(ad_text or "")
        _store_findings(conn, case_id, eid, findings)
        if case_id:
            case_service.add_event(conn, case_id, user["id"], "EVIDENCE",
                                   f"채증 자료 등록 #{eid}" + (f" (SHA-256 {meta['sha256'][:16]}…)" if meta else "")
                                   + (f" — 위반 의심 {len(findings)}건" if findings else ""))
        audit.log(conn, user["id"], "evidence.create", "evidence", eid, {"case_id": case_id, "sha256": meta.get("sha256")},
                  client_ip(request))
    return {"id": eid, "findings": _enrich(conn, findings), "sha256": meta.get("sha256")}


@router.get("/evidence")
def list_evidence(unassigned: bool = False, q: str | None = None, user=Depends(current_user), conn=Depends(get_db)):
    where, args = [], []
    if unassigned:
        where.append("e.case_id IS NULL")
    if q:
        where.append("(e.office_name LIKE ? OR e.ad_text LIKE ? OR e.url LIKE ?)")
        args += [f"%{q}%"] * 3
    w = ("WHERE " + " AND ".join(where)) if where else ""
    items = db.rows(conn.execute(
        f"""SELECT e.*, c.case_no,
              (SELECT COUNT(*) FROM ad_findings f WHERE f.evidence_id=e.id) AS finding_count,
              (SELECT GROUP_CONCAT(DISTINCT f.rule_label) FROM ad_findings f WHERE f.evidence_id=e.id) AS labels
            FROM evidence e LEFT JOIN cases c ON c.id=e.case_id {w} ORDER BY e.id DESC LIMIT 300""", args))
    return items


@router.get("/evidence/{eid}")
def get_evidence(eid: int, user=Depends(current_user), conn=Depends(get_db)):
    e = db.one(conn.execute("SELECT * FROM evidence WHERE id=?", (eid,)))
    if not e:
        raise HTTPException(404, "채증 자료를 찾을 수 없습니다.")
    fs = db.rows(conn.execute("SELECT * FROM ad_findings WHERE evidence_id=?", (eid,)))
    for f in fs:
        f["refs"] = json.loads(f.pop("article_refs"))
    e["findings"] = _enrich(conn, fs)
    return e


@router.get("/evidence/{eid}/file")
def evidence_file(eid: int, request: Request, user=Depends(current_user), conn=Depends(get_db)):
    e = db.one(conn.execute("SELECT * FROM evidence WHERE id=?", (eid,)))
    if not e or not e["stored_path"]:
        raise HTTPException(404, "첨부 파일이 없습니다.")
    audit.log(conn, user["id"], "evidence.download", "evidence", eid, None, client_ip(request))
    inline = (e["mime"] or "").startswith("image/") or e["mime"] == "application/pdf"
    return FileResponse(storage.resolve(e["stored_path"]), media_type=e["mime"], filename=e["file_name"],
                        content_disposition_type="inline" if inline else "attachment")


@router.post("/evidence/{eid}/assign")
def assign_evidence(eid: int, body: AssignIn, user=Depends(require_staff), conn=Depends(get_db)):
    e = db.one(conn.execute("SELECT * FROM evidence WHERE id=?", (eid,)))
    if not e:
        raise HTTPException(404, "채증 자료를 찾을 수 없습니다.")
    case_service.get_case(conn, body.case_id)
    with db.transaction(conn):
        conn.execute("UPDATE evidence SET case_id=? WHERE id=?", (body.case_id, eid))
        conn.execute("UPDATE ad_findings SET case_id=? WHERE evidence_id=?", (body.case_id, eid))
        case_service.add_event(conn, body.case_id, user["id"], "EVIDENCE", f"채증 자료 #{eid} 연결")
    return {"ok": True}


@router.post("/evidence/{eid}/create-case")
def case_from_evidence(eid: int, body: CaseFromEvidenceIn, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    e = db.one(conn.execute("SELECT * FROM evidence WHERE id=?", (eid,)))
    if not e:
        raise HTTPException(404, "채증 자료를 찾을 수 없습니다.")
    if e["case_id"]:
        raise HTTPException(409, "이미 사건에 연결된 자료입니다.")
    labels = [r["rule_label"] for r in conn.execute("SELECT DISTINCT rule_label FROM ad_findings WHERE evidence_id=?", (eid,))]
    title = body.title or f"{e['office_name'] or '미상 사무소'} 광고 — {', '.join(labels[:2]) or '규정 위반 의심'}"
    with db.transaction(conn):
        no = workflow.next_case_no(conn, "AD")
        facts = f"모니터링 중 확인한 광고({e['url'] or 'URL 미기재'}, {e['captured_at']} 채증).\n광고 문구: {e['ad_text'] or '-'}"
        cid = conn.execute(
            """INSERT INTO cases(case_no, case_type, source, title, respondent_office, respondent_name, respondent_email,
               facts, violation_date, received_at, created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (no, "AD", "MONITORING", title[:200], e["office_name"], body.respondent_name, body.respondent_email, facts,
             e["captured_at"], date.today().isoformat(), user["id"])).lastrowid
        conn.execute("UPDATE evidence SET case_id=? WHERE id=?", (cid, eid))
        conn.execute("UPDATE ad_findings SET case_id=? WHERE evidence_id=?", (cid, eid))
        conn.execute("INSERT INTO case_events(case_id, user_id, type, to_status, note) VALUES (?,?,?,?,?)",
                     (cid, user["id"], "CREATED", "RECEIVED", f"모니터링 채증 #{eid}로부터 사건 생성"))
        audit.log(conn, user["id"], "case.create_from_evidence", "case", cid, {"evidence_id": eid}, client_ip(request))
    return {"id": cid, "case_no": no}


@router.delete("/evidence/{eid}")
def delete_evidence(eid: int, request: Request, user=Depends(require_staff), conn=Depends(get_db)):
    e = db.one(conn.execute("SELECT * FROM evidence WHERE id=?", (eid,)))
    if not e:
        raise HTTPException(404, "채증 자료를 찾을 수 없습니다.")
    if e["case_id"] and user["role"] != "admin":
        raise HTTPException(403, "사건에 연결된 채증 자료는 관리자만 삭제할 수 있습니다(증거 보존).")
    with db.transaction(conn):
        conn.execute("DELETE FROM evidence WHERE id=?", (eid,))
        if e["case_id"]:
            case_service.add_event(conn, e["case_id"], user["id"], "EVIDENCE", f"채증 자료 #{eid} 삭제(관리자)")
        audit.log(conn, user["id"], "evidence.delete", "evidence", eid, {"sha256": e["sha256"], "file": e["file_name"]},
                  client_ip(request))
    # 원본 파일은 감사 목적상 즉시 지우지 않고 보존(백업 정책에 따라 정리)
    return {"ok": True}
