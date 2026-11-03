"""사건 처리 절차(상태 전이)와 기한 규칙.

업무 절차(회원서비스실 제공 자료 기준)
  접수 → 검토(증빙 보완) → 결재(담당이사, 중대건 회장) → 소명요청(약 2주 기한)
  → 소명검토 → [자진시정: 종결] / [불충분·거부·판단 모호: 위원회 상정
     (윤리위원회는 상임이사회 심의 경유)]
  → 위원회 결정: 시정요구 / 징계위원회 회부 / 종결 / 외부기관 이관(지식재산처·공정위)
"""
from datetime import date, datetime, timedelta

STATUSES = {
    "RECEIVED": "접수",
    "REVIEW": "검토 중",
    "PENDING_APPROVAL": "결재 대기",
    "EXPLANATION_REQUESTED": "소명 요청",
    "EXPLANATION_REVIEW": "소명 검토",
    "COMMITTEE": "위원회 상정",
    "CORRECTION_ORDERED": "시정 요구",
    "DISCIPLINE": "징계위원회 회부",
    "EXTERNAL": "외부기관 이관",
    "CLOSED": "종결",
}

TRANSITIONS = {
    "RECEIVED": ["REVIEW", "CLOSED"],
    "REVIEW": ["PENDING_APPROVAL", "COMMITTEE", "EXTERNAL", "CLOSED"],
    "PENDING_APPROVAL": ["EXPLANATION_REQUESTED", "REVIEW"],
    "EXPLANATION_REQUESTED": ["EXPLANATION_REVIEW", "COMMITTEE"],
    "EXPLANATION_REVIEW": ["CLOSED", "COMMITTEE", "EXPLANATION_REQUESTED"],
    "COMMITTEE": ["CORRECTION_ORDERED", "DISCIPLINE", "EXTERNAL", "CLOSED", "EXPLANATION_REQUESTED"],
    "CORRECTION_ORDERED": ["CLOSED", "DISCIPLINE", "COMMITTEE"],
    "DISCIPLINE": ["CLOSED", "EXTERNAL"],
    "EXTERNAL": ["CLOSED"],
    "CLOSED": ["REVIEW"],
}

# 사유(note) 기재가 필수인 전이 — 불이익 처분의 근거 기록
NOTE_REQUIRED = {
    "PENDING_APPROVAL->EXPLANATION_REQUESTED": "결재권자·결재일(예: 담당 이사 OOO, 2026-10-12 전자결재)",
    "EXPLANATION_REVIEW->CLOSED": "종결 사유(자진 시정 확인 내용 등)",
    "RECEIVED->CLOSED": "종결 사유",
    "REVIEW->CLOSED": "종결 사유",
    "COMMITTEE->CLOSED": "위원회 결정 내용",
    "COMMITTEE->CORRECTION_ORDERED": "위원회 결정 내용(의결일)",
    "COMMITTEE->DISCIPLINE": "징계위원회 회부 결정 내용",
    "CORRECTION_ORDERED->DISCIPLINE": "미시정 사실 및 위원회 의결",
    "REVIEW->EXTERNAL": "이관 기관·사유(상임이사회 의결 등)",
    "COMMITTEE->EXTERNAL": "이관 기관·사유(상임이사회 의결 등)",
    "DISCIPLINE->EXTERNAL": "이관 기관·사유",
    "DISCIPLINE->CLOSED": "징계 결정 및 통보 내용",
    "CLOSED->REVIEW": "재개 사유",
}

ADMIN_ONLY = {"CLOSED->REVIEW"}

SOURCES = {"MONITORING": "자체 모니터링", "HOMEPAGE": "홈페이지", "PHONE": "유선", "EMAIL": "이메일", "OTHER": "기타"}
CASE_TYPES = {"AD": "광고", "ETHICS": "윤리"}

DEFAULT_SETTINGS = {
    "org_name": "대한변리사회",
    "dept_name": "회원서비스실",
    "explanation_days": "14",        # 소명 기한(약 2주)
    "correction_days": "30",         # 시정 기한 기본값
    "discipline_after_days": "30",   # 광고규정 제12조④: 시정기한 만료 후 1개월
    "objection_days": "30",          # 징계위원회 운영규정 제19조①
    "limitation_years": "3",         # 변리사법 제17조④ 징계시효
    "doc_no_prefix": "대변",
    "ad_case_owner": "이대운 차장",
    "ethics_case_owner": "황예진 차장",
}


def can_transition(cur: str, nxt: str) -> bool:
    return nxt in TRANSITIONS.get(cur, [])


def note_requirement(cur: str, nxt: str) -> str | None:
    return NOTE_REQUIRED.get(f"{cur}->{nxt}")


def add_days(base: str | None, days: int) -> str:
    d = date.fromisoformat(base[:10]) if base else date.today()
    return (d + timedelta(days=days)).isoformat()


def _d(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        return None


def alerts_for(case: dict, settings: dict, today: date | None = None) -> list[dict]:
    """사건별 기한 경보. level: danger / warn / info"""
    today = today or date.today()
    out = []
    st = case["status"]
    due = _d(case.get("explanation_due"))
    if st == "EXPLANATION_REQUESTED" and due:
        left = (due - today).days
        if left < 0:
            out.append({"level": "danger", "code": "EXPLANATION_OVERDUE",
                        "text": f"소명 기한 {-left}일 경과 — 미제출 시 위원회 상정 검토"})
        elif left <= 3:
            out.append({"level": "warn", "code": "EXPLANATION_SOON", "text": f"소명 기한 D-{left}"})
    cdue = _d(case.get("correction_due"))
    if st == "CORRECTION_ORDERED" and cdue:
        after = int(settings.get("discipline_after_days", 30))
        if today > cdue + timedelta(days=after):
            out.append({"level": "danger", "code": "DISCIPLINE_ELIGIBLE",
                        "text": f"시정 기한 만료 후 {after}일 경과 — 징계발의 상정 가능(광고규정 제12조④)"})
        elif today > cdue:
            out.append({"level": "warn", "code": "CORRECTION_OVERDUE", "text": f"시정 기한 {(today - cdue).days}일 경과 — 이행 확인 필요"})
    odue = _d(case.get("objection_due"))
    if odue and st == "DISCIPLINE":
        if today <= odue:
            out.append({"level": "info", "code": "OBJECTION_PERIOD", "text": f"이의신청 기간 중(~{odue.isoformat()})"})
        else:
            out.append({"level": "warn", "code": "OBJECTION_ENDED", "text": "이의신청 기간 종료 — 공고(회지·홈페이지 2주 내)·특허청 보고 진행"})
    vd = _d(case.get("violation_date"))
    if vd and st not in ("CLOSED", "EXTERNAL"):
        years = int(settings.get("limitation_years", 3))
        try:
            limit = vd.replace(year=vd.year + years)
        except ValueError:  # 2/29
            limit = vd.replace(year=vd.year + years, day=28)
        left = (limit - today).days
        if left < 0:
            out.append({"level": "danger", "code": "LIMITATION_PASSED", "text": f"징계시효({years}년, 변리사법 제17조④) 경과 의심 — 위반일 재확인"})
        elif left <= 180:
            out.append({"level": "warn", "code": "LIMITATION_SOON", "text": f"징계시효 만료 {left}일 전({limit.isoformat()})"})
    if not case.get("respondent_is_member", 1) and st not in ("EXTERNAL", "CLOSED"):
        out.append({"level": "info", "code": "NON_MEMBER", "text": "미등록·비회원 — 자체 처분 곤란, 상임이사회 경유 지식재산처 징계요청/공정위 신고 검토"})
    return out


def next_case_no(conn, case_type: str, year: int | None = None) -> str:
    year = year or datetime.now().year
    prefix = f"{case_type}-{year}-"
    row = conn.execute("SELECT case_no FROM cases WHERE case_no LIKE ? ORDER BY case_no DESC LIMIT 1", (prefix + "%",)).fetchone()
    n = int(row["case_no"].rsplit("-", 1)[1]) + 1 if row else 1
    return f"{prefix}{n:04d}"
