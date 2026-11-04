"""lessonkit — 단계별 따라 하기 교안(HTML 1파일) 생성 도구.

사용법(빌드 스크립트에서):
    import sys; sys.path.insert(0, "<이 파일이 있는 폴더>")
    from lessonkit import *
    pages = [Page("home", "", "홈", hero(...) + wrap(...)), Page("p1", "1", "첫 단계", wrap(section(...) + step(...)))]
    build("out/index.html", pages, title=..., brand=..., site_url=..., og=...)

설계 원칙 (references/style-guide.md 참고)
- 모든 화면 텍스트는 E()로 이스케이프. 의도한 HTML 조각만 문자열로 이어 붙인다.
- 그림(모형 화면)은 폭 DESIGN_W(560px) 기준으로 그린다. 휴대폰에서는 자동 축소 + 탭하면 확대.
- 모형 화면의 빨간 번호(mk)는 바로 옆 '따라 하기' 번호와 같은 숫자를 쓴다.
- shots/<그림ID>.png 가 있으면 실제 캡처가 자동으로 모형을 대신한다.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
E = html.escape
DESIGN_W = 560

# ───────────────────────────── 기본 조각 ─────────────────────────────

def mk(text: str, n, block: bool = False) -> str:
    """빨간 테두리 + 번호 배지. text는 이미 HTML이어도 됨(이스케이프는 호출자가).
    목록(ul)·상자처럼 블록 요소에 번호를 달 때는 block=True."""
    tag = "div" if block else "span"
    return f'<{tag} class="mk" data-n="{n}">{text}</{tag}>'


def ui(label: str) -> str:
    """본문에서 화면 속 버튼·메뉴 이름 표기."""
    return f"<span class='ui'>{E(label)}</span>"


def kbd(*keys: str) -> str:
    return "+".join(f"<kbd>{E(k)}</kbd>" for k in keys)


def box(kind: str, title: str, body_html: str) -> str:
    """kind: ok / warn / no / info"""
    return f'<div class="box {kind}"><b>{E(title)}</b> {body_html}</div>'


def table(headers, rows, raw=False) -> str:
    cell = (lambda v: v) if raw else (lambda v: E(str(v)))
    head = "".join(f"<th>{E(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="t"><tr>{head}</tr>{body}</table>'


def flow(items) -> str:
    """[(굵은 제목, 설명), ...] → 화살표 흐름도"""
    parts = []
    for i, (t, d) in enumerate(items):
        if i:
            parts.append('<div class="ar">→</div>')
        parts.append(f'<div class="fs"><b>{E(t)}</b>{E(d)}</div>')
    return f'<div class="flow">{"".join(parts)}</div>'


def cards(items, cols=4) -> str:
    """[(아이콘, 제목, 설명HTML), ...]"""
    inner = "".join(f'<div class="card"><div class="ic">{ic}</div><h3>{E(t)}</h3>{d}</div>' for ic, t, d in items)
    return f'<div class="grid g{cols}">{inner}</div>'


def section(title: str, sub: str = "") -> str:
    return f'<h2 class="sec">{E(title)}{f"<small>{E(sub)}</small>" if sub else ""}</h2>'


def wrap(inner: str, pc_note: str | None = None) -> str:
    """페이지 본문 래퍼. pc_note를 주면 휴대폰에서만 보이는 'PC에서 실습' 안내를 맨 위에 넣는다."""
    note = f'<div class="box warn pc-note"><b>💻 실습은 PC에서</b> {pc_note}</div>' if pc_note else ""
    return f'<div class="wrap">{note}{inner}</div>'


def hero(eyebrow: str, title_html: str, desc: str) -> str:
    """title_html 안에서 강조할 부분은 <em>…</em>"""
    return f'<div class="hero"><div class="eb">{E(eyebrow)}</div><h1>{title_html}</h1><p>{E(desc)}</p></div>'


def downloads(links) -> str:
    """[(href, 라벨, 'g'|''), ...]"""
    return "".join(f'<a class="dl {cls}" href="{E(h)}" download>{E(l)}</a>' for h, l, cls in links)


# ───────────────────────────── 단계 카드 ─────────────────────────────

def step(no: str, title: str, goal: str, todo: list[str], ok: str | None = None, stuck: str | None = None,
         figure: str = "", extra: str = "", one: bool = False) -> str:
    """교안의 기본 단위.
    no: '1-2' 같은 단계 번호 / goal: 이 단계로 얻는 것 한 문장 / todo: 따라 하기(HTML 허용, 번호는 자동)
    ok: '성공하면' 화면에 보이는 것 / stuck: '막히면' 해결법 / figure: fig(...)들 / extra: 코드·프롬프트·안내 박스
    """
    lis = "".join(f"<li>{t}</li>" for t in todo)
    left = (f'<div><div class="goal">🎯 {goal}</div><ol class="do">{lis}</ol>{extra}'
            f'{f"<div class=okline>{ok}</div>" if ok else ""}{f"<div class=stuck>{stuck}</div>" if stuck else ""}</div>')
    body = f'<div class="step-b{" one" if one or not figure else ""}">{left}{f"<div>{figure}</div>" if figure else ""}</div>'
    return f'<section class="step" id="s{E(no)}"><div class="step-h"><span class="no">STEP {E(no)}</span><h3>{E(title)}</h3></div>{body}</section>'


def figs(*figures: str) -> str:
    """한 단계에 그림 여러 장"""
    return "<div style='height:10px'></div>".join(figures)


def fig(sid: str, cap: str, inner: str) -> str:
    """그림(모형 화면). sid는 'm1-03'처럼 고유하게 — 실제 캡처 파일명(shots/<sid>.png)과 촬영 목록에 쓰인다."""
    return (f'<figure class="shot" data-shot="{E(sid)}" data-cap="{E(cap)}"><div class="mock">{inner}</div>'
            f'<figcaption><span>{E(cap)}<span class="zoom-hint"> · 탭하면 크게 보기 🔍</span></span>'
            f'<span class="sid">{E(sid)}</span></figcaption></figure>')


def code_block(title: str, path: str | Path | None = None, text: str | None = None, cid: str = "code",
               download_href: str | None = None, tall: bool = False, wrap: bool = False) -> str:
    """코드 상자 + 전체 복사(+내려받기). path를 주면 실제 파일 내용을 그대로 넣는다(교안·코드 불일치 방지).
    wrap=True: 긴 안내문·실습 문구처럼 코드가 아닌 글은 줄바꿈해서 보여준다(복사 내용은 그대로)."""
    src = Path(path).read_text(encoding="utf-8") if path else (text or "")
    dl = f'<a class="copy-btn" style="text-decoration:none" href="{E(download_href)}" download>내려받기</a> ' if download_href else ""
    cls = "code" + (" tall" if tall else "") + (" wraptext" if wrap else "")
    return (f'<div class="{cls}"><div class="code-top"><span>📄 {E(title)} · {len(src.splitlines())}줄</span>'
            f'<span>{dl}<button class="copy-btn" data-copy="{E(cid)}">전체 복사</button></span></div>'
            f'<pre id="{E(cid)}">{E(src)}</pre></div>')


def prompt(text: str) -> str:
    """AI에 붙여넣을 프롬프트 카드(복사 버튼). [대괄호]는 사용자가 바꿀 부분."""
    return f'<div class="prompt"><button class="copy-btn" data-copy-text>복사</button>{E(text)}</div>'


# ───────────────────────────── 모형 화면 부품 ─────────────────────────────

def dropdown(items, align: str = "left", width: int | None = None, left=None, top=None) -> str:
    """펼친 메뉴. items: ['항목', ('표시할 항목', 번호), '-'(구분선)]
    menubar(dd_for=...)로 넘기면 해당 메뉴 바로 아래에 붙는다(오른쪽 끝 메뉴는 align='right')."""
    out = []
    for it in items:
        if it == "-":
            out.append("<hr>")
            continue
        text, n = it if isinstance(it, tuple) else (it, None)
        out.append(f'<div class="{"on" if n else ""}">{mk(E(text), n) if n else E(text)}</div>')
    w = f"min-width:{width}px;" if width else ""
    pos = f"left:{left}px;top:{top}px;" if left is not None else ("right:0;top:100%;" if align == "right" else "left:0;top:100%;")
    return f'<div class="dd" style="{pos}{w}">{"".join(out)}</div>'


def menubar(menus, marks: dict | None = None, dd_for: tuple | None = None) -> str:
    """메뉴 줄. marks={'파일': 1}, dd_for=('파일', dropdown(...))"""
    marks = marks or {}
    out = []
    for m in menus:
        n = marks.get(m)
        dd = dd_for[1] if dd_for and dd_for[0] == m else ""
        label = mk(E(m), n) if n else E(m)
        out.append(f'<span class="{"on" if n or dd else ""}" style="position:relative">{label}{dd}</span>')
    return f'<div class="gs-menu">{"".join(out)}</div>'


def dialog(title: str, body_html: str, buttons_html: str) -> str:
    """화면 위에 뜨는 확인 창(반투명 배경 포함) — overlay 인자로 넘긴다."""
    return (f'<div class="dlg-back"><div class="dlg"><h4>{title}</h4><div>{body_html}</div>'
            f'<div class="btns">{buttons_html}</div></div></div>')


def gbtn(label: str, primary=False, n=None) -> str:
    b = f'<span class="gbtn{" p" if primary else ""}">{E(label)}</span>'
    return mk(b, n) if n else b


def grid(rows, colors: dict | None = None, ncols: int | None = None, header_row=True) -> str:
    """스프레드시트 격자. rows[0]은 머리행. True/False는 체크박스로 표시. colors={행번호: '#색'}"""
    colors = colors or {}
    ncols = ncols or max(len(r) for r in rows)
    letters = "ABCDEFGHIJKLMNOP"[:ncols]
    head = '<tr><th class="rn"></th>' + "".join(f"<th>{c}</th>" for c in letters) + "</tr>"
    body = []
    for i, r in enumerate(rows):
        cells = []
        for j in range(ncols):
            v = r[j] if j < len(r) else ""
            v = '<span class="cb on"></span>' if v is True else '<span class="cb"></span>' if v is False else E(str(v))
            bg = colors.get((i, j)) or colors.get(i)
            cells.append(f'<td style="{f"background:{bg}" if bg else ""}">{v}</td>')
        body.append(f'<tr class="{"h" if i == 0 and header_row else ""}"><th class="rn">{i + 1}</th>{"".join(cells)}</tr>')
    return f'<table class="gs-grid">{head}{"".join(body)}</table>'


SHEETS_MENUS = ["파일", "수정", "보기", "삽입", "서식", "데이터", "도구", "확장 프로그램", "도움말"]


def sheets_window(rows, title="스프레드시트", marks=None, dd_for=None, extra_menus=(), tabs=("시트1",), active=None,
                  tab_marks: dict | None = None, colors=None, overlay="") -> str:
    """구글 시트 화면. extra_menus=('🗂 회원업무',)처럼 스크립트로 만든 메뉴를 메뉴줄 끝에 추가."""
    active = active or tabs[0]
    tab_marks = tab_marks or {}
    tab_html = "".join(f'<span class="{"on" if t == active else ""}">{mk(E(t), tab_marks[t]) if t in tab_marks else E(t)}</span>' for t in tabs)
    return (f'<div class="gs-top"><div class="gs-logo"></div><div class="gs-title">{E(title)} ☆</div></div>'
            f'{menubar(list(SHEETS_MENUS) + list(extra_menus), marks, dd_for)}<div class="gs-bar"></div>'
            f'<div class="gs-fx"><b>fx</b></div>{grid(rows, colors)}<div class="gs-tabs">＋ ≡ {tab_html}</div>{overlay}')


def app_window(title: str, body_html: str, icon_color="#1a73e8", menus=(), marks=None, dd_for=None, overlay="") -> str:
    """범용 앱/웹 화면(캔바·노션·사내 시스템 등). body_html에 grid/버튼/입력칸 등을 자유롭게 구성."""
    mb = menubar(list(menus), marks, dd_for) if menus else ""
    return (f'<div class="win-top"><span class="win-icon" style="background:{icon_color}"></span>'
            f'<span class="win-title">{E(title)}</span></div>{mb}<div class="win-body">{body_html}</div>{overlay}')


def code_editor(code_lines, files=("Code.gs",), active=None, fn="myFunction", marks=None, log=None,
                project="제목 없는 프로젝트", app="Apps Script", files_dd="") -> str:
    """코드 편집기(Apps Script 편집기 모양). marks 키: save, run, fn, add, project, log, file:<이름>"""
    marks = marks or {}
    active = active or files[0]

    def m(key, text):
        return mk(text, marks[key]) if key in marks else text

    def hl(line):
        s = E(line)
        for kw in ("function ", "const ", "return ", "let ", "var "):
            s = s.replace(kw, f'<span class="k">{kw}</span>')
        if "//" in s:
            a, b = s.split("//", 1)
            s = a + f'<span class="c">//{b}</span>'
        return s

    file_items = "".join(f'<div class="f {"on" if f == active else ""}">{m("file:" + f, E(f))}</div>' for f in files)
    lines = "\n".join(f'<span class="ln">{i + 1}</span>{hl(l)}' for i, l in enumerate(code_lines))
    log_html = ""
    if log:
        log_html = '<div class="as-log">' + m("log", '<div class="lh">실행 로그</div>') + "".join(
            f'<div class="row"><span>오후 3:00:0{i}</span><span>{E(a)}</span><span>{E(b)}</span></div>' for i, (a, b) in enumerate(log)) + "</div>"
    return (f'<div class="as-head"><div class="logo"></div><span>{E(app)}</span><span class="pn">{m("project", E(project))}</span></div>'
            f'<div class="as"><div class="as-rail"><span>ⓘ</span><span style="color:#1a73e8">‹›</span><span>⏰</span><span>≡</span><span>⚙</span></div>'
            f'<div class="as-files" style="position:relative"><div class="h"><span>파일</span>{m("add", "<b>＋</b>")}</div>{file_items}{files_dd}</div>'
            f'<div class="as-main"><div class="as-tool"><span>↶ ↷</span>{m("save", "💾")}{m("run", "<span class=run>▷ 실행</span>")}'
            f'<span>디버그</span>{m("fn", f"<span class=sel>{E(fn)} ▾</span>")}<span>실행 로그</span></div>'
            f'<div class="as-code">{lines}</div>{log_html}</div></div>')


def google_auth(kind: str, app_name="제목 없는 프로젝트", email="my.account@example.com") -> str:
    """구글 권한 승인 화면 3종: 'account'(계정 선택) / 'unverified'(확인하지 않은 앱) / 'consent'(권한 체크)"""
    logo = '<div class="glogo"><b>G</b><b>o</b><b>o</b><b>g</b><b>l</b><b>e</b></div>'
    if kind == "account":
        return (f'<div class="gw">{logo}<h4>계정 선택</h4><div style="color:#5f6368">계속하려면 <b>{E(app_name)}</b>(으)로 이동</div>'
                f'<div class="acct">{mk(f"<span class=av>나</span> <span>내 계정<br><small>{E(email)}</small></span>", 1)}</div>'
                f'<div class="acct"><span class="av" style="background:#9aa0a6">+</span> 다른 계정 사용</div></div>')
    if kind == "unverified":
        return (f'<div class="gw">{logo}<div class="warnicon">⚠</div><h4>Google에서 확인하지 않은 앱</h4>'
                f'<p style="color:#5f6368">개발자({E(email)})가 Google에 인증을 요청할 때까지 이 앱을 사용하지 마세요.</p>'
                f'<p style="margin-top:12px">{mk("<span class=lnk>고급</span>", 1)}</p>'
                f'<p style="margin-top:6px">{mk(f"<span class=lnk>{E(app_name)}(으)로 이동(안전하지 않음)</span>", 2)}</p>'
                f'<div class="foot"><span class="gbtn p">안전한 페이지로 돌아가기</span></div></div>')
    if kind == "consent":
        perms = ["Google Sheets 스프레드시트 보기, 수정, 생성, 삭제", "나로서 이메일 보내기"]
        rows = "".join(f'<div class="perm"><span class="cb on"></span><span>{p}</span></div>' for p in perms)
        return (f'<div class="gw">{logo}<h4>{E(app_name)}에서 내 Google 계정에 대한 추가 액세스를 요청합니다</h4>'
                f'<div class="perm">{mk("<span class=cb on></span> <b>모두 선택</b>", 1)}</div>{rows}'
                f'<div class="foot"><span class="gbtn">취소</span>{mk("<span class=gbtn p>계속</span>", 2)}</div></div>')
    raise ValueError(kind)


def mail_view(subject: str, body: str, sender="보낸 사람", to="나", marks=(1, 2)) -> str:
    """받은 메일 화면"""
    return (f'<div class="gm"><div class="subj">{mk(E(subject), marks[0])} <span class="pill b">받은편지함</span></div>'
            f'<div class="from"><span><b>{E(sender)}</b><br><small>받는사람: {E(to)}</small></span></div>'
            f'<div class="body">{mk(E(body), marks[1])}</div></div>')


def chat_view(messages, input_text="메시지를 입력하세요", app="Claude", marks: dict | None = None,
              hello: str = "무엇을 도와드릴까요?") -> str:
    """AI 대화 화면. messages=[('user'|'ai', 텍스트), ...], marks={메시지순번: 번호, 'input': 번호, 'send': 번호}
    messages가 비어 있으면 '새 채팅' 첫 화면(인사말 + 입력창)으로 그린다."""
    marks = marks or {}
    out = [] if messages else [f'<div class="hello"><b>{E(app)}</b>{E(hello)}</div>']
    for i, (who, text) in enumerate(messages):
        m = f'<div class="msg {who}">{E(text)}</div>'
        out.append(mk(m, marks[i]) if i in marks else m)
    inp = f'<span>{E(input_text)}</span>'
    send = '<span class="send">↑</span>'
    inbox = f'<div class="inbox">{mk(inp, marks["input"]) if "input" in marks else inp}{mk(send, marks["send"]) if "send" in marks else send}</div>'
    return f'<div class="win-top"><span class="win-icon" style="background:#c96442"></span><span class="win-title">{E(app)}</span></div><div class="chat">{"".join(out)}{inbox}</div>'


def sidebar(title: str, inner_html: str) -> str:
    """화면 오른쪽에 붙는 작업 패널(overlay로 사용)"""
    return f'<div class="sidebar"><div class="sb-t"><span>{E(title)}</span><span>✕</span></div>{inner_html}</div>'


# ───────────────────────────── 부록 ─────────────────────────────

def shot_list_section() -> str:
    """부록용: 실제 캡처 교체 안내 + 화면 ID 목록(런타임이 자동으로 채움)"""
    return ('<h3>화면 캡처 목록(실제 화면 교체용)</h3><p>아래 화면 ID 이름으로 실제 캡처를 <code>shots/</code> 폴더에 PNG로 저장하면, '
            '교안을 열 때 모형 화면 대신 실제 캡처가 자동으로 보입니다. 실제 개인정보가 보이는 화면은 찍지 마세요.</p><div id="shotlist"></div>')


# ───────────────────────────── 빌드 ─────────────────────────────

@dataclass
class Page:
    pid: str      # 탭 id(영문·숫자)
    num: str      # 탭 번호 배지('' 이면 생략, '+' 등 가능)
    label: str    # 탭 이름
    html: str     # 페이지 본문(hero/wrap 등)


def build(out_path, pages: list[Page], *, title: str, description: str, brand=("AS", "교안", "부제"),
          site_url: str | None = None, og_image: str | None = None, og_title: str | None = None,
          site_name: str | None = None, extra_css: str = "") -> Path:
    """index.html 생성. site_url(배포 주소, '/'로 끝)과 og_image(파일명)를 주면 카카오톡·SNS 미리보기 태그를 넣는다.
    extra_css: 이 교안에만 필요한 스타일(새 도구 모형 등) — lesson.css를 고치지 말고 여기로 넘긴다."""
    css = (HERE / "lesson.css").read_text(encoding="utf-8") + ("\n/* 교안 전용 */\n" + extra_css if extra_css else "")
    js = (HERE / "lesson_runtime.js").read_text(encoding="utf-8")
    ids = [p.pid for p in pages]
    js = js.replace("__PAGE_IDS__", ",".join(f'"{i}"' for i in ids))
    nav = "".join(f'<button class="tab" data-p="{E(p.pid)}">{f"<span class=tnum>{E(p.num)}</span>" if p.num else ""}{E(p.label)}</button>' for p in pages)
    body = "".join(f'<main class="page" id="{E(p.pid)}">{p.html}</main>' for p in pages)
    og = ""
    if site_url and og_image:
        t = E(og_title or title)
        og = f"""
<meta property="og:type" content="website">
<meta property="og:site_name" content="{E(site_name or brand[2])}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{E(description)}">
<meta property="og:image" content="{E(site_url + og_image)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:url" content="{E(site_url)}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:image" content="{E(site_url + og_image)}">"""
    doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">{og}
<style>{css}</style>
</head>
<body>
<nav class="nav"><div class="nav-inner"><div class="brand"><div class="logo">{E(brand[0])}</div><div><div class="bt">{E(brand[1])}</div><div class="bs">{E(brand[2])}</div></div></div><div class="tabs">{nav}</div></div></nav>
{body}
<script>{js}</script>
</body>
</html>
"""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return out
