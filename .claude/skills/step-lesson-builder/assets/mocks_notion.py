"""노션(Notion) 모형 부품 — 데이터베이스(표·보드)·속성 메뉴·페이지 열기·필터·수식 편집기·가져오기.
사용: from mocks_notion import *   그리고 build(..., extra_css=NT_CSS)
메뉴·버튼 이름은 작성 시점의 한국어 노션 화면 기준(실제 계정으로 확인하지 못함) — 교안에 대안 이름과 리허설 권장을 함께 둔다.
노션 회원 문의 관리 교안 테스트에서 만든 부품을 일반화한 것. 사이드바 항목은 nt_side(items=make_side(...))로 바꾼다.
"""
from lessonkit import E, mk

# 속성 유형 → 머리글 아이콘
TYPE_ICON = {"title": "Aa", "text": "≡", "select": "▾", "status": "◐", "person": "👤", "date": "📅",
             "formula": "Σ", "id": "#", "created": "🕒"}
# 선택 값 색(노션 기본 색 이름과 비슷하게)
PILL = {"gray": ("#e3e2e0", "#32302c"), "blue": ("#d3e5ef", "#183347"), "green": ("#dbeddb", "#1c3829"),
        "orange": ("#fadec9", "#49290e"), "purple": ("#e8deee", "#412454"), "pink": ("#f5e0e9", "#4c2337"),
        "yellow": ("#fdecc8", "#402c1b"), "red": ("#ffe2dd", "#5d1715"), "brown": ("#eee0da", "#442a1e")}
OPT_COLOR = {"홈페이지": "blue", "전화": "green", "이메일": "purple",
             "회비": "yellow", "연수": "orange", "회원정보": "blue", "증명서": "pink", "행사": "green", "기타": "gray"}
STATUS = {"시작 전": "gray", "접수": "gray", "진행 중": "blue", "처리 중": "blue", "완료": "green", "답변 완료": "green"}
DOT = {"gray": "#91918e", "blue": "#2e7cd1", "green": "#448361"}


class Raw(str):
    """표 칸에 HTML을 그대로 넣을 때: Raw('<b>..</b>')"""


def pill(text, color=None):
    bg, fg = PILL[color or OPT_COLOR.get(text, "gray")]
    return f'<span class="nt-pill" style="background:{bg};color:{fg}">{E(text)}</span>'


def status_pill(text):
    c = STATUS.get(text, "gray")
    bg, fg = PILL[c]
    return f'<span class="nt-pill st" style="background:{bg};color:{fg}"><i style="background:{DOT[c]}"></i>{E(text)}</span>'


def person(name):
    return f'<span class="nt-person"><i>{E(name[:1])}</i>{E(name)}</span>'


def nt_date(iso):
    if not iso:
        return ""
    y, m, d = iso.split("-")
    return f"{y}년 {int(m)}월 {int(d)}일"


def cell(kind, v):
    if v in ("", None):
        return ""
    if isinstance(v, Raw):
        return v
    if kind == "select":
        return pill(v)
    if kind == "status":
        return status_pill(v)
    if kind == "person":
        return person(v)
    if kind == "date":
        return E(nt_date(v)) if "-" in v else E(v)
    if kind == "title":
        return f'<b class="nt-tt">{E(v)}</b>'
    return E(v)


# ───────── 창(사이드바 + 상단 줄) ─────────
def make_side(workspace="내 워크스페이스", team_pages=("📢 공지",), my_pages=("📄 실습",), db="🗂 데이터베이스"):
    """사이드바 항목 목록 만들기 — 교안 주제에 맞게 이름을 바꿔 nt_window(side_items=...)에 넘긴다."""
    return ([("ws", workspace), ("it", "🔍 검색"), ("it", "🏠 홈"), ("it", "📥 받은 편지함"), ("hd", "팀스페이스")]
            + [("it", t) for t in team_pages] + [("hd", "개인 페이지")] + [("it", t) for t in my_pages]
            + ([("sub", db)] if db else []) + [("bot", "⚙ 설정"), ("bot", "📦 템플릿"), ("bot", "⬇ 가져오기"), ("bot", "🗑 휴지통")])


SIDE = make_side()


def nt_side(on=None, marks=None, items=None, hide=()):
    """왼쪽 사이드바. marks={'⬇ 가져오기':1, '＋개인 페이지':1}, hide=('🗂 회원 문의 접수대장',)"""
    marks = marks or {}
    out, bot = [], []
    for kind, label in (items or SIDE):
        if label in hide:
            continue
        if kind == "hd" and label in marks:
            out.append(mk(f'<div class="hd"><span>{E(label)}</span><span>＋</span></div>', marks[label], block=True))
            continue
        if kind == "hd":
            plus = mk("＋", marks["＋" + label]) if "＋" + label in marks else "＋"
            out.append(f'<div class="hd"><span>{E(label)}</span><span>{plus}</span></div>')
            continue
        cls = {"ws": "ws", "sub": "it sub", "bot": "it"}.get(kind, "it") + (" on" if label == on else "")
        h = f'<div class="{cls}">{E(label)}{" ▾" if kind == "ws" else ""}</div>'
        h = mk(h, marks[label], block=True) if label in marks else h
        (bot if kind == "bot" else out).append(h)
    return f'<div class="nt-side">{"".join(out)}<div class="bot">{"".join(bot)}</div></div>'


def nt_window(body, crumbs=("실습", "데이터베이스"), side=True, side_on="🗂 데이터베이스", side_marks=None,
              side_hide=(), top_marks=None, overlay="", min_h=300, side_items=None):
    """노션 화면 전체. top_marks={'공유':1,'•••':2}"""
    tm = top_marks or {}

    def t(k, h):
        return mk(h, tm[k]) if k in tm else h
    cr = " / ".join(E(c) for c in crumbs)
    top = (f'<div class="nt-top"><span class="cr">{cr}</span>{t("공유", "<span>공유</span>")}<span>☆</span>'
           f'{t("•••", "<span>•••</span>")}</div>')
    sd = nt_side(side_on, side_marks, items=side_items, hide=side_hide) if side else ""
    return (f'<div class="nt{"" if side else " noside"}" style="min-height:{min_h}px">{sd}'
            f'<div class="nt-main">{top}{body}{overlay}</div></div>')


def nt_page(title, inner="", icon="", title_mark=None, placeholder=False):
    t = f'{icon + " " if icon else ""}{E(title) if title else "<span class=ph>새 페이지</span>"}'
    t = mk(t, title_mark) if title_mark else t
    return f'<div class="nt-pg"><h1>{t}</h1>{inner}</div>'


# ───────── 데이터베이스 ─────────
def nt_vbar(views=("표",), view_on=None, view_marks=None, tool_marks=None, new_btn=True):
    """보기 탭 줄 + 오른쪽 도구(필터·정렬·•••·새로 만들기)"""
    vm, tm = view_marks or {}, tool_marks or {}
    view_on = view_on or views[0]
    vicon = {"표": "▦", "보드": "▥", "캘린더": "▤", "리스트": "☰"}
    vt = []
    for v in views:
        ic = "" if v[:1] in "▦▥▤☰" else vicon.get(v.split()[0], "▦") + " "
        s = f'<span class="{"on" if v == view_on else ""}">{ic}{E(v)}</span>'
        vt.append(mk(s, vm[v]) if v in vm else s)
    vt.append(mk("<span>＋</span>", vm["＋"]) if "＋" in vm else "<span>＋</span>")

    def tl(k, h):
        return mk(h, tm[k]) if k in tm else h
    tools = (tl("필터", "<span>필터</span>") + tl("정렬", "<span>정렬</span>") + "<span>⚡</span><span>🔍</span>"
             + tl("•••", "<span>•••</span>") + (tl("새로 만들기", '<span class="new">새로 만들기 ▾</span>') if new_btn else ""))
    return f'<div class="nt-vbar"><div class="nt-views">{"".join(vt)}</div><div class="nt-tools">{tools}</div></div>'


def nt_db(cols, rows, name="데이터베이스", views=("표",), view_on=None, view_marks=None, tool_marks=None,
          col_marks=None, cell_marks=None, add_row_mark=None, name_mark=None, widths=None, plus_col=True, new_btn=True,
          calc=None):
    """cols=[(속성 이름, 유형)], rows=[[값,...]] 값은 유형에 따라 자동 표시(선택→색 꼬리표, 상태→점 꼬리표, 사람→아바타, 날짜).
    view_marks={'＋':1, '보드':2} / tool_marks={'필터':1,'정렬':2,'•••':3,'새로 만들기':4} / col_marks={'속성 이름' 또는 '＋': n}
    cell_marks={(행, 열): n} / widths=[px,...]"""
    cm, celm = col_marks or {}, cell_marks or {}
    bar = nt_vbar(views, view_on, view_marks, tool_marks, new_btn)
    nm = f'<div class="nt-dbname">{mk(E(name), name_mark) if name_mark else E(name)}</div>' if name else ""
    cg = "".join(f'<col style="width:{w}px">' for w in widths) if widths else ""
    th = []
    for n, k in cols:
        h = f'<span class="ti">{TYPE_ICON.get(k, "≡")}</span>{E(n)}'
        th.append(f'<th class="{"vis" if n in cm else ""}">{mk(h, cm[n]) if n in cm else h}</th>')
    if plus_col:
        th.append(f'<th class="plus{" vis" if "＋" in cm else ""}">{mk("＋", cm["＋"]) if "＋" in cm else "＋"}</th>')
    trs = []
    for i, r in enumerate(rows):
        tds = []
        for j, (n, k) in enumerate(cols):
            v = r[j] if j < len(r) else ""
            h = cell(k, v)
            if (i, j) in celm:
                tds.append(f'<td class="vis">{mk(h or "&nbsp;&nbsp;&nbsp;", celm[(i, j)])}</td>')
            else:
                tds.append(f"<td>{h}</td>")
        if plus_col:
            tds.append("<td></td>")
        trs.append("<tr>" + "".join(tds) + "</tr>")
    add = '<span class="nt-add">＋ 새 페이지</span>'
    add = mk(add, add_row_mark) if add_row_mark else add
    if calc:  # ('개수 12', 번호)
        c = f'<span class="nt-calc">{E(calc[0])}</span>'
        add = f'<div class="nt-foot">{add}{mk(c, calc[1]) if calc[1] else c}</div>'
    if plus_col:
        cg += '<col style="width:28px">' if widths else ""
    return (f'<div class="nt-db">{nm}{bar}'
            f'<table class="nt-tbl">{f"<colgroup>{cg}</colgroup>" if cg else ""}<tr>{"".join(th)}</tr>{"".join(trs)}</table>{add}</div>')


def nt_board(groups, name="데이터베이스", views=("표", "처리 상태별"), view_on="처리 상태별", view_marks=None,
             tool_marks=None, card_marks=None, group_marks=None):
    """보드 보기. groups=[(상태 이름, [(카드 제목, [작은 줄 HTML,...]), ...])], card_marks={(그룹, 카드): n}, group_marks={그룹: n}"""
    cmk, gmk = card_marks or {}, group_marks or {}
    nm = f'<div class="nt-dbname">{E(name)}</div>' if name else ""
    head = f'<div class="nt-db board">{nm}{nt_vbar(views, view_on, view_marks, tool_marks)}</div>'
    colhtml = []
    for gi, grp in enumerate(groups):
        g, cards_ = grp[0], grp[1]
        cnt = grp[2] if len(grp) > 2 else len(cards_)
        gh = f'<div class="gh">{status_pill(g)} <small>{cnt}</small></div>'
        gh = mk(gh, gmk[gi], block=True) if gi in gmk else gh
        cs = []
        for ci, (t, lines) in enumerate(cards_):
            c = f'<div class="nt-card"><b>{E(t)}</b>{"".join(f"<div>{x}</div>" for x in lines)}</div>'
            cs.append(mk(c, cmk[(gi, ci)], block=True) if (gi, ci) in cmk else c)
        colhtml.append(f'<div class="nt-col">{gh}{"".join(cs)}<div class="nt-add">＋ 새 페이지</div></div>')
    return head + f'<div class="nt-board">{"".join(colhtml)}</div>'


# ───────── 떠 있는 메뉴·창 ─────────
def nt_pop(items, top=40, left=None, right=None, width=220, search=None, title=None):
    """떠 있는 메뉴. items: '#머리글', '-'(구분선), '항목', ('항목', 번호), ('항목', 번호, '설명') / 번호 None이면 표시 없음"""
    out = []
    if title:
        out.append(f'<div class="pt">{E(title)}</div>')
    if search is not None:
        out.append(f'<div class="ps">{search if search else "<span class=ph>검색…</span>"}</div>')
    for it in items:
        if it == "-":
            out.append("<hr>")
            continue
        if isinstance(it, str) and it.startswith("#"):
            out.append(f'<div class="ph2">{E(it[1:])}</div>')
            continue
        text, n, sub = (it + (None, None))[:3] if isinstance(it, tuple) else (it, None, None)
        body = E(text) + (f"<small>{E(sub)}</small>" if sub else "")
        out.append(f'<div class="pi{" on" if n else ""}">{mk(body, n) if n else body}</div>')
    pos = f"top:{top}px;" + (f"right:{right}px;" if right is not None else f"left:{left if left is not None else 40}px;")
    return f'<div class="nt-pop" style="{pos}width:{width}px">{"".join(out)}</div>'


def nt_peek(title, props, body_html="", marks=None, width="64%"):
    """오른쪽에서 열리는 페이지(사이드 보기). props=[(유형, 이름, 값)] 값은 유형에 맞게 자동 표시. marks={'title' 또는 속성 이름: n}"""
    m = marks or {}
    rows = []
    for k, n, v in props:
        val = cell(k, v) if v not in ("", None) else '<span class="ph">비어 있음</span>'
        val = mk(val, m[n], block=(k == "text")) if n in m else val
        rows.append(f'<div class="pr"><span class="pn"><i>{TYPE_ICON.get(k, "≡")}</i>{E(n)}</span><span class="pv">{val}</span></div>')
    t = mk(E(title), m["title"]) if "title" in m else E(title)
    return (f'<div class="nt-peek" style="width:{width}"><div class="pk-top"><span>⇥</span><span>⤢</span>'
            f'<span style="margin-left:auto">💬 •••</span></div><h2>{t}</h2>{"".join(rows)}<div class="pk-body">{body_html}</div></div>')


def nt_panel(title, inner_html, width="52%"):
    """오른쪽 '속성 편집'·'공유' 같은 패널(overlay로)"""
    return f'<div class="nt-peek nt-panel" style="width:{width}"><div class="pt2"><b>{E(title)}</b><span>✕</span></div>{inner_html}</div>'


def nt_field(label, value_html):
    return f'<div class="pr"><span class="pn">{E(label)}</span><span class="pv">{value_html}</span></div>'


def nt_calendar(year, month, sel=None, mark=None, remind=None, remind_mark=None, value=None, top=60, left=None, right=None):
    """날짜 칸을 누르면 뜨는 달력. sel=고른 날, mark=그 날짜 번호, remind='1일 전(오전 9시)' + remind_mark"""
    import calendar as _c
    days = ['<b>일</b>', '<b>월</b>', '<b>화</b>', '<b>수</b>', '<b>목</b>', '<b>금</b>', '<b>토</b>']
    first = (_c.weekday(year, month, 1) + 1) % 7  # 일요일 시작
    cells = [""] * first + [str(d) for d in range(1, _c.monthrange(year, month)[1] + 1)]
    out = []
    for c in cells:
        if c and int(c) == sel:
            h = f'<span class="sel">{c}</span>'
            out.append(mk(h, mark) if mark else h)
        else:
            out.append(f"<span>{c}</span>")
    val = value or (f"{year}년 {month}월 {sel}일" if sel else "")
    rm = ""
    if remind is not None:
        r = f'<div class="rm"><span>알림</span><span>{E(remind)} ›</span></div>'
        rm = mk(r, remind_mark, block=True) if remind_mark else r
    pos = f"top:{top}px;" + (f"right:{right}px;" if right is not None else f"left:{left or 40}px;")
    return (f'<div class="nt-pop nt-cal" style="{pos}width:210px"><div class="ps">{E(val)}</div>'
            f'<div class="cm">{year}년 {month}월 <span>‹ 오늘 ›</span></div><div class="cg">{"".join(days + out)}</div>'
            f'<hr>{rm}<div class="rm"><span>종료일</span><span>○</span></div></div>')


def nt_modal(title, inner, width=360, top=40):
    return (f'<div class="nt-dim"></div><div class="nt-modal" style="width:{width}px;top:{top}px">'
            f'<div class="mt">{title}</div>{inner}</div>')


NT_CSS = """
.nt{display:grid;grid-template-columns:148px minmax(0,1fr);font-family:'Malgun Gothic','Noto Sans KR',Arial,sans-serif;color:#37352f;position:relative}
.nt.noside{grid-template-columns:minmax(0,1fr)}
.nt-side{background:#f7f7f5;border-right:1px solid #ececea;padding:8px 6px;font-size:11.5px;color:#5f5e5b;display:flex;flex-direction:column;gap:1px}
.nt-side .ws{font-weight:700;color:#37352f;padding:3px 6px;margin-bottom:4px}
.nt-side .it{padding:3px 6px;border-radius:4px;white-space:nowrap}
.nt-side .it.on{background:#e9e9e7;color:#37352f;font-weight:700}
.nt-side .it.sub{padding-left:16px}
.nt-side .hd{font-size:10.5px;font-weight:700;color:#91918e;padding:9px 6px 2px;display:flex;justify-content:space-between}
.nt-side .bot{margin-top:auto;padding-top:10px}
.nt-main{position:relative;min-width:0}
.nt-top{display:flex;align-items:center;gap:12px;padding:6px 12px;font-size:11.5px;color:#5f5e5b}
.nt-top .cr{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nt-pg{padding:8px 20px 16px}
.nt-pg h1{font-size:22px;font-weight:700;margin:6px 0 10px;line-height:1.3}
.nt-pg p{margin:4px 0}
.nt .ph{color:#b4b4b0}
.nt-slash{color:#37352f;background:#f1f1ef;border-radius:3px;padding:1px 3px}
.nt-db{margin-top:4px}
.nt-dbname{font-size:16px;font-weight:700;margin:2px 0 4px}
.nt-vbar{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #e9e9e7;gap:6px}
.nt-views{display:flex;gap:2px;font-size:11.5px;white-space:nowrap}
.nt-views span{padding:4px 6px;color:#787774}
.nt-views span.on{color:#37352f;font-weight:700;box-shadow:inset 0 -2px #37352f}
.nt-tools{display:flex;gap:8px;align-items:center;font-size:11px;color:#787774;white-space:nowrap}
.nt-tools .new{background:#2383e2;color:#fff;border-radius:4px;padding:2px 7px;font-weight:700}
.nt-tbl{border-collapse:collapse;width:100%;table-layout:fixed;font-size:11px}
.nt-tbl th{font-weight:400;color:#787774;text-align:left;border-bottom:1px solid #e9e9e7;border-right:1px solid #e9e9e7;padding:4px 5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nt-tbl th .ti{font-size:9.5px;color:#9b9a97;margin-right:3px}
.nt-tbl th.plus{width:28px;text-align:center;border-right:none}
.nt-tbl td{border-bottom:1px solid #e9e9e7;border-right:1px solid #e9e9e7;padding:4px 5px;height:24px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nt-tbl td:last-child{border-right:none}
.nt-tbl .vis,.nt-tbl th.vis{overflow:visible}
.nt-tt{font-weight:600}
.nt-add{display:block;color:#9b9a97;font-size:11px;padding:5px 5px}
span.nt-add{display:inline-block}
.nt-pill{display:inline-block;border-radius:3px;padding:0 6px;font-size:10.5px;line-height:17px;white-space:nowrap}
.nt-pill.st{border-radius:9px;padding:0 7px 0 6px}
.nt-pill.st i{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:4px;vertical-align:1px}
.nt-person{white-space:nowrap}
.nt-person i{display:inline-block;width:15px;height:15px;border-radius:50%;background:#a7c4e5;color:#fff;font-style:normal;font-size:9px;line-height:15px;text-align:center;margin-right:3px}
.nt-board{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:8px}
.nt-col{background:#f7f7f5;border-radius:6px;padding:6px}
.nt-col .gh{font-size:11px;margin-bottom:5px}
.nt-col .gh small{color:#9b9a97}
.nt-card{background:#fff;border-radius:5px;box-shadow:0 0 0 1px rgba(15,15,15,.08),0 2px 4px rgba(15,15,15,.06);padding:6px 7px;margin-bottom:6px;font-size:11px}
.nt-card b{display:block;font-weight:600;margin-bottom:3px}
.nt-card div{margin-top:2px}
.nt-pop{position:absolute;z-index:6;background:#fff;border-radius:6px;box-shadow:0 0 0 1px rgba(15,15,15,.05),0 3px 6px rgba(15,15,15,.1),0 9px 24px rgba(15,15,15,.2);padding:5px 0;font-size:11.5px}
.nt-pop .pt{font-weight:700;padding:3px 10px 5px}
.nt-pop .ps{margin:2px 8px 4px;border:1px solid #e3e2e0;background:#f7f7f5;border-radius:4px;padding:3px 6px}
.nt-pop .ph2{font-size:10px;color:#9b9a97;font-weight:700;padding:5px 10px 2px}
.nt-pop .pi{padding:4px 10px;white-space:nowrap}
.nt-pop .pi.on{background:#f1f1ef}
.nt-pop .pi small{display:block;color:#9b9a97;font-size:10px;white-space:normal}
.nt-pop hr{border:none;border-top:1px solid #ececea;margin:4px 0}
.nt-peek{position:absolute;top:0;right:0;bottom:0;background:#fff;box-shadow:-4px 0 14px rgba(15,15,15,.12);border-left:1px solid #e9e9e7;padding:8px 14px;z-index:5;font-size:11.5px;overflow:hidden}
.nt-peek .pk-top{display:flex;gap:10px;color:#9b9a97;margin-bottom:6px}
.nt-peek h2{font-size:17px;font-weight:700;margin:4px 0 8px;line-height:1.3}
.nt-peek .pr{display:grid;grid-template-columns:96px minmax(0,1fr);gap:6px;padding:3px 0;align-items:center}
.nt-peek .pn{color:#787774;white-space:nowrap}
.nt-peek .pn i{font-style:normal;font-size:9.5px;color:#9b9a97;margin-right:4px}
.nt-peek .pk-body{border-top:1px solid #e9e9e7;margin-top:8px;padding-top:8px;white-space:pre-wrap;line-height:1.55}
.nt-dim{position:absolute;inset:0;background:rgba(15,15,15,.35);z-index:6}
.nt-modal{position:absolute;left:50%;transform:translateX(-50%);z-index:7;background:#fff;border-radius:8px;box-shadow:0 9px 24px rgba(15,15,15,.25);padding:10px 12px;font-size:11.5px}
.nt-modal .mt{font-weight:700;margin-bottom:6px}
.nt-fx{font-family:Consolas,monospace;font-size:9.5px;background:#f7f7f5;border:1px solid #e3e2e0;border-radius:4px;padding:6px 8px;white-space:pre;overflow:hidden;line-height:1.5}
.nt-btn{display:inline-block;background:#2383e2;color:#fff;border-radius:4px;padding:2px 10px;font-weight:700}
.nt-btn.w{background:#fff;color:#37352f;box-shadow:0 0 0 1px #e3e2e0}
.nt-foot{display:flex;justify-content:space-between;align-items:center}
.nt-calc{color:#9b9a97;font-size:11px;padding:4px 6px}
.nt-panel div.mk{margin:4px 0}
.nt-side div.mk::after{top:50%;margin-top:-10px;right:-8px}
.nt-panel .pt2{display:flex;justify-content:space-between;margin-bottom:8px}
.nt-panel .opt{display:flex;align-items:center;gap:6px;padding:2px 0}
.nt-panel .gl{font-size:10px;color:#9b9a97;font-weight:700;margin-top:8px}
.nt-panel .pr{grid-template-columns:70px minmax(0,1fr)}
.nt-cal .cm{display:flex;justify-content:space-between;padding:2px 10px;font-weight:700}
.nt-cal .cm span{color:#9b9a97;font-weight:400}
.nt-cal .cg{display:grid;grid-template-columns:repeat(7,1fr);padding:2px 8px;text-align:center;font-size:10.5px;row-gap:2px}
.nt-cal .cg b{font-weight:400;color:#9b9a97}
.nt-cal .cg .sel{background:#2383e2;color:#fff;border-radius:4px;display:inline-block;min-width:18px}
.nt-cal .rm{display:flex;justify-content:space-between;padding:3px 10px}
.nt-inp{border:1px solid #e3e2e0;border-radius:4px;padding:2px 6px;background:#f7f7f5;display:inline-block;min-width:120px}
.nt-cmt{display:flex;gap:6px;align-items:center;border-top:1px solid #e9e9e7;margin-top:8px;padding-top:6px;color:#37352f}
.nt-cmt i{display:inline-block;width:16px;height:16px;border-radius:50%;background:#a7c4e5;color:#fff;font-style:normal;font-size:9px;line-height:16px;text-align:center}
.nt-mention{color:#2383e2;background:#e7f3f8;border-radius:3px;padding:0 3px}
.nt-chip{display:inline-block;margin-left:6px;font-size:10px;color:#5f5e5b;background:#fff;box-shadow:0 0 0 1px #e3e2e0;border-radius:3px;padding:0 4px;font-weight:400}
.xl-top{background:#217346;color:#fff;padding:5px 10px;font-size:12px}
.xl-rib{display:flex;gap:12px;padding:4px 10px;font-size:11.5px;border-bottom:1px solid #d4d4d4;background:#f3f3f3}
.xl-rib span.on{color:#217346;font-weight:700;box-shadow:inset 0 -2px #217346}
"""
