"""광고규정 위반 의심 표현 1차 스크리닝(규칙 기반).

- 결과는 '위반 확정'이 아니라 '검토 필요' 신호다. 최종 판단은 담당자·위원회가 한다.
- 각 규칙은 반드시 본회 규정 조문(AD_REG / PAA / ETHICS)에 연결된다. 근거 없는 규칙은 두지 않는다.
- 규칙을 추가·수정할 때는 tests/test_ad_rules.py 에 사례를 함께 추가한다.
"""
import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Ref:
    source: str
    article_no: str
    item: str = ""          # 호·항 표시 (예: "제2항", "제6호")


@dataclass
class Rule:
    code: str
    label: str
    patterns: list[str]
    refs: list[Ref]
    confidence: str          # HIGH / MEDIUM / LOW
    guide: str               # 담당자 확인 포인트
    exclude: list[str] = field(default_factory=list)   # 매치 주변에 있으면 제외(오탐 방지)


RULES: list[Rule] = [
    Rule("SUPERLATIVE", "최고·최초·유일·1위 등 최상급 표현",
         [r"(국내|업계|대한민국|한국|국내외)\s*(최고|최초|최대|최상|유일|1위|No\.?\s*1|넘버\s*원)",
          r"(최고의|최고\s*수준|최초로|유일한|유일의)\s*\S*(변리사|특허|사무소|법인|상표|서비스)",
          r"(No\.?\s*1|넘버\s*원|1위|일등)\s*(변리사|특허|사무소|법인|상표)?",
          r"업계\s*(최고|최초|유일)"],
         [Ref("AD_REG", "제7조", "제2항"), Ref("AD_REG", "제4조", "제2호"), Ref("PAA", "제8조의5", "제2항제3호")],
         "HIGH", "객관적 근거(공인 순위·통계 출처)가 함께 표시되어 있는지 확인. 근거가 있어도 제7조②의 금지 용어는 사용 불가."),
    Rule("GUARANTEE", "등록·결과 보장 표현",
         [r"(등록|승소|성공|합격|거절\s*극복)\s*(100\s*%|보장|확실|책임\s*보장)",
          r"(100\s*%|무조건|반드시)\s*(등록|승소|성공)",
          r"(미등록|거절|실패)\s*시\s*(전액\s*)?(환불|비용\s*반환)"],
         [Ref("AD_REG", "제7조", "제2항"), Ref("AD_REG", "제4조", "제6호"), Ref("PAA", "제8조의5", "제2항제4호")],
         "HIGH", "업무수행 결과에 대한 부당한 기대를 갖게 하는지 확인. '환불 보장'은 보수 관련 제4조 제11호도 함께 검토."),
    Rule("SUCCESS_RATE", "등록률·승소율 등 성공률 표시",
         [r"(등록\s*률|등록\s*율|승소\s*율|승소\s*률|성공\s*률|성공\s*율|합격\s*률|통과\s*율|통과\s*률)\s*[:：]?\s*\d{1,3}(\.\d+)?\s*%?",
          r"\d{1,3}(\.\d+)?\s*%\s*의?\s*(등록|승소|성공)\s*(률|율)",
          r"(등록\s*률|승소\s*율|성공\s*률)\s*(1위|최고)"],
         [Ref("AD_REG", "제4조", "제6호"), Ref("AD_REG", "제7조", "제2항"), Ref("PAA", "제8조의5", "제2항제4호")],
         "HIGH", "수치의 산출 기준·기간·모수가 표시되었는지, 일부 사실만 강조해 오도하는지 확인."),
    Rule("FEE_PRICE", "최저가·할인·견적비교·후불 등 보수 관련 표현",
         [r"최저\s*(가|비용|수임료|수수료|가격)", r"(업계|국내)\s*최저",
          r"(할인|특가|이벤트\s*가|반값|파격\s*가|쿠폰|원가\s*(제공|수준))",
          r"(견적|가격)\s*(비교|입찰)", r"(후불|성공\s*보수\s*만|선\s*착수\s*후\s*결제)",
          r"\d[\d,]*\s*원\s*(부터|~|만)"],
         [Ref("AD_REG", "제4조", "제11호"), Ref("AD_REG", "제7조", "제2항")],
         "MEDIUM", "보수에 관해 견적·입찰·비교·최저·원가·후불·환불·할인쿠폰 등을 표방하는지 확인(2026. 8. 28. 개정 제11호)."),
    Rule("FREE_BENEFIT", "무료·경품·금품 제공 표현",
         [r"(무료|공짜|0\s*원)\s*(출원|등록|상표|특허|대행|진행)",
          r"(사은품|경품|상품권|캐시백|페이백|리워드|포인트\s*지급|현금\s*지급)",
          r"(수수료|비용|수임료)\s*(무료|면제|0\s*원)"],
         [Ref("AD_REG", "제4조", "제12호"), Ref("AD_REG", "제5조", "제1항")],
         "MEDIUM", "'무료 상담'은 일반적으로 허용되나, 업무 보수의 무료·부당 염가 또는 금품 제공 표방인지 구분.",
         exclude=[r"무료\s*상담", r"상담\s*무료", r"무료\s*검색"]),
    Rule("OUTCOME_PREDICTION", "처분·판결 결과 예측 표방",
         [r"(등록|승소|거절)\s*(가능성|확률)\s*(\d{1,3}\s*%|예측|진단|분석)",
          r"(AI|인공지능)\s*(등록|심사|결과)?\s*(예측|판정|진단)",
          r"(결과|심사\s*결과|판결)\s*(예측|미리\s*확인)"],
         [Ref("AD_REG", "제4조", "제13호"), Ref("AD_REG", "제5조", "제4항제3호")],
         "MEDIUM", "행정기관 처분·법원 판결 결과 예측을 표방하는지 확인. 플랫폼 참여 여부(제5조④3호)도 함께 확인."),
    Rule("FAKE_TITLE", "법적 근거 없는 자격·명칭 / 비변리사의 전문가 표기",
         [r"국제\s*변리사", r"국제\s*특허\s*(전문가|변리사)", r"해외\s*변리사",
          r"(특허|상표|지식재산권|지재권|IP|디자인)\s*전문가",
          r"(수석|전문|선임)\s*(컨설턴트|상담사|매니저)\s*\S{0,6}\s*(특허|상표)"],
         [Ref("AD_REG", "제4조", "제10호"), Ref("AD_REG", "제4조", "제9호"), Ref("PAA", "제8조의5", "제2항제2호")],
         "MEDIUM", "표기 대상이 등록 변리사인지 확인(변리사가 아닌 직원을 '전문가'로 표기하면 제4조 제9호). '국제변리사'는 법적 근거 없는 명칭."),
    Rule("COMPARISON", "다른 변리사 비방·비교",
         [r"(타\s*사무소|다른\s*(변리사|사무소|법인)|타\s*법인|타사)\s*(대비|보다|와\s*달리|와\s*비교)",
          r"(대형|일반)\s*(사무소|법인)\s*(보다|대비|와\s*달리)",
          r"(비싼|불친절한|무능한)\s*(변리사|사무소)"],
         [Ref("AD_REG", "제4조", "제3호"), Ref("PAA", "제8조의5", "제2항제5호")],
         "MEDIUM", "특정 또는 불특정 다른 변리사를 비방하거나 자신의 입장에서 비교하는지 확인."),
    Rule("OFFICIAL_TIES", "공무원 연고·전관 영향력 암시",
         [r"(특허청|특허심판원|법원|심사관|심판관)\s*(출신|인맥|연고|네트워크|라인)",
          r"전관\s*(예우|변리사|출신)?", r"(심사관|심판관)\s*(과|와)\s*(친분|직접\s*소통)"],
         [Ref("AD_REG", "제4조", "제5호"), Ref("ETHICS", "제29조")],
         "LOW", "경력 사실 기재 자체는 허용될 수 있음. 영향력을 미칠 수 있는 것처럼 선전·암시하는지가 판단 기준."),
    Rule("REFERRAL_PLATFORM", "소개·알선·중개 플랫폼 이용 정황",
         [r"(중개|알선|소개)\s*(수수료|료|비)", r"(변리사\s*매칭|매칭\s*플랫폼|변리사\s*찾기\s*서비스)",
          r"(가입비|회비|연결\s*수수료)"],
         [Ref("AD_REG", "제5조", "제4항"), Ref("AD_REG", "제8조", "제2항")],
         "LOW", "광고 게재처가 수임 알선·보수 비교·결과 예측 서비스인지 확인(플랫폼 약관·수수료 구조 채증)."),
    Rule("PROHIBITED_MEDIA", "금지된 광고 방법(현수막·전단 살포·확성기 등)",
         [r"현수막", r"(전단|전단지)\s*(배포|살포|삽입)", r"확성기|샌드위치\s*맨|어깨\s*띠", r"(차량|버스|택시|지하철)\s*(외부\s*)?광고"],
         [Ref("AD_REG", "제5조", "제3항")],
         "MEDIUM", "실제 광고 방법이 제5조③ 각호에 해당하는지 사진 등으로 확인."),
    Rule("PRE_REGISTRATION", "등록·회원가입 전 사전광고 의심",
         [r"(개업|오픈|개소)\s*예정", r"(합격자|수습\s*변리사|예비\s*변리사)\s*(상담|진행|대행)"],
         [Ref("AD_REG", "제6조")],
         "LOW", "광고 시점에 변리사 등록(변리사법 제5조①) 및 본회 가입이 완료되었는지 회원 DB로 확인."),
    Rule("UNSOLICITED", "특정 사건 당사자에 대한 무단 접촉 권유",
         [r"(거절\s*이유\s*통지|이의\s*신청|무효\s*심판|심판\s*청구)\s*(받으셨|받은)\s*(분|경우)",
          r"(귀사|귀하)의\s*(출원|상표|특허)\s*(건|에\s*대해)\s*(연락|안내)드"],
         [Ref("AD_REG", "제4조", "제7호"), Ref("AD_REG", "제4조", "제8호")],
         "LOW", "특정 사건 당사자에게 요청·동의 없이 문자·메일 등으로 접촉해 수임을 권유했는지 확인(수신 화면 채증)."),
]

NAME_RES = (re.compile(r"변리사\s*([가-힣]{2,4})"), re.compile(r"([가-힣]{2,4})\s*변리사"))
NOT_NAMES = {"국제", "해외", "전문", "대표", "소속", "담당", "수습", "예비", "등록", "미국", "유럽", "일본", "중국",
             "상담", "출원", "사무소", "특허", "상표", "변리", "전담", "책임", "광고", "경력", "현직", "출신"}


def _has_attorney_name(text: str) -> bool:
    for rx in NAME_RES:
        for m in rx.finditer(text):
            name = m.group(1)
            if not any(name.startswith(x) or name.endswith(x) for x in NOT_NAMES):
                return True
    return False


def _context(text: str, start: int, end: int, width: int = 40) -> str:
    s = max(0, start - width)
    e = min(len(text), end + width)
    return ("…" if s > 0 else "") + text[s:e].replace("\n", " ") + ("…" if e < len(text) else "")


def screen(text: str) -> list[dict]:
    """광고 문구에서 위반 의심 표현을 찾는다. 같은 규칙의 같은 문구는 한 번만 보고한다."""
    findings: list[dict] = []
    if not text or not text.strip():
        return findings
    seen = set()
    for rule in RULES:
        excludes = [re.compile(x) for x in rule.exclude]
        for pat in rule.patterns:
            for m in re.finditer(pat, text, flags=re.IGNORECASE):
                matched = m.group(0).strip()
                if not matched:
                    continue
                window = text[max(0, m.start() - 10): m.end() + 10]
                if any(x.search(window) for x in excludes):
                    continue
                key = (rule.code, matched)
                if key in seen:
                    continue
                seen.add(key)
                findings.append({
                    "rule_code": rule.code,
                    "rule_label": rule.label,
                    "matched_text": matched,
                    "context": _context(text, m.start(), m.end()),
                    "confidence": rule.confidence,
                    "guide": rule.guide,
                    "refs": [{"source": r.source, "article_no": r.article_no, "item": r.item} for r in rule.refs],
                })
    # 광고 주체 표시(제3조②) — 문구가 충분히 길고 변리사 성명 표기가 없을 때만 신호
    if len(text) >= 80 and not _has_attorney_name(text):
        findings.append({
            "rule_code": "NO_RESPONSIBLE_NAME",
            "rule_label": "광고 주체(변리사·광고책임변리사) 성명 미표시 의심",
            "matched_text": "(성명 표기 없음)",
            "context": "광고 문구 전체에서 '변리사 OOO' 형태의 성명 표기를 찾지 못했습니다.",
            "confidence": "LOW",
            "guide": "사무소 소재지 간판에 명칭·연락처만 표시한 경우는 예외(제3조② 단서). 캡처 원본에서 성명 표기 여부를 확인.",
            "refs": [{"source": "AD_REG", "article_no": "제3조", "item": "제2항"}],
        })
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    findings.sort(key=lambda f: order[f["confidence"]])
    return findings


def rule_catalog() -> list[dict]:
    return [{"code": r.code, "label": r.label, "confidence": r.confidence, "guide": r.guide,
             "refs": [{"source": x.source, "article_no": x.article_no, "item": x.item} for x in r.refs],
             "patterns": r.patterns} for r in RULES]
