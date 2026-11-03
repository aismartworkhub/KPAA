"""법령·회규 텍스트를 조문 단위로 분해한다.

입력 형식(HWP에서 추출한 텍스트 기준):
  < 변리사법 >            ← 규정 구분 머리표
  제1조(목적) 본문...      ← 조문 시작
  제1장 총칙               ← 장 구분
  부  칙 (2023. 5. 19.)    ← 부칙 시작 (이후 조문은 '부칙(...) 제N조'로 저장)
"""
import re

SOURCE_CODES = {
    "변리사법": "PAA",
    "윤리강령": "ETHICS",
    "윤리위원회 운영 규정": "ETHICS_COMMITTEE",
    "징계위원회 운영 규정": "DISCIPLINE_COMMITTEE",
    "변리사 광고에 관한 규정": "AD_REG",
}
SOURCE_LABELS = {
    "PAA": "변리사법",
    "ETHICS": "윤리강령·윤리규정",
    "ETHICS_COMMITTEE": "윤리위원회 운영 규정",
    "DISCIPLINE_COMMITTEE": "징계위원회 운영 규정",
    "AD_REG": "변리사 광고에 관한 규정",
}

HEADER_RE = re.compile(r"^<\s*(.+?)\s*>\s*$")
ARTICLE_RE = re.compile(r"^(제\d+조(?:의\d+)?)\s*(?:[(\[]([^)\]]*)[)\]])?\s*(.*)$")
CHAPTER_RE = re.compile(r"^제\d+장\s*.*$")
ADDENDA_RE = re.compile(r"^부\s*칙\s*(.*)$")


def _code_for(name: str) -> str:
    if name in SOURCE_CODES:
        return SOURCE_CODES[name]
    slug = re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_").upper()
    return "CUSTOM_" + (slug or str(abs(hash(name)) % 100000))


def parse(text: str, default_source_name: str | None = None) -> list[dict]:
    """조문 사전 리스트를 반환한다: source, source_name, chapter, article_no, title, body, sort_order."""
    articles: list[dict] = []
    source_name = default_source_name
    source = _code_for(source_name) if source_name else None
    chapter = None
    addenda = None
    preamble: list[str] = []
    cur: dict | None = None
    order = 0

    def flush():
        nonlocal cur, preamble
        if cur:
            cur["body"] = "\n".join(cur.pop("_lines")).strip()
            if cur["body"] or cur["title"]:
                articles.append(cur)
            cur = None
        if preamble and source:
            body = "\n".join(preamble).strip()
            if body:
                articles.append(_mk(source, source_name, None, addenda or "전문", None, body))
            preamble = []

    def _mk(src, sname, chap, no, title, body):
        nonlocal order
        order += 1
        return {"source": src, "source_name": SOURCE_LABELS.get(src, sname), "chapter": chap,
                "article_no": no, "title": title, "body": body, "sort_order": order}

    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        m = HEADER_RE.match(stripped)
        if m:
            flush()
            source_name = m.group(1)
            source = _code_for(source_name)
            chapter = None
            addenda = None
            continue
        if source is None:
            continue
        if ADDENDA_RE.match(stripped) and len(stripped) < 40:
            flush()
            addenda = "부칙" + (" " + ADDENDA_RE.match(stripped).group(1).strip() if ADDENDA_RE.match(stripped).group(1).strip() else "")
            continue
        if CHAPTER_RE.match(stripped) and len(stripped) < 40 and not line.startswith(" "):
            flush()
            chapter = stripped
            continue
        m = ARTICLE_RE.match(stripped)
        if m and not line.startswith(" "):
            if cur is None and preamble:
                flush()
            elif cur is not None:
                flush()
            no = m.group(1) if not addenda else f"{addenda} {m.group(1)}"
            cur = _mk(source, source_name, chapter, no, (m.group(2) or "").strip() or None, "")
            cur["_lines"] = [m.group(3)] if m.group(3) else []
            continue
        if cur is not None:
            cur["_lines"].append(stripped)
        else:
            preamble.append(stripped)
    flush()

    # (source, article_no) 중복 방지 — 같은 부칙 표기가 반복되는 경우 일련번호를 붙인다.
    seen: dict[tuple, int] = {}
    for a in articles:
        key = (a["source"], a["article_no"])
        if key in seen:
            seen[key] += 1
            a["article_no"] = f"{a['article_no']} ({seen[key]})"
        else:
            seen[key] = 1
    return articles


def cite(article: dict) -> str:
    """'변리사 광고에 관한 규정 제7조(주로 취급하는 업무광고)' 형태의 인용 표기."""
    t = f"({article['title']})" if article.get("title") else ""
    return f"{article['source_name']} {article['article_no']}{t}"
