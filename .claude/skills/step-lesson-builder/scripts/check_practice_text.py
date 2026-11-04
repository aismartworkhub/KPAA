"""실습 문구·예시 파일 점검(코드 없는 교안용) — 테스트 교안 2개에서 반복된 점검을 범용으로 묶은 것.
사용:
  python3 check_practice_text.py --year 2026 practice/*.txt practice/*.csv        # 요일·개인정보 점검
  python3 check_practice_text.py --facts practice/원문.txt practice/예시답.txt      # 예시 답이 원문 사실(날짜·시각·숫자)을 지켰는지
  python3 check_practice_text.py --maxlen 15 --lines 3 practice/카드문구.txt       # 줄 길이·줄 수 제한(카드뉴스 등)
점검
- 요일: '11. 26.(목)', '2026. 11. 26.(목)', '11월 26일(목)' 표기의 요일이 달력과 맞는지(--year 기준, 연도가 적혀 있으면 그 연도)
- 개인정보 의심: 휴대폰 번호(010-0000-xxxx 같은 가짜 형식은 통과), 이메일(example.com/test 도메인은 통과), 주민등록번호 형식
- 사실 대조: 예시 답에 나온 날짜·시각·숫자가 원문에 모두 있는지(AI가 사실을 바꾸지 않았는지 보여주는 예시여야 하므로)
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path

WD = "월화수목금토일"
FAKE_EMAIL = re.compile(r"@(example\.(com|org|net)|test\.|.*\.test$|.*\.invalid$)")


def read(p):
    raw = Path(p).read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


def check_weekdays(name, text, year):
    errs = []
    pats = [r"(?:(\d{4})\.\s*)?(\d{1,2})\.\s*(\d{1,2})\.\s*\(([월화수목금토일])\)",
            r"(?:(\d{4})년\s*)?(\d{1,2})월\s*(\d{1,2})일\s*\(([월화수목금토일])\)"]
    n = 0
    for pat in pats:
        for m in re.finditer(pat, text):
            y = int(m.group(1)) if m.group(1) else year
            try:
                d = date(y, int(m.group(2)), int(m.group(3)))
            except ValueError:
                errs.append(f"{name}: 없는 날짜 '{m.group(0)}'")
                continue
            n += 1
            if WD[d.weekday()] != m.group(4):
                errs.append(f"{name}: '{m.group(0)}' → {y}년 기준 실제는 ({WD[d.weekday()]})")
    return errs, n


def check_personal(name, text):
    errs = []
    for m in re.finditer(r"01[016789][-\s.]?(\d{3,4})[-\s.]?(\d{4})", text):
        if m.group(1).strip("0") and not m.group(1).startswith("0000"):
            errs.append(f"{name}: 실제 휴대폰 번호로 보임 '{m.group(0)}' — 010-0000-xxxx 형식 권장")
    for m in re.finditer(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", text):
        if not FAKE_EMAIL.search(m.group(0)):
            errs.append(f"{name}: 실제 이메일로 보임 '{m.group(0)}' — example.com 권장")
    for m in re.finditer(r"\b\d{6}-[1-4]\d{6}\b", text):
        errs.append(f"{name}: 주민등록번호 형식 '{m.group(0)}'")
    return errs


def facts(text):
    t = re.sub(r"\s+", "", text)
    out = set(re.findall(r"\d{1,2}\.\d{1,2}\.", t))                    # 11.26.
    out |= {f"{a}.{b}." for a, b in re.findall(r"(\d{1,2})월(\d{1,2})일", t)}
    out |= set(re.findall(r"\d{1,2}:\d{2}", t))                          # 13:30
    out |= {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:원|명|건|시간|분|일|%)", t)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--year", type=int, default=date.today().year)
    ap.add_argument("--facts", nargs=2, metavar=("원문", "예시답"))
    ap.add_argument("--maxlen", type=int)
    ap.add_argument("--lines", type=int)
    a = ap.parse_args()
    errs, total = [], 0
    for f in a.files:
        text = read(f)
        e, n = check_weekdays(Path(f).name, text, a.year)
        errs += e
        total += n
        errs += check_personal(Path(f).name, text)
        if a.maxlen or a.lines:
            ls = [l for l in text.splitlines() if l.strip()]
            if a.lines and len(ls) > a.lines:
                errs.append(f"{Path(f).name}: {len(ls)}줄 > {a.lines}줄")
            for l in ls:
                if a.maxlen and len(l.strip()) > a.maxlen:
                    errs.append(f"{Path(f).name}: {len(l.strip())}자 > {a.maxlen}자 — '{l.strip()[:30]}'")
    if a.facts:
        src, ans = facts(read(a.facts[0])), facts(read(a.facts[1]))
        extra = sorted(ans - src)
        if extra:
            errs.append(f"예시 답에 원문에 없는 날짜·시각·숫자: {extra}")
        print(f"사실 대조: 예시 답 {len(ans)}개 중 원문에 있는 것 {len(ans & src)}개")
    if a.files:
        print(f"파일 {len(a.files)}개 · 날짜-요일 표기 {total}곳 확인")
    for e in errs:
        print("❌", e)
    print("문제 없음 ✓" if not errs else f"문제 {len(errs)}건")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
