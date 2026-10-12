"""상황별 공문 양식과 렌더링.

양식 규칙은 대한변리사회 시행문 표기(수 신/참 조/제 목, 1.→가.→(1), 날짜 '2026. 8. 18.(화)', '끝.')를 따른다.
값이 없는 자리에는 지어내지 않고 {{확인 필요: 항목}} 을 남긴다.
"""
import re
from datetime import date

WEEKDAYS = "월화수목금토일"

FOOTER = """대한변리사회장

수신자 {{recipient}}
시행 {{doc_no}} ({{issue_date_compact}})  접수
우편번호 06660 서울 서초구 명달로 107 (서초동, 대한변리사회 회관) / www.kpaa.or.kr
전화번호 {{contact_phone}} FAX 02-3486-3511 / 메일 {{contact_email}} / 비공개
결재자 {{approval_line}}
협조자 {{cooperation_line}}"""

DEFAULT_TEMPLATES = [
    {
        "code": "SUPPLEMENT_REQUEST", "name": "민원 증빙자료 보완 요청", "category": "CASE",
        "subject": "{{case_type_label}} 관련 민원 증빙자료 보완 요청의 건",
        "body": """수 신  {{complainant_name}} 귀하
참 조
제 목  {{subject}}

1. 귀하의 건승을 기원합니다.
2. 귀하께서 {{received_date}} 본회에 제출하신 민원(본회 접수번호 {{case_no}})과 관련하여 사실관계 확인을 위해 아래와 같이 증빙자료의 보완을 요청드립니다.
  가. 민원 대상: {{respondent_office}}
  나. 보완 요청 자료: {{supplement_items}}
  다. 제출 기한: {{supplement_due}}까지
  라. 제출 방법: 전자우편({{contact_email}})
3. 기한 내 보완자료가 제출되지 않을 경우 현재 제출된 자료만으로 검토가 진행될 수 있음을 알려드립니다.
4. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
    {
        "code": "EXPLANATION_REQUEST", "name": "소명 요청", "category": "CASE",
        "subject": "{{case_type_label}}규정 위반 의심 사항에 대한 소명 요청의 건",
        "body": """수 신  {{respondent_office}} 대표변리사
참 조  {{respondent_name}} 변리사
제 목  {{subject}}

1. 회원님의 건승을 기원합니다.
2. 본회는 {{source_phrase}} 귀 사무소의 아래 사항이 {{applied_rules}}에 위반될 소지가 있는 것으로 확인하였습니다.
  가. 사건번호: {{case_no}}
  나. 확인 일자: {{received_date}}
  다. 위반 의심 사항
{{violation_lines}}
  라. 관련 규정
{{rule_lines}}
  마. 채증 자료: {{evidence_summary}}
3. 이에 {{basis_phrase}} 소명의 기회를 드리오니, {{explanation_due}}까지 위 사항에 대한 소명서(시정 결과가 있는 경우 시정 전·후 자료 포함)를 제출하여 주시기 바랍니다.
  가. 제출 방법: 전자우편({{contact_email}})
  나. 제출 서식: 자유 양식(사실관계, 위반 여부에 대한 의견, 시정 계획 또는 결과)
4. 기한 내 소명이 없거나 소명이 불충분한 경우 관련 위원회에 안건으로 상정될 수 있으며, 「징계위원회 운영 규정」 제8조제5호에 따라 소명자료 제출 요구에 2회 이상 불응하는 것은 징계사유가 될 수 있음을 알려드립니다.
5. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
    {
        "code": "CORRECTION_RECOMMEND", "name": "자진 시정 권고", "category": "CASE",
        "subject": "{{case_type_label}} 관련 자진 시정 권고의 건",
        "body": """수 신  {{respondent_office}} 대표변리사
참 조  {{respondent_name}} 변리사
제 목  {{subject}}

1. 회원님의 건승을 기원합니다.
2. 본회 사건번호 {{case_no}}와 관련하여, 귀 사무소의 아래 사항은 {{applied_rules}}에 부합하지 않을 소지가 있어 자진 시정을 권고드립니다.
  가. 시정 권고 사항
{{violation_lines}}
  나. 관련 규정
{{rule_lines}}
  다. 시정 기한: {{correction_due}}까지
3. 시정을 완료하신 경우 시정 후 화면 캡처 등 확인 자료를 위 기한까지 전자우편({{contact_email}})으로 회신하여 주시기 바랍니다.
4. 기한 내 시정이 확인되지 않을 경우 관련 위원회 심의 절차가 진행될 수 있음을 알려드립니다.
5. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
    {
        "code": "CORRECTION_ORDER", "name": "위원회 의결에 따른 시정 요구", "category": "CASE",
        "subject": "{{committee_name}} 의결에 따른 시정 요구의 건",
        "body": """수 신  {{respondent_office}} 대표변리사
참 조  {{respondent_name}} 변리사
제 목  {{subject}}

1. 회원님의 건승을 기원합니다.
2. 본회 {{committee_name}}는 {{decision_date}} 회의에서 귀 사무소 관련 사건(사건번호 {{case_no}})을 심의하고, 아래와 같이 시정을 요구하기로 의결하였습니다.
  가. 위반 사항
{{violation_lines}}
  나. 관련 규정
{{rule_lines}}
  다. 의결 내용: {{decision_text}}
  라. 시정 기한: {{correction_due}}까지
3. 「변리사 광고에 관한 규정」 제12조제2항에 따라 위 요구를 받은 때에는 즉시 이행한 후 그 결과를 본회에 보고하여 주시기 바랍니다.
4. 기한 만료 후 1개월이 경과하도록 시정조치가 이루어지지 않는 경우, 같은 규정 제12조제3항 및 제4항에 따라 시정조치 요구 사실의 공표 또는 징계발의 안건 상정 등의 조치가 이루어질 수 있음을 알려드립니다.
5. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
    {
        "code": "COMMITTEE_NOTICE", "name": "위원회 안건 상정 통지", "category": "CASE",
        "subject": "{{committee_name}} 안건 상정 안내",
        "body": """수 신  {{respondent_office}} 대표변리사
참 조  {{respondent_name}} 변리사
제 목  {{subject}}

1. 회원님의 건승을 기원합니다.
2. 본회 사건번호 {{case_no}}와 관련하여, {{committee_reason}} 아래와 같이 {{committee_name}} 안건으로 상정되었음을 안내드립니다.
  가. 상정 위원회: {{committee_name}}
  나. 심의 예정일: {{meeting_date}}
  다. 심의 대상
{{violation_lines}}
3. 추가로 제출하실 의견이나 자료가 있는 경우 {{opinion_due}}까지 전자우편({{contact_email}})으로 제출하여 주시기 바랍니다.
4. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
    {
        "code": "DISCIPLINE_REFERRAL", "name": "징계위원회 회부 및 출석 안내", "category": "CASE",
        "subject": "징계위원회 심의기일 출석 안내",
        "body": """수 신  {{respondent_name}} 변리사
참 조  {{respondent_office}}
제 목  {{subject}}

1. 회원님의 건승을 기원합니다.
2. 본회 사건번호 {{case_no}}와 관련하여 귀하에 대한 징계혐의 사건이 징계위원회에 회부되었으므로, 「징계위원회 운영 규정」 제9조 및 제10조에 따라 아래와 같이 심의기일을 안내드립니다.
  가. 심의 일시: {{meeting_date}}
  나. 장소: {{meeting_location}}
  다. 징계혐의 사실
{{violation_lines}}
  라. 관련 규정
{{rule_lines}}
3. 귀하는 심의기일에 출석하여 구술 또는 서면으로 진술할 수 있으며, 증거서류나 증거물을 제출하고 징계에 관한 의견을 진술할 수 있습니다.
4. 같은 규정 제9조제2항에 따라 심의기일에 출석하지 않은 경우에도 심의절차가 진행되어 종결될 수 있음을 알려드립니다.
5. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
    {
        "code": "CLOSURE_NOTICE", "name": "사건 종결 통지(피민원인)", "category": "CASE",
        "subject": "{{case_type_label}} 관련 사건 종결 안내",
        "body": """수 신  {{respondent_office}} 대표변리사
참 조  {{respondent_name}} 변리사
제 목  {{subject}}

1. 회원님의 건승을 기원합니다.
2. 본회 사건번호 {{case_no}}와 관련하여 제출하신 소명 및 시정 결과를 검토한 결과, 아래와 같이 사건을 종결하였음을 안내드립니다.
  가. 종결 일자: {{closed_date}}
  나. 종결 사유: {{closed_reason}}
3. 앞으로도 「변리사법」 및 본회 회칙·규정을 준수하여 주시기를 부탁드립니다.
4. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
    {
        "code": "COMPLAINANT_RESULT", "name": "민원 처리결과 안내(민원인)", "category": "CASE",
        "subject": "민원 처리결과 안내",
        "body": """수 신  {{complainant_name}} 귀하
참 조
제 목  {{subject}}

1. 귀하의 건승을 기원합니다.
2. 귀하께서 {{received_date}} 제출하신 민원(본회 접수번호 {{case_no}})에 대한 처리결과를 아래와 같이 안내드립니다.
  가. 민원 대상: {{respondent_office}}
  나. 처리 결과: {{result_text}}
3. 본회 업무에 관심을 가져 주신 데 감사드립니다.
4. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
    {
        "code": "EXTERNAL_REFERRAL", "name": "지식재산처 징계 요구(외부 이관)", "category": "CASE",
        "subject": "변리사 징계 요구의 건",
        "body": """수 신  지식재산처장
참 조
제 목  {{subject}}

1. 지식재산처의 무궁한 발전을 기원합니다.
2. 본회는 「변리사법」 제17조제3항에 따라 아래 변리사에 대하여 징계사유가 있다고 인정되어 증거서류를 첨부하여 징계를 요구합니다.
  가. 대상: {{respondent_office}} {{respondent_name}} (등록번호 {{respondent_reg_no}})
  나. 징계 사유
{{violation_lines}}
  다. 관련 규정
{{rule_lines}}
  라. 본회 처리 경과: {{history_summary}}
3. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})

붙 임  1. 징계 사유 증거서류 일체 1부.
       2. 본회 처리 경과 및 위원회 의결 자료 1부.  끝.

""" + FOOTER,
    },
    {
        "code": "MEETING_NOTICE", "name": "위원회 개최 안내(위원)", "category": "MEETING",
        "subject": "{{meeting_title}} 개최 안내",
        "body": """수 신  {{committee_name}} 위원
참 조
제 목  {{subject}}

1. 위원님의 건승을 기원합니다.
2. {{committee_name}}를 아래와 같이 개최하오니 참석하여 주시기 바랍니다.
  가. 일시: {{meeting_date}}
  나. 장소: {{meeting_location}}
  다. 안건
{{agenda_lines}}
3. 회의자료는 개최 전 별도 송부할 예정이며, 「징계위원회 운영 규정」 제15조 등에 따른 비밀유지의무에 유의하여 주시기 바랍니다.
4. 참석 여부를 {{reply_due}}까지 회신하여 주시기 바랍니다.
5. 문의처: {{dept_name}} {{contact_name}} ({{contact_email}} / {{contact_phone}})  끝.

""" + FOOTER,
    },
]

COMMITTEE_NAMES = {"AD_REVIEW": "광고심사위원회", "ETHICS": "윤리위원회", "DISCIPLINE": "징계위원회", "STANDING_BOARD": "상임이사회"}

OPTIONAL_VARS = {"cooperation_line"}
_VAR = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


def kdate(value: str | None) -> str:
    """'2026-08-18' → '2026. 8. 18.(화)'"""
    if not value:
        return ""
    try:
        d = date.fromisoformat(str(value)[:10])
    except ValueError:
        return str(value)
    return f"{d.year}. {d.month}. {d.day}.({WEEKDAYS[d.weekday()]})"


def kdatetime(value: str | None) -> str:
    if not value:
        return ""
    s = str(value)
    t = s[11:16] if len(s) >= 16 else ""
    return kdate(s) + (f" {t}" if t and t != "00:00" else "")


def render(text: str, values: dict) -> tuple[str, list[str]]:
    """{{변수}} 치환. 값이 비면 {{확인 필요: 변수}} 를 남기고 목록으로 돌려준다."""
    missing: list[str] = []

    def sub(m):
        key = m.group(1)
        v = values.get(key)
        if key in OPTIONAL_VARS and (v is None or not str(v).strip()):
            return ""
        if v is None or (isinstance(v, str) and not v.strip()):
            label = VAR_LABELS.get(key, key)
            if label not in missing:
                missing.append(label)
            return f"{{{{확인 필요: {label}}}}}"
        return str(v)

    # subject 가 본문에 들어가므로 두 번 치환(중첩 변수 허용)
    once = _VAR.sub(sub, text)
    return once, missing


VAR_LABELS = {
    "recipient": "수신자", "doc_no": "시행번호", "issue_date_compact": "시행일", "contact_phone": "담당자 전화",
    "contact_email": "담당자 메일", "contact_name": "담당자", "approval_line": "결재선", "cooperation_line": "협조자",
    "complainant_name": "민원인 성명", "respondent_office": "사무소명", "respondent_name": "변리사 성명",
    "respondent_reg_no": "변리사 등록번호", "received_date": "접수일", "case_no": "사건번호",
    "supplement_items": "보완 요청 자료", "supplement_due": "보완 제출 기한", "explanation_due": "소명 기한",
    "correction_due": "시정 기한", "applied_rules": "적용 규정", "violation_lines": "위반 의심 사항",
    "rule_lines": "관련 규정", "evidence_summary": "채증 자료", "committee_name": "위원회명",
    "decision_date": "의결일", "decision_text": "의결 내용", "meeting_date": "회의 일시", "meeting_location": "회의 장소",
    "committee_reason": "상정 사유", "opinion_due": "의견 제출 기한", "closed_date": "종결일", "closed_reason": "종결 사유",
    "result_text": "처리 결과", "history_summary": "처리 경과", "agenda_lines": "안건 목록", "reply_due": "회신 기한",
    "meeting_title": "회의명", "dept_name": "부서명", "subject": "제목", "case_type_label": "사건 유형",
    "source_phrase": "인지 경위", "basis_phrase": "근거 규정",
}
