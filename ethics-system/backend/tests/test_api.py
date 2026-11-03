"""API 통합 테스트: 인증·보안, 사건 절차, 채증, 공문, 회의, 백업, AI 근거 검증."""
import io

from app.services import llm
from tests.conftest import ADMIN_PW, login


def make_case(client, h, **kw):
    body = {"case_type": "AD", "source": "MONITORING", "title": "테스트 광고 사건", "respondent_office": "가나특허",
            "respondent_name": "홍길동", "respondent_email": "a@example.com",
            "facts": "블로그에 '국내 최고', '등록률 99%' 표기"}
    body.update(kw)
    r = client.post("/api/cases", json=body, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


# ── 인증·보안 ──────────────────────────────────────────────
def test_requires_login(client):
    assert client.get("/api/cases").status_code == 401


def test_csrf_required_for_writes(client, admin):
    r = client.post("/api/cases", json={"case_type": "AD", "source": "OTHER", "title": "x1"})
    assert r.status_code == 403


def test_login_lockout(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    r = client.post("/api/auth/login", json={"username": "admin", "password": ADMIN_PW})
    assert r.status_code == 423


def test_viewer_cannot_write(client, admin):
    r = client.post("/api/users", json={"username": "viewer1", "name": "조회", "role": "viewer", "password": "Viewer!2345"}, headers=admin)
    assert r.status_code == 200
    client.cookies.clear()
    vh = login(client, "viewer1", "Viewer!2345")
    assert client.get("/api/cases").status_code == 200
    assert client.post("/api/cases", json={"case_type": "AD", "source": "OTHER", "title": "xx"}, headers=vh).status_code == 403


def test_password_policy_and_change(client, admin):
    assert client.post("/api/auth/password", json={"current_password": ADMIN_PW, "new_password": "short"}, headers=admin).status_code == 400
    assert client.post("/api/auth/password", json={"current_password": ADMIN_PW, "new_password": "Better!Pass2026"}, headers=admin).status_code == 200
    assert client.get("/api/auth/me").json()["user"]["must_change_pw"] == 0


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["x-frame-options"] == "DENY" and "default-src 'self'" in r.headers["content-security-policy"]


# ── 사건 절차 ─────────────────────────────────────────────
def test_case_workflow_rules(client, admin):
    cid = make_case(client, admin)
    # 건너뛰기 불가
    assert client.post(f"/api/cases/{cid}/transition", json={"to": "COMMITTEE"}, headers=admin).status_code == 409
    assert client.post(f"/api/cases/{cid}/transition", json={"to": "REVIEW"}, headers=admin).status_code == 200
    assert client.post(f"/api/cases/{cid}/transition", json={"to": "PENDING_APPROVAL"}, headers=admin).status_code == 200
    # 결재 사유 필수
    assert client.post(f"/api/cases/{cid}/transition", json={"to": "EXPLANATION_REQUESTED"}, headers=admin).status_code == 400
    r = client.post(f"/api/cases/{cid}/transition", json={"to": "EXPLANATION_REQUESTED", "note": "담당 이사 결재"}, headers=admin)
    assert r.status_code == 200
    c = client.get(f"/api/cases/{cid}").json()
    assert c["status"] == "EXPLANATION_REQUESTED" and c["explanation_due"]  # 기한 자동 설정(14일)
    assert [e["type"] for e in c["events"]].count("STATUS") == 3


def test_case_number_sequence(client, admin):
    a = client.post("/api/cases", json={"case_type": "ETHICS", "source": "EMAIL", "title": "윤리1"}, headers=admin).json()
    b = client.post("/api/cases", json={"case_type": "ETHICS", "source": "EMAIL", "title": "윤리2"}, headers=admin).json()
    assert a["case_no"].endswith("-0001") and b["case_no"].endswith("-0002") and a["case_no"].startswith("ETHICS-")


def test_analysis_without_ai(client, admin):
    cid = make_case(client, admin)
    r = client.post(f"/api/cases/{cid}/analyze", json={"use_ai": True}, headers=admin).json()
    cites = [a["citation"] for a in r["articles"]]
    assert any("제7조" in c for c in cites) and any("제8조의5" in c for c in cites)
    assert "ANTHROPIC_API_KEY" in r["ai_error"]   # 키 없으면 명확한 안내 후 규칙 결과 제공


def test_ethics_matching(client, admin):
    r = client.post("/api/articles/match", json={"facts": "변리사가 의뢰인의 비밀을 동의 없이 누설", "case_type": "ETHICS"}, headers=admin).json()
    top = r["articles"][:3]
    assert any(a["source"] == "ETHICS" and a["article_no"] == "제12조" for a in top)


# ── 채증 ──────────────────────────────────────────────────
def test_evidence_upload_hash_and_findings(client, admin):
    cid = make_case(client, admin)
    data = b"\x89PNG fake image bytes"
    r = client.post("/api/evidence", data={"case_id": str(cid), "ad_text": "등록 보장! 업계 최초"},
                    files={"file": ("cap.png", data, "image/png")}, headers=admin)
    assert r.status_code == 200
    import hashlib
    assert r.json()["sha256"] == hashlib.sha256(data).hexdigest()
    eid = r.json()["id"]
    f = client.get(f"/api/evidence/{eid}/file")
    assert f.status_code == 200 and f.content == data
    assert len(client.get(f"/api/cases/{cid}").json()["findings"]) >= 2


def test_evidence_rejects_bad_extension(client, admin):
    r = client.post("/api/evidence", data={"ad_text": "x"}, files={"file": ("evil.exe", b"MZ", "application/octet-stream")}, headers=admin)
    assert r.status_code == 400


def test_evidence_inbox_to_case(client, admin):
    r = client.post("/api/evidence", data={"ad_text": "상표 최저가 할인 쿠폰", "office_name": "다라특허"}, headers=admin)
    eid = r.json()["id"]
    assert any(e["id"] == eid for e in client.get("/api/evidence?unassigned=true").json())
    c = client.post(f"/api/evidence/{eid}/create-case", json={}, headers=admin).json()
    case = client.get(f"/api/cases/{c['id']}").json()
    assert case["source"] == "MONITORING" and case["evidence"][0]["id"] == eid


def test_batch_screen_csv(client, admin):
    csv_bytes = "url,office_name,ad_text\nhttps://a,가,국내 최고 변리사\nhttps://b,나,특허 출원 안내\n".encode("utf-8")
    r = client.post("/api/screen/batch", files={"file": ("m.csv", csv_bytes, "text/csv")}, data={"save": "true"}, headers=admin)
    j = r.json()
    assert j["total"] == 2 and j["flagged"] == 1


# ── 공문 ──────────────────────────────────────────────────
def test_document_lifecycle(client, admin):
    cid = make_case(client, admin)
    pv = client.post("/api/documents/preview", json={"template_code": "EXPLANATION_REQUEST", "case_id": cid}, headers=admin).json()
    assert "가나특허" in pv["body"] and "시행번호" in pv["missing"]
    did = client.post("/api/documents", json={"case_id": cid, "subject": pv["subject"], "body": pv["body"],
                                              "recipient_email": "a@example.com"}, headers=admin).json()["id"]
    # 확인 필요 항목 남으면 결재 불가
    assert client.post(f"/api/documents/{did}/approve", json={"note": "이사 결재"}, headers=admin).status_code == 400
    body = pv["body"].replace("{{확인 필요:", "[").replace("}}", "]")
    client.put(f"/api/documents/{did}", json={"body": body, "doc_no": "대한변리사회-1"}, headers=admin)
    assert client.post(f"/api/documents/{did}/approve", json={"note": "이사 결재"}, headers=admin).status_code == 200
    # 결재 후 수정 불가
    assert client.put(f"/api/documents/{did}", json={"body": "x"}, headers=admin).status_code == 409
    # SMTP 미설정 → 502, 수동 기록은 근거 필수
    assert client.post(f"/api/documents/{did}/send", json={"method": "SMTP"}, headers=admin).status_code == 502
    assert client.post(f"/api/documents/{did}/send", json={"method": "MANUAL"}, headers=admin).status_code == 400
    r = client.post(f"/api/documents/{did}/send", json={"method": "MANUAL", "sent_at": "2026-10-12 10:00:00", "sent_ref": "MSG-1"}, headers=admin)
    assert r.status_code == 200
    ev = client.get(f"/api/cases/{cid}").json()["events"]
    assert any(e["type"] == "MAIL" and "MSG-1" in e["note"] for e in ev)
    dx = client.get(f"/api/documents/{did}/docx")
    assert dx.status_code == 200 and dx.content[:2] == b"PK"


def test_smtp_send(client, admin, monkeypatch):
    from app import config
    from app.services import mailer
    monkeypatch.setattr(config, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(config, "SMTP_FROM", "ethics@kpaa.test")
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port, timeout): sent["host"] = host
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context): pass
        def login(self, u, p): pass
        def send_message(self, msg): sent["to"] = msg["To"]; sent["att"] = len(list(msg.iter_attachments()))
    monkeypatch.setattr(mailer.smtplib, "SMTP", FakeSMTP)
    cid = make_case(client, admin)
    did = client.post("/api/documents", json={"case_id": cid, "subject": "s", "body": "본문", "doc_no": "1",
                                              "recipient_email": "a@example.com"}, headers=admin).json()["id"]
    client.post(f"/api/documents/{did}/approve", json={"note": "결재"}, headers=admin)
    r = client.post(f"/api/documents/{did}/send", json={"method": "SMTP"}, headers=admin)
    assert r.status_code == 200 and r.json()["sent_ref"].startswith("<")
    assert sent == {"host": "smtp.test", "to": "a@example.com", "att": 1}


# ── 위원회 ────────────────────────────────────────────────
def test_meeting_flow_applies_decisions(client, admin):
    cid = make_case(client, admin)
    for to in ("REVIEW", "COMMITTEE"):
        client.post(f"/api/cases/{cid}/transition", json={"to": to}, headers=admin)
    mid = client.post("/api/meetings", json={"committee": "AD_REVIEW", "title": "제1차 광고심사위원회",
                                             "scheduled_at": "2026-10-20 15:00", "members": [{"name": "김", "role": "위원장"}]},
                      headers=admin).json()["id"]
    iid = client.post(f"/api/meetings/{mid}/items", json={"case_id": cid}, headers=admin).json()["id"]
    client.patch(f"/api/meetings/items/{iid}", json={"decision": "CORRECTION", "vote_for": 5, "vote_against": 0}, headers=admin)
    ag = client.get(f"/api/meetings/{mid}/agenda").json()["text"]
    assert "위반 사실" in ag and "가나특허" in ag
    r = client.post(f"/api/meetings/{mid}/apply-decisions", headers=admin).json()
    assert r["applied"][0]["to"] == "시정 요구"
    c = client.get(f"/api/cases/{cid}").json()
    assert c["status"] == "CORRECTION_ORDERED" and c["correction_due"]
    s = client.post(f"/api/meetings/{mid}/summarize", json={"transcript": "김 00:01\n시정 요구하기로 의결합니다. 찬성 5명입니다."},
                    headers=admin).json()
    assert s["resolutions"] and "회의록" in s["draft"]
    assert client.patch(f"/api/meetings/{mid}", json={"allowance_paid": True}, headers=admin).status_code == 200


# ── 지식베이스 ────────────────────────────────────────────
def test_precedent_csv_and_book_upload(client, admin):
    csv_bytes = "origin,volume,title,sanction_type,holding,keywords\nKBA,제8집,허위 광고 사례,과태료,허위 경력 광고,광고\n".encode("utf-8")
    assert client.post("/api/precedents/import-csv", files={"file": ("p.csv", csv_bytes)}, headers=admin).json()["imported"] == 1
    book = ("징계사례 1. 혐의자는 블로그에 승소율 95%를 표기하였다. 이는 업무수행 결과에 대한 부당한 기대를 갖게 하는 광고에 해당한다. "
            "징계: 과태료 300만원\n" * 5).encode("utf-8")
    r = client.post("/api/source-docs", data={"title": "테스트 사례집"}, files={"file": ("b.txt", book)}, headers=admin)
    assert r.status_code == 200 and r.json()["chunks"] >= 1
    # 같은 파일 재업로드 차단
    assert client.post("/api/source-docs", data={"title": "중복"}, files={"file": ("b.txt", book)}, headers=admin).status_code == 409
    s = client.post("/api/precedents/search", json={"text": "승소율 광고"}, headers=admin).json()
    assert s["passages"] and s["precedents"]
    ex = client.post("/api/source-docs/extract", json={"chunk_ids": [s["passages"][0]["id"]]}, headers=admin).json()
    assert ex["candidates"][0]["sanction_type"].startswith("과태료")


def test_article_import(client, admin):
    text = "< 테스트 세칙 >\n제1조(목적) 테스트 세칙이다.\n제2조(광고) 과장 광고 금지.\n".encode("utf-8")
    r = client.post("/api/articles/import", files={"file": ("r.txt", text)}, headers=admin)
    assert r.status_code == 200 and r.json()["count"] == 2
    arts = client.get("/api/articles?q=과장 광고 금지").json()
    assert any(a["source_name"] == "테스트 세칙" for a in arts)


# ── 관리 ──────────────────────────────────────────────────
def test_backup_and_traversal(client, admin):
    r = client.post("/api/admin/backups", headers=admin)
    assert r.status_code == 200
    name = r.json()["db"]
    assert client.get(f"/api/admin/backups/{name}").status_code == 200
    assert client.get("/api/admin/backups/..%2F..%2Fetc%2Fpasswd").status_code == 404
    import sqlite3, tempfile
    data = client.get(f"/api/admin/backups/{name}").content
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        f.write(data); f.flush()
        assert sqlite3.connect(f.name).execute("SELECT COUNT(*) FROM articles").fetchone()[0] > 100


def test_audit_log_records(client, admin):
    make_case(client, admin)
    actions = [a["action"] for a in client.get("/api/admin/audit").json()]
    assert "case.create" in actions and "auth.login" in actions


# ── AI 근거 검증(환각 차단) ───────────────────────────────
def test_grounded_analysis_rejects_hallucinations(monkeypatch):
    articles = [{"id": 7, "citation": "변리사 광고에 관한 규정 제7조", "body": "변리사는 \"국내 최고\" 기타 이와 유사한 용어를 사용하여 광고할 수 없다."}]
    fake = {
        "summary": "요약", "insufficient": False, "missing_info": [],
        "issues": [
            {"issue": "정상", "article_id": "A7", "quote": "\"국내 최고\" 기타 이와 유사한 용어", "reasoning": "r", "likelihood": "높음"},
            {"issue": "없는 조문", "article_id": "A99", "quote": "아무거나", "reasoning": "r", "likelihood": "높음"},
            {"issue": "지어낸 인용", "article_id": "A7", "quote": "변리사는 무조건 징계한다", "reasoning": "r", "likelihood": "보통"},
        ],
        "precedents": [{"precedent_id": "P5", "relevance": "x", "sanction": "견책"}],
    }
    monkeypatch.setattr(llm, "_call_json", lambda *a, **k: fake)
    r = llm.grounded_analysis("사실", articles, [])
    assert [i["issue"] for i in r["issues"]] == ["정상"]
    reasons = sorted(x["reject_reason"] for x in r["rejected"])
    assert reasons == ["인용문이 조문 원문에 없음", "제공하지 않은 근거 ID", "제공하지 않은 선례 ID"]


def test_minutes_ai_verification(monkeypatch):
    monkeypatch.setattr(llm, "_call_json", lambda *a, **k: {
        "overview": "o", "speakers": [], "follow_ups": [],
        "resolutions": [{"agenda": "1", "decision": "시정", "vote": "5:0", "evidence_quote": "시정 요구하기로 의결"},
                        {"agenda": "2", "decision": "제명", "vote": "-", "evidence_quote": "제명하기로 의결"}]})
    r = llm.summarize_minutes("위원장: 시정 요구하기로 의결합니다.", ["1"])
    assert [x["verified"] for x in r["resolutions"]] == [True, False]
