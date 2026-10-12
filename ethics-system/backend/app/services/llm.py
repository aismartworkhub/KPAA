"""Claude API 연동(선택 기능) — '근거 제한(grounded)' 모드.

환각 방지 장치
1. 모델에는 시스템이 검색한 조문·선례만 [ID]와 함께 제공한다(외부 지식 사용 금지 지시).
2. 응답은 JSON 스키마(structured outputs)로 강제한다.
3. 응답의 모든 인용은 서버에서 재검증한다.
   - 제공하지 않은 ID를 인용 → 폐기
   - 인용문(quote)이 해당 조문 원문에 실제로 존재하지 않음 → 폐기
   폐기 건수는 화면에 '검증 실패'로 표시된다.
4. API 키가 없거나 호출이 실패하면 규칙·검색 결과만 반환한다(기능 저하, 오류 아님).
"""
import json
import os
import re

from .. import config

_client = None


def available() -> bool:
    return config.AI_ENABLED and bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()
    return _client


class LLMError(Exception):
    pass


def _call_json(system: str, user: str, schema: dict, max_tokens: int = 16000) -> dict:
    import anthropic
    try:
        resp = _get_client().beta.messages.create(
            model=config.AI_MODEL,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": config.AI_EFFORT, "format": {"type": "json_schema", "schema": schema}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.AuthenticationError as e:
        raise LLMError("AI API 인증 실패: API 키를 확인하세요.") from e
    except anthropic.RateLimitError as e:
        raise LLMError("AI API 호출 한도 초과: 잠시 후 다시 시도하세요.") from e
    except anthropic.APIStatusError as e:
        raise LLMError(f"AI API 오류({e.status_code}).") from e
    except anthropic.APIConnectionError as e:
        raise LLMError("AI API 연결 실패: 네트워크를 확인하세요.") from e
    if resp.stop_reason == "refusal":
        raise LLMError("AI가 요청 처리를 거절했습니다. 규칙·검색 결과를 참고하세요.")
    if resp.stop_reason == "max_tokens":
        raise LLMError("AI 응답이 길이 제한으로 잘렸습니다. 입력을 줄여 다시 시도하세요.")
    text = next((b.text for b in resp.content if b.type == "text"), None)
    if not text:
        raise LLMError("AI 응답이 비어 있습니다.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError("AI 응답 형식 오류.") from e


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s or "")


GROUNDED_SYSTEM = """당신은 대한변리사회 회원서비스실의 윤리·광고 사건 검토를 돕는 보조자입니다.
반드시 지켜야 할 원칙:
- 오직 <근거자료>에 제공된 조문과 선례만 사용합니다. 일반 법률 지식, 다른 법령, 기억에 의존한 판례를 쓰지 않습니다.
- 모든 판단에는 근거 ID(예: A12, P3)와 그 원문에서 그대로 복사한 인용문(quote)을 붙입니다. 인용문은 원문 일부를 글자 그대로 옮깁니다.
- 근거자료로 판단할 수 없으면 insufficient=true 로 두고 무엇이 부족한지 missing_info 에 적습니다. 추측하지 않습니다.
- 위반을 '확정'하지 않습니다. '위반 소지', '검토 필요' 수준으로 표현합니다. 최종 판단은 위원회가 합니다.
- 사실관계에 없는 사실을 만들어내지 않습니다."""

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "issues": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "issue": {"type": "string"},
                "article_id": {"type": "string"},
                "quote": {"type": "string"},
                "reasoning": {"type": "string"},
                "likelihood": {"type": "string", "enum": ["높음", "보통", "낮음"]},
            },
            "required": ["issue", "article_id", "quote", "reasoning", "likelihood"],
            "additionalProperties": False,
        }},
        "precedents": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "precedent_id": {"type": "string"},
                "relevance": {"type": "string"},
                "sanction": {"type": "string"},
            },
            "required": ["precedent_id", "relevance", "sanction"],
            "additionalProperties": False,
        }},
        "insufficient": {"type": "boolean"},
        "missing_info": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "issues", "precedents", "insufficient", "missing_info"],
    "additionalProperties": False,
}


def grounded_analysis(facts: str, articles: list[dict], precedents: list[dict]) -> dict:
    """articles: [{id, citation, body}], precedents: [{id, title, holding, sanction_type, ...}]"""
    amap = {f"A{a['id']}": a for a in articles}
    pmap = {f"P{p['id']}": p for p in precedents}
    ctx = ["<근거자료>"]
    for key, a in amap.items():
        ctx.append(f"[{key}] {a['citation']}\n{a['body']}")
    for key, p in pmap.items():
        ctx.append(f"[{key}] 선례: {p['title']} / 징계: {p.get('sanction_type') or '-'} {p.get('sanction_detail') or ''}\n"
                   f"사실: {p.get('facts') or '-'}\n요지: {p.get('holding') or '-'}")
    ctx.append("</근거자료>")
    user = "\n\n".join(ctx) + f"\n\n<사실관계>\n{facts}\n</사실관계>\n\n위 사실관계에 적용될 수 있는 조문과 유사 선례를 근거자료 범위 안에서만 분석하세요."
    raw = _call_json(GROUNDED_SYSTEM, user, ANALYSIS_SCHEMA)

    verified, rejected = [], []
    for it in raw.get("issues", []):
        art = amap.get(it["article_id"])
        if not art:
            rejected.append({**it, "reject_reason": "제공하지 않은 근거 ID"})
        elif not it["quote"].strip() or _norm(it["quote"]) not in _norm(art["body"]):
            rejected.append({**it, "reject_reason": "인용문이 조문 원문에 없음"})
        else:
            verified.append({**it, "citation": art["citation"], "article_db_id": art["id"]})
    precs = []
    for p in raw.get("precedents", []):
        src = pmap.get(p["precedent_id"])
        if not src:
            rejected.append({"issue": "선례 인용", **p, "reject_reason": "제공하지 않은 선례 ID"})
        else:
            precs.append({**p, "title": src["title"], "precedent_db_id": src["id"]})
    return {
        "summary": raw.get("summary", ""),
        "issues": verified,
        "precedents": precs,
        "insufficient": raw.get("insufficient", False),
        "missing_info": raw.get("missing_info", []),
        "rejected": rejected,
        "model": config.AI_MODEL,
    }


MINUTES_SCHEMA = {
    "type": "object",
    "properties": {
        "overview": {"type": "string"},
        "speakers": {"type": "array", "items": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "points": {"type": "array", "items": {"type": "string"}}},
            "required": ["name", "points"], "additionalProperties": False}},
        "resolutions": {"type": "array", "items": {
            "type": "object",
            "properties": {"agenda": {"type": "string"}, "decision": {"type": "string"},
                           "vote": {"type": "string"}, "evidence_quote": {"type": "string"}},
            "required": ["agenda", "decision", "vote", "evidence_quote"], "additionalProperties": False}},
        "follow_ups": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["overview", "speakers", "resolutions", "follow_ups"],
    "additionalProperties": False,
}


def summarize_minutes(transcript: str, agenda: list[str]) -> dict:
    system = ("당신은 위원회 회의록 작성 보조자입니다. 녹취록에 실제로 있는 발언만 정리합니다. "
              "의결사항(resolutions)마다 녹취록에서 그대로 복사한 근거 문장(evidence_quote)을 붙입니다. "
              "녹취록에 의결이 명확하지 않으면 decision 을 '의결 불명확 — 확인 필요'로 적습니다. 추측하지 않습니다.")
    user = "<안건>\n" + "\n".join(f"- {a}" for a in agenda) + f"\n</안건>\n\n<녹취록>\n{transcript}\n</녹취록>"
    raw = _call_json(system, user, MINUTES_SCHEMA)
    tn = _norm(transcript)
    for r in raw.get("resolutions", []):
        r["verified"] = bool(r.get("evidence_quote")) and _norm(r["evidence_quote"]) in tn
    raw["model"] = config.AI_MODEL
    return raw


PRECEDENT_SCHEMA = {
    "type": "object",
    "properties": {
        "cases": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "case_ref": {"type": "string"}, "title": {"type": "string"}, "category": {"type": "string"},
                "sanction_type": {"type": "string"}, "sanction_detail": {"type": "string"},
                "facts": {"type": "string"}, "holding": {"type": "string"}, "related_rules": {"type": "string"},
                "source_quote": {"type": "string"},
            },
            "required": ["case_ref", "title", "category", "sanction_type", "sanction_detail", "facts", "holding",
                         "related_rules", "source_quote"],
            "additionalProperties": False}},
    },
    "required": ["cases"],
    "additionalProperties": False,
}


def extract_precedents(text: str) -> list[dict]:
    """사례집 본문 조각에서 사례별 요지·징계수위를 구조화 추출(검토 후 저장)."""
    system = ("당신은 징계사례집에서 사례를 구조화하는 보조자입니다. 본문에 있는 내용만 옮깁니다. "
              "징계 수위(sanction_type)는 본문 표현 그대로(예: 견책, 과태료 300만원, 정직 1월, 제명). 없으면 '미기재'. "
              "source_quote 에는 징계 결과가 적힌 문장을 본문에서 그대로 복사합니다.")
    raw = _call_json(system, f"<본문>\n{text}\n</본문>", PRECEDENT_SCHEMA)
    tn = _norm(text)
    out = []
    for c in raw.get("cases", []):
        c["verified"] = bool(c.get("source_quote")) and _norm(c["source_quote"]) in tn
        out.append(c)
    return out
