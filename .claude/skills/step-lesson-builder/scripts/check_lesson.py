"""교안 정적 점검 — 브라우저 없이(Python만) 실행. Claude 대화창(코드 실행 환경)에서도 동작.
사용: python3 check_lesson.py <교안폴더 또는 index.html>
점검: 탭·페이지 짝, 단계 구성(목표·번호 순서·성공하면), 그림 한 장 안 번호 중복·번호 > 따라 하기 수, 그림 ID 중복, 촬영 목록 자리,
      복사 버튼 대상, 로컬 링크 파일 존재, 미리보기(og) 태그, 휴대폰 대응 코드 포함.
브라우저 점검(scripts/check_lesson.mjs)이 가능한 환경이면 그것도 함께 실행할 것 — 실제 화면 잘림은 그쪽에서만 보인다.
"""
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.tabs, self.pages, self.figs, self.ids = [], [], [], []
        self.copy_targets, self.links, self.meta = [], [], {}
        self.steps = []           # 각 단계: {'no','goal','todo','ok','marks':[]}
        self.cur_step = None
        self.depth_step = None
        self.in_do = 0
        self.shotlist = False
        self.wrap_depth = []      # 열린 .wrap 의 깊이들
        self.outside = []         # wrap 밖 단계
        self.cur_fig = None       # 현재 그림의 번호 목록
        self.depth_fig = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        self.stack.append(tag)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "button" and "tab" in cls:
            self.tabs.append(a.get("data-p"))
        if tag == "main" and "page" in cls:
            self.pages.append(a.get("id"))
        if tag == "figure" and "shot" in cls:
            self.figs.append(a.get("data-shot"))
            self.cur_fig = {"id": a.get("data-shot"), "ns": []}
            if self.cur_step is not None:
                self.cur_step.setdefault("figs", []).append(self.cur_fig)
            self.depth_fig = len(self.stack)
        if a.get("data-copy"):
            self.copy_targets.append(a["data-copy"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag == "meta" and (a.get("property") or a.get("name")):
            self.meta[a.get("property") or a.get("name")] = a.get("content", "")
        if a.get("id") == "shotlist":
            self.shotlist = True
        if tag == "div" and "wrap" in cls:
            self.wrap_depth.append(len(self.stack))
        if tag == "section" and "step" in cls and not self.wrap_depth:
            self.outside.append((a.get("id") or "")[1:])
        if tag == "section" and "step" in cls:
            self.cur_step = {"no": (a.get("id") or "")[1:], "goal": False, "todo": 0, "ok": False, "marks": []}
            self.steps.append(self.cur_step)
            self.depth_step = len(self.stack)
        if self.cur_step is not None:
            if "goal" in cls:
                self.cur_step["goal"] = True
            if "okline" in cls:
                self.cur_step["ok"] = True
            if tag == "ol" and "do" in cls:
                self.in_do = len(self.stack)
            if tag == "li" and self.in_do and len(self.stack) == self.in_do + 1:
                self.cur_step["todo"] += 1
            if "mk" in cls and a.get("data-n", "").isdigit():
                self.cur_step["marks"].append(int(a["data-n"]))
                if self.cur_fig is not None:
                    self.cur_fig["ns"].append(int(a["data-n"]))

    def handle_endtag(self, tag):
        if self.stack:
            if self.in_do and len(self.stack) == self.in_do and tag == "ol":
                self.in_do = 0
            if self.wrap_depth and len(self.stack) == self.wrap_depth[-1] and tag == "div":
                self.wrap_depth.pop()
            if self.depth_fig and len(self.stack) == self.depth_fig and tag == "figure":
                self.cur_fig = None
                self.depth_fig = None
            if self.depth_step and len(self.stack) == self.depth_step and tag == "section":
                self.cur_step = None
                self.depth_step = None
            self.stack.pop()


def main(arg):
    p = Path(arg)
    f = p / "index.html" if p.is_dir() else p
    root = f.parent
    src = f.read_text(encoding="utf-8")
    parser = P()
    parser.feed(src)
    errors, warns = [], []

    if parser.outside:
        errors.append(f"단계 카드가 본문 상자(wrap) 밖에 있음: STEP {parser.outside} — wrap(...) 괄호 위치 확인")
    if set(parser.tabs) != set(parser.pages):
        errors.append(f"탭과 페이지 id가 맞지 않음: 탭 {parser.tabs} / 페이지 {parser.pages}")
    dups = sorted({x for x in parser.figs if parser.figs.count(x) > 1})
    if dups:
        errors.append(f"그림 ID 중복: {dups}")
    if parser.figs and not parser.shotlist:
        warns.append("부록에 촬영 목록 자리(shot_list_section())가 없음")
    for t in parser.copy_targets:
        if t not in parser.ids:
            errors.append(f"복사 버튼 대상 id 없음: {t}")
    for s in parser.steps:
        tag = f"STEP {s['no']}"
        if not s["goal"]:
            warns.append(f"{tag}: 목표(🎯) 없음")
        if s["todo"] == 0:
            errors.append(f"{tag}: 따라 하기 번호 목록 없음")
        if not s["ok"]:
            warns.append(f"{tag}: '성공하면' 없음")
        for fg in s.get("figs", []):
            d = sorted({n for n in fg["ns"] if fg["ns"].count(n) > 1})
            if d:
                warns.append(f"{tag} 그림 {fg['id']}: 같은 번호 {d}가 두 곳 — '누를 곳 + 결과'처럼 의도한 게 아니면 하나 지우기")
            if fg["ns"] and max(fg["ns"]) > s["todo"]:
                warns.append(f"{tag} 그림 {fg['id']}: 번호 {max(fg['ns'])} > 따라 하기 {s['todo']}개 — 글 번호와 대응 확인")
    for href in parser.links:
        if href.startswith(("http", "#", "mailto:")) or not href:
            continue
        if not (root / unquote(href.split("#")[0])).exists():
            errors.append(f"링크한 파일 없음: {href}")
    if "viewport" not in parser.meta:
        errors.append("viewport 메타 태그 없음(휴대폰 표시 깨짐)")
    if "og:image" in parser.meta:
        img = parser.meta["og:image"]
        if not img.startswith("http"):
            errors.append("og:image는 절대 주소(https://…)여야 카카오톡이 읽음")
        name = img.rsplit("/", 1)[-1]
        if not (root / name).exists():
            warns.append(f"미리보기 이미지 파일이 교안 폴더에 없음: {name}")
    else:
        warns.append("미리보기(og) 태그 없음 — 링크 공유 시 이미지·제목이 안 나옴")
    for needle, what in (("fitMocks", "휴대폰 그림 맞춤"), ("openLightbox", "탭 확대"), ("pc-note", "PC 실습 안내 스타일")):
        if needle not in src:
            errors.append(f"휴대폰 대응 코드 누락: {what}")

    print(f"탭 {len(parser.tabs)}개 · 단계 {len(parser.steps)}개 · 그림 {len(parser.figs)}개 · 복사 상자 {len(parser.copy_targets)}개 · 파일 {f.stat().st_size // 1024}KB")
    for e in errors:
        print("❌", e)
    for w in warns:
        print("⚠", w)
    if not errors and not warns:
        print("문제 없음 ✓")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
