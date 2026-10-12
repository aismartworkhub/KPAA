"""회의 녹취록(클로바노트 등) 규칙 기반 정리 — AI 키가 없어도 동작.

지원 형식
  1) 클로바노트 내보내기:  '참석자 1 00:03' / '홍길동 01:22' 줄 다음에 발언 내용
  2) '이름: 발언' 또는 '이름 : 발언' 형식
  3) 그 외 자유 메모(화자 '미상'으로 묶음)
"""
import re

HEADER_RE = re.compile(r"^\s*([가-힣A-Za-z0-9 ]{1,12}?)\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*$")
COLON_RE = re.compile(r"^\s*([가-힣A-Za-z0-9 ]{1,12}?)\s*[:：]\s*(.+)$")
SENT_SPLIT = re.compile(r"(?<=[.?!다요])\s+")

KEY_WORDS = ["위반", "징계", "시정", "소명", "의견", "판단", "생각", "동의", "반대", "제안", "필요", "검토",
             "경고", "견책", "과태료", "정직", "제명", "기각", "보류", "상정", "규정", "조항"]
DECISION_RE = re.compile(r"(의결|가결|부결|결정하|결정되|하기로\s*(하|했|함|합)|만장일치|찬성\s*\d|반대\s*\d|기각하|보류하|회부하기로|시정\s*요구하기로)")
FOLLOW_RE = re.compile(r"(하기로|요청하기로|통보|발송|송부|까지\s*(제출|회신)|다음\s*회의|차기\s*회의|재상정)")


def parse_utterances(transcript: str) -> list[tuple[str, str]]:
    utts: list[tuple[str, str]] = []
    speaker = None
    buf: list[str] = []

    def flush():
        nonlocal buf
        if buf:
            utts.append((speaker or "미상", " ".join(buf).strip()))
        buf = []

    for line in transcript.splitlines():
        if not line.strip():
            continue
        m = HEADER_RE.match(line)
        if m:
            flush()
            speaker = m.group(1).strip()
            continue
        m = COLON_RE.match(line)
        if m and not re.match(r"^\d", m.group(1)):
            flush()
            speaker = m.group(1).strip()
            buf.append(m.group(2).strip())
            continue
        buf.append(line.strip())
    flush()
    return [(s, t) for s, t in utts if t]


def _score(sentence: str) -> float:
    return sum(2 for k in KEY_WORDS if k in sentence) + min(len(sentence), 120) / 60


def summarize(transcript: str, agenda: list[str] | None = None, per_speaker: int = 4) -> dict:
    utts = parse_utterances(transcript)
    by_speaker: dict[str, list[str]] = {}
    resolutions, follow_ups = [], []
    for speaker, text in utts:
        for sent in SENT_SPLIT.split(text):
            sent = sent.strip()
            if len(sent) < 6:
                continue
            by_speaker.setdefault(speaker, []).append(sent)
            if FOLLOW_RE.search(sent) and re.search(r"(통보|발송|송부|제출|회신|차기|다음\s*회의)", sent):
                follow_ups.append({"speaker": speaker, "text": sent})
            elif DECISION_RE.search(sent):
                resolutions.append({"speaker": speaker, "text": sent})
            elif FOLLOW_RE.search(sent):
                follow_ups.append({"speaker": speaker, "text": sent})
    speakers = []
    for name, sents in by_speaker.items():
        top = sorted(sents, key=_score, reverse=True)[:per_speaker]
        top.sort(key=sents.index)    # 원래 발언 순서 유지
        speakers.append({"name": name, "utterance_count": len(sents), "points": top})
    return {
        "method": "rule",
        "speakers": speakers,
        "resolutions": resolutions,
        "follow_ups": follow_ups,
        "agenda": agenda or [],
        "notice": "규칙 기반 자동 정리입니다. 의결사항은 반드시 녹취 원문과 대조해 확정하세요.",
    }


def to_minutes_text(meeting: dict, items: list[dict], summary: dict) -> str:
    """회의록 초안 텍스트(위원장 결재용)."""
    lines = [f"{meeting['title']} 회의록(안)", "",
             f"1. 일시: {meeting.get('scheduled_at') or '-'}",
             f"2. 장소: {meeting.get('location') or '-'}"]
    members = meeting.get("members_list") or []
    attend = [m["name"] for m in members if m.get("attend")]
    absent = [m["name"] for m in members if m.get("attend") is False]
    lines.append(f"3. 참석: {', '.join(attend) or '-'}" + (f" (불참: {', '.join(absent)})" if absent else ""))
    lines += ["", "4. 안건 및 의결사항"]
    decision_labels = {"PENDING": "심의 중", "CORRECTION": "시정 요구", "WARNING": "경고", "DISCIPLINE_REFERRAL": "징계위원회 회부",
                       "DISMISS": "종결(혐의 없음·자진 시정)", "DEFER": "보류(차기 재상정)", "EXTERNAL": "외부기관 이관"}
    for it in items:
        vote = ""
        if it.get("vote_for") is not None:
            vote = f" (찬성 {it['vote_for']}, 반대 {it.get('vote_against') or 0})"
        lines.append(f"  제{it['seq']}호 안건: {it['title']}")
        lines.append(f"    - 의결: {decision_labels.get(it['decision'], it['decision'])}{vote}")
        if it.get("decision_note"):
            lines.append(f"    - 비고: {it['decision_note']}")
    lines += ["", "5. 주요 발언 요지"]
    for sp in summary.get("speakers", []):
        lines.append(f"  ○ {sp['name']}")
        for p in sp.get("points", []):
            lines.append(f"    - {p}")
    if summary.get("resolutions"):
        lines += ["", "6. 녹취상 의결 관련 발언(대조용)"]
        for r in summary["resolutions"]:
            text = r.get("text") or f"{r.get('agenda', '')}: {r.get('decision', '')}"
            lines.append(f"  - [{r.get('speaker', '')}] {text}")
    if summary.get("follow_ups"):
        lines += ["", "7. 후속 조치"]
        for f in summary["follow_ups"]:
            lines.append(f"  - {f['text'] if isinstance(f, dict) else f}")
    lines += ["", "위 회의록 내용이 사실과 같음을 확인합니다.", "", "위원장            (서명)", "간  사            (서명)"]
    return "\n".join(lines)
