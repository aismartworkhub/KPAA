"""초기 데이터: 설정·공문양식·법령조문·관리자 계정. (재실행해도 기존 데이터는 덮어쓰지 않음)

  python -m app.seed            # 초기화만
  python -m app.seed --demo     # 화면 확인용 가상 예시 데이터 추가(실제 사건 아님)
"""
import os
import secrets
import sys

from . import config, db
from .security import hash_password
from .services import doc_templates, reg_parser, workflow


def load_articles(conn, text: str, default_source_name: str | None = None, replace: bool = True) -> dict:
    arts = reg_parser.parse(text, default_source_name)
    if not arts:
        return {"sources": [], "count": 0}
    sources = sorted({a["source"] for a in arts})
    with db.transaction(conn):
        if replace:
            for s in sources:
                # 사건에 연결된 조문은 유지되도록 UPSERT 사용, 원문에서 사라진 조문만 삭제
                keep = [a["article_no"] for a in arts if a["source"] == s]
                q = ",".join("?" * len(keep))
                conn.execute(f"DELETE FROM articles WHERE source=? AND article_no NOT IN ({q})", (s, *keep))
        for a in arts:
            conn.execute(
                """INSERT INTO articles(source, source_name, chapter, article_no, title, body, sort_order)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(source, article_no) DO UPDATE SET
                     source_name=excluded.source_name, chapter=excluded.chapter, title=excluded.title,
                     body=excluded.body, sort_order=excluded.sort_order, updated_at=datetime('now','localtime')""",
                (a["source"], a["source_name"], a["chapter"], a["article_no"], a["title"], a["body"], a["sort_order"]))
    return {"sources": sources, "count": len(arts)}


def seed_base(conn) -> None:
    for k, v in workflow.DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings(key, value) VALUES (?,?)", (k, v))
    for t in doc_templates.DEFAULT_TEMPLATES:
        conn.execute("INSERT OR IGNORE INTO templates(code, name, category, subject, body) VALUES (?,?,?,?,?)",
                     (t["code"], t["name"], t["category"], t["subject"], t["body"]))
    if conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0 and config.SEED_REGULATIONS.exists():
        load_articles(conn, config.SEED_REGULATIONS.read_text(encoding="utf-8"))
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        pw = config.INITIAL_ADMIN_PASSWORD or secrets.token_urlsafe(12)
        conn.execute("INSERT INTO users(username, name, role, password_hash, must_change_pw) VALUES (?,?,?,?,1)",
                     ("admin", "시스템 관리자", "admin", hash_password(pw)))
        if not config.INITIAL_ADMIN_PASSWORD:
            path = config.DATA_DIR / "INITIAL_ADMIN_PASSWORD.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"admin / {pw}\n최초 로그인 후 반드시 비밀번호를 변경하고 이 파일을 삭제하세요.\n", encoding="utf-8")
            os.chmod(path, 0o600)
            print(f"[KPAA] 최초 관리자 계정이 생성되었습니다. 비밀번호 파일: {path}", file=sys.stderr)


DEMO_CASES = [
    # (type, source, title, office, name, email, facts, ad_text, violation_date, priority)
    ("AD", "MONITORING", "[예시] 블로그 광고 '국내 최고·등록률 98%' 표기", "가나다특허사무소(가상)", "가상인", "demo-a@example.com",
     "포털 블로그 광고에 '국내 최고 특허사무소', '상표 등록률 98%', '미등록 시 전액 환불' 문구가 게재됨. 산출 근거 표시 없음.",
     "국내 최고 특허사무소! 상표 등록률 98%, 미등록 시 전액 환불 보장. 상표출원 최저가 9,900원부터. 지금 무료 상담 받으세요.",
     "2026-09-20", "NORMAL"),
    ("AD", "HOMEPAGE", "[예시] 홈페이지 '국제변리사' 명칭 및 직원 '상표전문가' 표기", "라마바국제특허(가상)", "예시인", "demo-b@example.com",
     "민원인 제보: 사무소 홈페이지에 대표를 '국제변리사'로 소개하고, 변리사가 아닌 사무직원을 '상표전문가'로 표기함.",
     "국제변리사가 직접 상담합니다. 상표전문가 김예시 팀장이 출원부터 등록까지 책임집니다. 타 사무소 대비 절반 비용.",
     "2026-08-01", "NORMAL"),
    ("ETHICS", "EMAIL", "[예시] 수임사건 처리 지연 및 의뢰인 연락 두절 민원", "사아자특허법률사무소(가상)", "샘플인", "demo-c@example.com",
     "의뢰인이 상표 출원 의뢰 후 6개월간 진행상황 안내를 받지 못했고, 의견제출 기한을 도과하여 거절결정을 받았다는 민원 제기.",
     None, "2026-03-15", "SERIOUS"),
]

DEMO_PRECEDENTS = [
    ("DEMO", "예시", "DEMO-1", "[가상 예시] 근거 없는 '업계 1위' 광고", "광고", "경고", "",
     "근거 없이 '업계 1위' 표현을 사용한 광고(가상 사례).", "객관적 근거 없는 최상급 표현은 소비자를 오도할 우려가 있음(가상 요지).",
     "광고규정 제7조②", "최고, 1위, 최상급"),
    ("DEMO", "예시", "DEMO-2", "[가상 예시] 의뢰인 기한 관리 소홀", "수임·성실의무", "견책", "",
     "기한 관리 소홀로 권리 상실(가상 사례).", "성실 대리 의무 위반(가상 요지).", "윤리규정 제9조, 제21조", "기한, 성실, 지연"),
]


def seed_demo(conn) -> None:
    from datetime import date
    from .services import ad_rules
    if conn.execute("SELECT COUNT(*) FROM cases WHERE title LIKE '[예시]%'").fetchone()[0]:
        print("예시 데이터가 이미 있습니다.")
        return
    admin_id = conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()[0]
    with db.transaction(conn):
        for ctype, src, title, office, name, email, facts, ad_text, vdate, prio in DEMO_CASES:
            no = workflow.next_case_no(conn, ctype)
            cur = conn.execute(
                """INSERT INTO cases(case_no, case_type, source, title, priority, respondent_office, respondent_name,
                   respondent_email, facts, violation_date, received_at, created_by)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (no, ctype, src, title, prio, office, name, email, facts, vdate, date.today().isoformat(), admin_id))
            cid = cur.lastrowid
            conn.execute("INSERT INTO case_events(case_id, user_id, type, to_status, note) VALUES (?,?,?,?,?)",
                         (cid, admin_id, "CREATED", "RECEIVED", "예시 데이터"))
            if ad_text:
                ev = conn.execute(
                    "INSERT INTO evidence(case_id, url, office_name, ad_text, captured_at, note, created_by) VALUES (?,?,?,?,?,?,?)",
                    (cid, "https://example.com/demo-ad", office, ad_text, date.today().isoformat(), "예시 채증", admin_id)).lastrowid
                import json
                for f in ad_rules.screen(ad_text):
                    conn.execute(
                        """INSERT INTO ad_findings(case_id, evidence_id, rule_code, rule_label, article_refs, matched_text, context, confidence)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (cid, ev, f["rule_code"], f["rule_label"], json.dumps(f["refs"], ensure_ascii=False),
                         f["matched_text"], f["context"], f["confidence"]))
        for row in DEMO_PRECEDENTS:
            conn.execute(
                """INSERT INTO precedents(origin, volume, case_ref, title, category, sanction_type, sanction_detail,
                   facts, holding, related_rules, keywords, created_by) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (*row, admin_id))
    print("예시 데이터를 추가했습니다(모두 가상 데이터).")


def main() -> None:
    db.init_db()
    conn = db.get_conn()
    try:
        seed_base(conn)
        if "--demo" in sys.argv:
            seed_demo(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
