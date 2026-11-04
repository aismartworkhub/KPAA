"""캔바(Canva) 모형 부품 — 캔바 카드뉴스 교안 테스트에서 만든 부품을 일반화한 것. 스타일은 lesson.css의 .cv-* 구역.
사용:  from mocks_canva import canva_home, canva_editor, cv_card, cv_pages_row, cv_stage, cv_text_tool, cv_text_panel, cv_pop, cv_download_pop, cv_share_pop

예) 텍스트 패널을 연 편집 화면, 1번=제목 추가, 2번=카드의 제목
    canva_editor(cv_stage(cv_card(title="하반기 연수 안내", date="11. 25.(수)", marks={"title": 2})),
                 rail_on="텍스트", panel=cv_text_panel(marks={"제목 추가": 1}))
메뉴·버튼 이름은 작성 시점의 한국어 캔바 화면 기준이며 자주 바뀐다 — 교안에 '이름이 다르면 비슷한 이름' 안내와 리허설 권장을 함께 둔다.
"""
from lessonkit import E, mk

EDITOR_RAIL = [("▦", "디자인"), ("◇", "요소"), ("T", "텍스트"), ("©", "브랜드"), ("☁", "업로드 항목"), ("✎", "그리기"), ("▣", "프로젝트"), ("⊞", "앱")]
HOME_RAIL = [("⌂", "홈"), ("▣", "프로젝트"), ("▦", "템플릿"), ("©", "브랜드"), ("✦", "Canva AI"), ("⊞", "앱")]


def cv_rail(items, on=None, marks=None, create=False):
    marks = marks or {}
    out = []
    if create:
        c = '<span class="create"><i>＋</i>만들기</span>'
        out.append(mk(c, marks["만들기"]) if "만들기" in marks else c)
    for ic, label in items:
        s = f'<span class="{"on" if label == on else ""}"><i>{ic}</i>{E(label)}</span>'
        out.append(mk(s, marks[label]) if label in marks else s)
    return f'<div class="cv-rail">{"".join(out)}</div>'


def cv_card(kind="cover", title="", date="", lines=(), org="기관명 · 안내", footer="문의 000-0000", marks=None, sel=(), lock=(),
            small=False, card_mark=None, logo=True, blank=False, bg=None):
    """카드뉴스 한 장. kind='cover'(제목·날짜) / 'detail'(안내 내용 목록).
    marks={'org','logo','title','date','lab','lines','ft': 번호}, sel/lock=같은 키(선택 테두리/잠금 표시), bg='#색'"""
    m = marks or {}

    def part(key, h):
        cls = " ".join(c for c, on in (("sel", key in sel), ("lock", key in lock)) if on)
        h = f'<span class="{cls}">{h}</span>' if cls else h
        return mk(h, m[key]) if key in m else h

    cls = "cv-card" + (" sm" if small else "") + (" blank" if blank else "") + (" mk" if card_mark else "")
    attr = (f' data-n="{card_mark}"' if card_mark else "") + (f' style="background:{bg}"' if bg and not blank else "")
    if blank:
        return f'<div class="{cls}"{attr}></div>'
    h = f'<div class="org">{part("org", E(org))}</div>' if org else ""
    h += f'<div class="logo">{part("logo", "로고")}</div>' if logo else ""
    if kind == "cover":
        h += f'<div class="tt">{part("title", E(title))}</div>' if title else ""
        h += f'<div>{part("date", f"<span class=dt>{E(date)}</span>")}</div>' if date else ""
    else:
        h += f'<div>{part("lab", "<span class=lab>안내 내용</span>")}</div>'
        if lines:
            ul = "<ul>" + "".join(f"<li>{E(x)}</li>" for x in lines) + "</ul>"
            h += mk(ul, m["lines"], block=True) if "lines" in m else ul
    h += f'<div class="ft">{part("ft", E(footer))}</div>' if footer else ""
    return f'<div class="{cls}"{attr}>{h}</div>'


def cv_pop(inner, right=None, left=None, top=6, width=220):
    """편집 화면 위 팝업(공유·다운로드 등) — canva_editor(popup=...)로 넘긴다."""
    pos = f"right:{right}px;" if right is not None else f"left:{left or 8}px;"
    return f'<div class="cv-pop" style="{pos}top:{top}px;width:{width}px">{inner}</div>'


def canva_home(marks=None, popup="", recent=("[원본] 안내 카드뉴스", "제목 없는 디자인")):
    """캔바 홈. marks={'만들기': n, 'search': n, '<왼쪽 메뉴 이름>': n}"""
    marks = marks or {}
    s = '<div class="cvh-search">🔍 디자인·폴더·템플릿 검색</div>'
    s = mk(s, marks["search"], block=True) if "search" in marks else s
    chips = "".join(f"<span><i>{i}</i>{t}</span>" for i, t in (("✦", "맞춤형"), ("▭", "프레젠테이션"), ("♥", "소셜 미디어"), ("▶", "동영상"), ("🖨", "인쇄 제품"), ("⋯", "더 보기")))
    thumbs = ""
    if recent:
        thumbs = '<div class="cvh-recent">최근 디자인</div><div class="cvh-thumbs">' + "".join(
            f'<div><b{"" if i == 0 else " style=background:#d9dce3"}></b>{E(t)}</div>' for i, t in enumerate(recent)) + "</div>"
    main = f'<div class="cvh-main"><h4>오늘은 어떤 디자인을 만들어 볼까요?</h4>{s}<div class="cvh-chips">{chips}</div>{thumbs}</div>'
    return (f'<div class="win-top"><span class="win-icon" style="background:#7d2ae8"></span><span class="win-title">Canva · 홈</span></div>'
            f'<div class="cv-body">{cv_rail(HOME_RAIL, on="홈", marks=marks, create=True)}{main}{popup}</div>')


def canva_editor(stage, title="제목 없는 디자인 - 1080 × 1080px", rail_on=None, rail_marks=None, panel="", tool="",
                 top_marks=None, dd_for=None, popup="", row=False):
    """캔바 편집 화면. stage=cv_stage(...) 또는 cv_pages_row(...), panel=cv_text_panel(...) 등,
    top_marks={'파일': n, '크기 조정': n, 'title': n, 'share': n}, dd_for=('파일', dropdown(...))"""
    tm = top_marks or {}

    def menu(name):
        dd = dd_for[1] if dd_for and dd_for[0] == name else ""
        lab = mk(E(name), tm[name]) if name in tm else E(name)
        return f'<span class="m{" on" if dd or name in tm else ""}">{lab}{dd}</span>'

    ttl = mk(E(title), tm["title"]) if "title" in tm else E(title)
    share = '<span class="share">⇪ 공유</span>'
    share = mk(share, tm["share"]) if "share" in tm else share
    top = (f'<div class="cv-top"><b style="font-size:13px">Canva</b>{menu("파일")}{menu("크기 조정")}{menu("편집")}'
           f'<span>↶ ↷ ☁</span><span class="ttl">{ttl}</span>{share}</div>')
    pnl = f'<div class="cv-panel">{panel}</div>' if panel else ""
    st = f'<div class="cv-stage{" row" if row else ""}">{tool}{stage}</div>'
    return f'{top}<div class="cv-body">{cv_rail(EDITOR_RAIL, on=rail_on, marks=rail_marks)}{pnl}{st}{popup}</div>'


def cv_stage(card_html, page="1페이지", dup_mark=None, add_page=True):
    """페이지 1장 편집 영역(페이지 도구줄 + 카드 + '페이지 추가'). dup_mark: 페이지 복제(⧉) 번호"""
    d = mk("⧉", dup_mark) if dup_mark else "⧉"
    bar = f'<div class="cv-pbar"><span>{E(page)} - 페이지 제목 추가</span><span>⌃ ⌄ 🔒 {d} 🗑 ＋</span></div>'
    return bar + card_html + ('<div class="cv-add">＋ 페이지 추가</div>' if add_page else "")


def cv_pages_row(*cards):
    """여러 페이지를 나란히(canva_editor(row=True)와 함께)"""
    return "".join(f'<div class="cv-pg">{c}{i + 1}페이지</div>' for i, c in enumerate(cards))


def cv_text_tool(font_mark=None, lock_mark=None, color="#ffffff", size="90", font="Noto Sans KR"):
    """글자 선택 시 위쪽 도구줄"""
    f = f'<span class="f">{E(font)} ▾</span><span class="f">− {E(size)} ＋</span><span class="swc" style="background:{color}"></span>'
    f = mk(f, font_mark) if font_mark else f
    lk = mk("🔒", lock_mark) if lock_mark else "🔒"
    return f'<div class="cv-tool">{f}<b>B</b><i>I</i><span>≡</span><span>효과</span><span>⋯</span>{lk}</div>'


def cv_text_panel(marks=None):
    """왼쪽 '텍스트' 패널. marks={'제목 추가': n, '부제목 추가': n, '본문 텍스트 추가': n}"""
    marks = marks or {}

    def b(label, cls):
        h = f'<span class="pbtn {cls}">{E(label)}</span>'
        return mk(h, marks[label]) if label in marks else h

    return ('<div class="ph">텍스트</div><span class="minput">🔍 글꼴 및 조합 검색</span>'
            '<span class="pbtn" style="background:#7d2ae8;color:#fff;text-align:center">T 텍스트 상자 추가</span>'
            '<div style="color:#5f6368;margin-top:8px">기본 텍스트 스타일</div>'
            + b("제목 추가", "big") + b("부제목 추가", "mid") + b("본문 텍스트 추가", ""))


def cv_share_pop(download_mark=None):
    dl = '<span class="ic"><i>⬇</i>다운로드</span>'
    return cv_pop('<div class="ph">이 디자인 공유</div><div style="color:#5f6368">액세스 권한이 있는 사람: 나만</div>'
                  '<div class="row" style="margin-top:10px;justify-content:space-between">'
                  + (mk(dl, download_mark) if download_mark else dl)
                  + '<span class="ic"><i>🔗</i>링크 보기</span><span class="ic"><i>♥</i>소셜 미디어</span><span class="ic"><i>⋯</i>모두 보기</span></div>',
                  right=8, width=260)


def cv_download_pop(pages="1", fmt_mark=None, button_mark=None):
    fmt = '<span class="inp">PNG <small style="color:#7d2ae8">추천</small> ▾</span>'
    btn = '<span class="pbtn">다운로드</span>'
    return cv_pop('<div class="ph">← 다운로드</div><div>파일 형식</div>'
                  + (mk(fmt, fmt_mark, block=True) if fmt_mark else fmt)
                  + '<div style="margin-top:8px">크기 ×1 · 1,080 × 1,080px</div>'
                  + f'<div style="margin-top:8px">페이지 선택</div><span class="inp">모든 페이지 ({E(pages)}) ▾</span>'
                  + (mk(btn, button_mark, block=True) if button_mark else btn), right=8, width=200)
