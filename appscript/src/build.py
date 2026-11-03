"""교안 빌드: python appscript/src/build.py  →  appscript/index.html
코드 블록은 appscript/code/ 의 실제 파일을 그대로 넣으므로, 코드를 고친 뒤 다시 빌드하면 교안도 맞춰집니다.
화면 캡처: appscript/shots/<화면ID>.png 가 있으면 모형 화면 대신 실제 캡처가 자동으로 표시됩니다.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"
FIX = json.loads((ROOT / "tests" / "practice_fixture.json").read_text(encoding="utf-8"))
E = html.escape


def mk(text, n):
    return f'<span class="mk" data-n="{n}">{text}</span>'


def fig(sid, cap, inner, h=None):
    style = f' style="min-height:{h}px"' if h else ""
    return (f'<figure class="shot" data-shot="{sid}" data-cap="{E(cap)}"><div class="mock"{style}>{inner}</div>'
            f'<figcaption><span>{E(cap)}</span><span class="sid">{sid}</span></figcaption></figure>')


# ── 구글 시트 모형 ───────────────────────────────────────────
MENUS = ["파일", "수정", "보기", "삽입", "서식", "데이터", "도구", "확장 프로그램", "도움말"]


def sheet(menu_mark=None, custom=False, custom_mark=None, dropdown="", rows=None, colors=None, tabs=None,
          active="추천신청", overlay="", title="회원업무_실습", tab_mark=None, ncols=None, dd_for=None):
    """dd_for=(메뉴이름, 드롭다운HTML): 해당 메뉴 바로 아래에 펼친 메뉴를 붙입니다."""
    menus = []
    for m in MENUS + (["🗂 회원업무"] if custom else []):
        is_custom = m == "🗂 회원업무"
        n = custom_mark if is_custom else (menu_mark[1] if menu_mark and m == menu_mark[0] else None)
        label = mk(E(m), n) if n else E(m)
        dd = dd_for[1] if dd_for and dd_for[0] == m else ""
        menus.append(f'<span class="{"on" if n or dd else ""}" style="position:relative">{label}{dd}</span>')
    rows = rows if rows is not None else FIX["추천신청"][:7]
    ncols = ncols or max(len(r) for r in rows)
    letters = "ABCDEFGHIJKL"[:ncols]
    head = '<tr><th class="rn"></th>' + "".join(f"<th>{c}</th>" for c in letters) + "</tr>"
    body = []
    for i, r in enumerate(rows):
        cells = []
        for j in range(ncols):
            v = r[j] if j < len(r) else ""
            if v is True:
                v = '<span class="cb on"></span>'
            elif v is False:
                v = '<span class="cb"></span>'
            else:
                v = E(str(v))
            bg = colors.get((i, j)) or colors.get(i) if colors else None
            cells.append(f'<td style="{f"background:{bg}" if bg else ""}">{v}</td>')
        body.append(f'<tr class="{"h" if i == 0 else ""}"><th class="rn">{i + 1}</th>{"".join(cells)}</tr>')
    tabs = tabs or ["추천신청", "메일양식", "연수", "공익", "회비"]
    tab_html = "".join(
        f'<span class="{"on" if t == active else ""}">{mk(E(t), tab_mark[1]) if tab_mark and t == tab_mark[0] else E(t)}</span>'
        for t in tabs)
    return (f'<div class="gs-top"><div class="gs-logo"></div><div class="gs-title">{E(title)} ☆</div></div>'
            f'<div class="gs-menu">{"".join(menus)}</div><div class="gs-bar"></div>'
            f'<div class="gs-fx"><b>fx</b></div>'
            f'<table class="gs-grid">{head}{"".join(body)}</table><div class="gs-tabs">＋ ≡ {tab_html}</div>'
            f'{dropdown}{overlay}')


def dropdown(items, left=None, top=None, width=None, align="left"):
    out = []
    for it in items:
        if it == "-":
            out.append("<hr>")
            continue
        text, n = (it if isinstance(it, tuple) else (it, None))
        out.append(f'<div class="{"on" if n else ""}">{mk(E(text), n) if n else E(text)}</div>')
    w = f"min-width:{width}px;" if width else ""
    pos = f"left:{left}px;top:{top}px;" if left is not None else ("right:0;top:100%;" if align == "right" else "left:0;top:100%;")
    return f'<div class="dd" style="{pos}{w}">{"".join(out)}</div>'


def dialog(title, body, buttons):
    return (f'<div class="dlg-back"><div class="dlg"><h4>{title}</h4><div>{body}</div>'
            f'<div class="btns">{buttons}</div></div></div>')


# ── Apps Script 편집기 모형 ──────────────────────────────────
def highlight(line):
    s = E(line)
    for kw in ("function ", "const ", "return ", "let "):
        s = s.replace(kw, f'<span class="k">{kw}</span>')
    if "//" in s:
        a, b = s.split("//", 1)
        s = a + f'<span class="c">//{b}</span>'
    return s


def editor(code_lines, files=("Code.gs",), active="Code.gs", fn="onOpen", marks=None, log=None, project="제목 없는 프로젝트",
           files_plus_dd=""):
    marks = marks or {}
    def m(key, text):
        return mk(text, marks[key]) if key in marks else text
    file_items = "".join(f'<div class="f {"on" if f == active else ""}">{m("file:" + f, E(f))}</div>' for f in files)
    lines = "\n".join(f'<span class="ln">{i + 1}</span>{highlight(l)}' for i, l in enumerate(code_lines))
    log_html = ""
    if log:
        log_html = '<div class="as-log">' + m("log", '<div class="lh">실행 로그</div>') + "".join(
            f'<div class="row"><span>오후 3:00:0{i}</span><span>{E(a)}</span><span>{E(b)}</span></div>' for i, (a, b) in enumerate(log)) + "</div>"
    return (f'<div class="as-head"><div class="logo"></div><span>Apps Script</span>'
            f'<span class="pn">{m("project", E(project))}</span></div>'
            f'<div class="as"><div class="as-rail"><span title="개요">ⓘ</span><span title="편집기" style="color:#1a73e8">‹›</span><span title="트리거">⏰</span><span title="실행">≡</span><span title="설정">⚙</span></div>'
            f'<div class="as-files" style="position:relative"><div class="h"><span>파일</span>{m("add", "<b>＋</b>")}</div>{file_items}{files_plus_dd}'
            f'<div class="h" style="margin-top:12px"><span>라이브러리 ＋</span></div><div class="h"><span>서비스 ＋</span></div></div>'
            f'<div class="as-main"><div class="as-tool"><span>↶ ↷</span>{m("save", "💾")}'
            f'{m("run", "<span class=run>▷ 실행</span>")}<span>디버그</span>{m("fn", f"<span class=sel>{E(fn)} ▾</span>")}'
            f'{m("logbtn", "<span>실행 로그</span>")}</div>'
            f'<div class="as-code">{lines}</div>{log_html}</div></div>')


def google_window(kind):
    logo = '<div class="glogo"><b>G</b><b>o</b><b>o</b><b>g</b><b>l</b><b>e</b></div>'
    if kind == "account":
        return (f'<div class="gw">{logo}<h4>계정 선택</h4><div style="color:#5f6368">계속하려면 <b>제목 없는 프로젝트</b>(으)로 이동</div>'
                f'<div class="acct">{mk("<span class=av>나</span> <span>내 계정<br><small>my.account@example.com</small></span>", 1)}</div>'
                f'<div class="acct"><span class="av" style="background:#9aa0a6">+</span> 다른 계정 사용</div></div>')
    if kind == "unverified":
        return (f'<div class="gw">{logo}<div class="warnicon">⚠</div><h4>Google에서 확인하지 않은 앱</h4>'
                f'<p style="color:#5f6368">개발자(my.account@example.com)가 Google에 인증을 요청할 때까지 이 앱을 사용하지 마세요.</p>'
                f'<p style="margin-top:12px">{mk("<span class=lnk>고급</span>", 1)}</p>'
                f'<p style="margin-top:8px;color:#5f6368">Google에서 아직 검토하지 않은 앱입니다. 개발자를 신뢰하는 경우에만 계속하세요.</p>'
                f'<p style="margin-top:6px">{mk("<span class=lnk>제목 없는 프로젝트(으)로 이동(안전하지 않음)</span>", 2)}</p>'
                f'<div class="foot"><span class="gbtn p">안전한 페이지로 돌아가기</span></div></div>')
    if kind == "consent":
        perms = ["Google Sheets 스프레드시트 보기, 수정, 생성, 삭제", "나로서 이메일 보내기", "외부 콘텐츠를 표시하고 실행"]
        rows = "".join(f'<div class="perm"><span class="cb on"></span><span>{p}</span></div>' for p in perms)
        return (f'<div class="gw">{logo}<h4>제목 없는 프로젝트에서 내 Google 계정에 대한 추가 액세스를 요청합니다</h4>'
                f'<div class="perm">{mk("<span class=cb on></span> <b>모두 선택</b>", 1)}</div>{rows}'
                f'<div class="foot"><span class="gbtn">취소</span>{mk("<span class=gbtn p>계속</span>", 2)}</div></div>')
    raise ValueError(kind)


def gmail(subject, body, to="나"):
    return (f'<div class="gm"><div class="subj">{mk(E(subject), 1)} <span class="pill b">받은편지함</span></div>'
            f'<div class="from"><span class="av" style="width:28px;height:28px;border-radius:50%;background:#1a73e8;color:#fff;display:inline-flex;align-items:center;justify-content:center">대</span>'
            f'<span><b>대한변리사회</b> &lt;my.account@example.com&gt;<br><small>받는사람: {E(to)}</small></span></div>'
            f'<div class="body">{mk(E(body), 2)}</div></div>')


# ── 단계 카드 ───────────────────────────────────────────────
def step(no, title, goal, todo, ok=None, stuck=None, figure="", extra="", one=False):
    lis = "".join(f"<li>{t}</li>" for t in todo)
    left = (f'<div><div class="goal">🎯 {goal}</div><ol class="do">{lis}</ol>{extra}'
            f'{f"<div class=okline>{ok}</div>" if ok else ""}{f"<div class=stuck>{stuck}</div>" if stuck else ""}</div>')
    body = f'<div class="step-b{" one" if one or not figure else ""}">{left}{f"<div>{figure}</div>" if figure else ""}</div>'
    return f'<section class="step" id="s{no}"><div class="step-h"><span class="no">STEP {no}</span><h3>{title}</h3></div>{body}</section>'


def code_block(title, filename, tall=False, cid=None):
    src = (CODE / filename).read_text(encoding="utf-8")
    cid = cid or filename
    return (f'<div class="code{" tall" if tall else ""}"><div class="code-top"><span>📄 {E(title)} · {len(src.splitlines())}줄</span>'
            f'<span><a class="copy-btn" style="text-decoration:none" href="code/{E(filename)}" download>내려받기</a> '
            f'<button class="copy-btn" data-copy="{E(cid)}">전체 복사</button></span></div>'
            f'<pre id="{E(cid)}">{E(src)}</pre></div>')


def prompt(text):
    return f'<div class="prompt"><button class="copy-btn" data-copy-text>복사</button>{E(text)}</div>'


# ════════════════════════════════════════════════════════════
APPLY = FIX["추천신청"]
COLS_APPLY = ["타임스탬프", "추천기관", "성명", "등록번호", "이메일", "연락처", "소속사무소", "주요경력", "선정", "비고", "발송상태", "발송일시"]


def apply_rows(n=7, selected=(), notes=None, status=None, short=True):
    rows = [["추천기관", "성명", "등록번호", "이메일", "선정", "비고", "발송상태"]] if short else [COLS_APPLY]
    notes = notes or {}
    status = status or {}
    for i, r in enumerate(APPLY[1:n]):
        rows.append([r[1], r[2], r[3], r[4], (i + 1) in selected, notes.get(i + 1, ""), status.get(i + 1, "")])
    return rows


first_code = (CODE / "01_첫자동화.gs").read_text(encoding="utf-8").splitlines()
full_code = (CODE / "회원업무_전체코드.gs").read_text(encoding="utf-8").splitlines()
pages = {}

# ── 홈 ──
pages["home"] = f"""
<div class="hero"><div class="eb">대한변리사회 회원서비스실 · AI 업무 자동화 실습</div>
<h1>구글 시트 + Apps Script로<br><em>회원 업무 자동화</em> 따라 하기</h1>
<p>코드를 외우지 않습니다. 복사 → 붙여넣기 → 실행 → 결과 확인. 화면 순서대로 따라 하면
중복 신청 확인, 선정 메일 발송, 연수·공익·회비 통합 현황까지 직접 만들 수 있습니다.</p></div>
<div class="wrap">
<h2 class="sec">오늘 만드는 것<small>회의(회원 관리 업무 AI 활용 방안)에서 결정한 내용을 그대로 실습합니다</small></h2>
<div class="grid g4">
<div class="card"><div class="ic">🧭</div><h3>나만의 메뉴</h3>시트 위에 <span class="ui">🗂 회원업무</span> 메뉴를 만들어 버튼 하나로 작업을 실행합니다.</div>
<div class="card"><div class="ic">🔁</div><h3>중복 신청 확인</h3>등록번호 기준으로 여러 기관·같은 기관 중복 신청을 색으로 표시합니다.</div>
<div class="card"><div class="ic">✉️</div><h3>선정 메일 자동 발송</h3>체크한 선정자에게만 안내 메일을 보내고 발송 이력을 남깁니다.</div>
<div class="card"><div class="ic">📊</div><h3>통합 현황 보드</h3>연수·공익·회비 미이수(미납) 현황을 등록번호로 합쳐 한 화면에 봅니다.</div>
</div>
<h2 class="sec">진행 순서</h2>
<div class="flow"><div class="fs"><b>0. 준비</b>실습 시트 만들기</div><div class="ar">→</div>
<div class="fs"><b>1. 첫 자동화</b>메뉴·권한 승인</div><div class="ar">→</div>
<div class="fs"><b>2. 회원 추천</b>중복·선정·메일</div><div class="ar">→</div>
<div class="fs"><b>3. 현황 보드</b>연수·공익·회비</div><div class="ar">→</div>
<div class="fs"><b>4. 버튼 패널</b>오른쪽 작업창</div><div class="ar">→</div>
<div class="fs"><b>5. AI 활용</b>요청·수정하는 법</div></div>
<table class="t"><tr><th>회차</th><th>일시</th><th>내용</th><th>준비물</th></tr>
<tr><td><span class="pill">1차</span></td><td>11. 4.(수) 15:00</td><td>0 준비 · 1 첫 자동화 · 2 회원 추천 자동화</td><td>노트북, 구글 계정(회 업무용), 크롬 브라우저</td></tr>
<tr><td><span class="pill">2차</span></td><td>11. 13.</td><td>3 통합 현황 보드 · 4 버튼 패널 · 5 AI에게 요청하는 법</td><td>연수·공익 내려받기 파일(실제 업무 적용 시)</td></tr></table>

<h2 class="sec">꼭 지킬 원칙 3가지</h2>
<div class="grid g3">
<div class="box info"><b>① 개인정보는 시트 안에서만</b><br>회원 명단은 구글 시트 안에서 처리합니다. AI(Claude·GPT 등)에는 <b>열 이름(1행)만</b> 알려주고 데이터는 넣지 않습니다.</div>
<div class="box ok"><b>② 먼저 시험, 그다음 실제</b><br>메일은 항상 <b>나에게 시험 발송</b> → 확인 → 실제 발송 순서. 실습은 가상 데이터로만 합니다.</div>
<div class="box warn"><b>③ 막히면 화면 그대로 복사</b><br>빨간 오류 문구를 그대로 복사해 AI에 붙여넣으면 고치는 방법을 알려줍니다. (<a href="#" data-go="p5">5. AI 활용</a>)</div>
</div>

<h2 class="sec">실습 파일</h2>
<a class="dl" href="practice/회원업무_실습데이터.xlsx" download>📥 실습 데이터(엑셀) 내려받기</a>
<a class="dl g" href="code/회원업무_전체코드.gs" download>📄 전체 코드</a>
<a class="dl g" href="code/Panel.html" download>📄 패널 화면(Panel.html)</a>
<div class="box info" style="margin-top:12px"><b>실습 데이터 안내</b> 성명·등록번호·이메일은 모두 <b>가상</b>입니다(등록번호 20001번대, 이메일 example.com).
실제 내려받은 파일의 특징은 그대로 살렸습니다: 첫 줄 제목행, 사무소명 끝 공백, 공익 파일의 등록번호 열 이름 <span class="ui">변리사</span>, 공익 명단에 이미 이수한 사람이 섞여 있음.</div>
<p class="foot-note">화면은 실제 구글 화면을 단순화한 모형입니다. 메뉴 이름과 위치는 실제와 같으며, 구글 화면이 일부 바뀌어도 빨간 번호 순서대로 같은 이름을 찾으면 됩니다.</p>
</div>"""

# ── 0. 준비 ──
import_dd = dropdown(["새로 만들기", "열기", ("가져오기", 2), "사본 만들기", "-", "공유", "이메일", "다운로드", "-", "버전 기록"])
import_dialog = dialog("파일 가져오기",
                       f'<div style="display:flex;gap:14px;border-bottom:1px solid #e0e0e0;margin-bottom:10px;color:#5f6368"><span>내 드라이브</span><span>최근 사용</span>{mk("<b style=color:#1a73e8>업로드</b>", 3)}</div>'
                       f'<div style="border:2px dashed #dadce0;border-radius:6px;padding:22px;text-align:center;color:#5f6368">파일을 여기로 드래그<br>또는<br>{mk("<span class=gbtn p>기기에서 파일 선택</span>", 4)}</div>',
                       '<span class="gbtn">취소</span>')
replace_dialog = dialog("파일 가져오기",
                        f'<div style="color:#5f6368;margin-bottom:6px">회원업무_실습데이터.xlsx</div><div><b>가져오기 위치</b></div>'
                        f'<div>○ 새 스프레드시트 만들기</div><div>○ 새 시트 삽입</div><div>{mk("● 스프레드시트 바꾸기", 5)}</div>',
                        f'<span class="gbtn">취소</span>{mk("<span class=gbtn p>데이터 가져오기</span>", 6)}')
ext_dd = dropdown(["부가기능", "매크로", ("Apps Script", 2), "AppSheet"], align="right")
pages["p0"] = f"""<div class="wrap">
<h2 class="sec">0. 준비 — 실습 시트 만들기<small>약 10분 · 엑셀 실습 파일을 구글 시트로 가져옵니다</small></h2>
{step("0-1", "새 구글 시트 열기", "빈 구글 시트를 하나 만듭니다.", [
    "크롬 주소창에 <kbd>sheets.new</kbd> 입력 후 <kbd>Enter</kbd>",
    "왼쪽 위 <span class='ui'>제목 없는 스프레드시트</span>를 눌러 이름을 <b>회원업무_실습</b>으로 바꾸기",
], ok="새 시트 왼쪽 위에 ‘회원업무_실습’이 보입니다.", stuck="로그인 화면이 나오면 회 업무용 구글 계정으로 로그인하세요.",
    figure=fig("m0-01", "새 시트 — 제목 바꾸기", sheet(rows=[["", "", "", ""]] * 6, tabs=["시트1"], active="시트1", title="회원업무_실습").replace("회원업무_실습 ☆", mk("회원업무_실습", 2) + " ☆")))}
{step("0-2", "실습 데이터 가져오기", "내려받은 엑셀 파일의 탭 5개를 한 번에 가져옵니다.", [
    "<a href='practice/회원업무_실습데이터.xlsx' download>실습 데이터(엑셀)</a>를 먼저 내려받기",
    "메뉴 <span class='ui'>파일</span> → <span class='ui'>가져오기</span>",
    "<span class='ui'>업로드</span> 탭 선택",
    "<span class='ui'>기기에서 파일 선택</span> → 내려받은 <b>회원업무_실습데이터.xlsx</b> 선택",
    "가져오기 위치: <span class='ui'>스프레드시트 바꾸기</span>",
    "<span class='ui'>데이터 가져오기</span> 클릭",
], ok="아래쪽에 <b>추천신청 · 메일양식 · 연수 · 공익 · 회비</b> 탭 5개가 생깁니다.",
    figure=fig("m0-02", "파일 → 가져오기", sheet(menu_mark=("파일", 1), dd_for=("파일", import_dd), rows=[["", "", ""]] * 7, tabs=["시트1"], active="시트1"))
    + "<div style='height:10px'></div>" + fig("m0-03", "업로드 → 파일 선택", sheet(rows=[["", "", ""]] * 7, tabs=["시트1"], active="시트1", overlay=import_dialog))
    + "<div style='height:10px'></div>" + fig("m0-04", "스프레드시트 바꾸기 → 데이터 가져오기", sheet(rows=[["", "", ""]] * 7, tabs=["시트1"], active="시트1", overlay=replace_dialog)))}
{step("0-3", "탭 5개 확인하기", "각 탭이 무슨 자료인지 알고 시작합니다.", [
    "<b>추천신청</b>: 구글폼 응답과 같은 모양(추천기관·성명·등록번호·이메일…)",
    "<b>메일양식</b>: 선정 안내 메일의 제목(B1)과 본문(B2)",
    "<b>연수 · 공익 · 회비</b>: 각 시스템에서 내려받은 미이수·미납 자료(2차 교육용)",
], ok="추천신청 탭에 28건의 가상 신청 내역이 보입니다.",
    figure=fig("m0-05", "가져온 결과 — 탭 5개", sheet(rows=[r[:5] for r in APPLY[:7]], tab_mark=("추천신청", 1))))}
{step("0-4", "Apps Script 편집기 열기", "자동화 코드를 넣을 곳을 엽니다.", [
    "메뉴 <span class='ui'>확장 프로그램</span> 클릭",
    "<span class='ui'>Apps Script</span> 클릭 → 새 탭이 열립니다",
    "왼쪽 위 <span class='ui'>제목 없는 프로젝트</span>를 눌러 이름을 <b>회원업무 자동화</b>로 바꾸기",
], ok="새 탭에 코드 편집 화면과 <code>function myFunction() {{}}</code> 이 보입니다.",
    stuck="‘Apps Script’ 메뉴가 없으면 회 계정 관리자가 Apps Script 사용을 막았을 수 있습니다. 개인 Gmail 계정으로 실습하세요.",
    figure=fig("m0-06", "확장 프로그램 → Apps Script", sheet(menu_mark=("확장 프로그램", 1), dd_for=("확장 프로그램", ext_dd), rows=[r[:5] for r in APPLY[:6]]))
    + "<div style='height:10px'></div>" + fig("m0-07", "Apps Script 편집기 첫 화면", editor(["function myFunction() {", "  ", "}"], fn="myFunction", marks={"project": 3})))}
</div>"""

# ── 1. 첫 자동화 ──
auth_needed = dialog("승인 필요", "이 프로젝트에서 내 데이터에 액세스하려면 승인이 필요합니다.",
                     f'<span class="gbtn">취소</span>{mk("<span class=gbtn p>권한 검토</span>", 1)}')
pages["p1"] = f"""<div class="wrap">
<h2 class="sec">1. 첫 자동화 — 나만의 메뉴 만들기<small>약 20분 · 코드 붙여넣기 → 저장 → 실행 → 권한 승인, 이 네 동작만 익히면 됩니다</small></h2>
{step("1-1", "코드 붙여넣기", "편집기에 있던 내용을 지우고 1단계 코드를 넣습니다.", [
    "아래 코드 상자의 <span class='ui'>전체 복사</span> 클릭",
    "편집기 코드 칸을 클릭 → <kbd>Ctrl</kbd>+<kbd>A</kbd> (전체 선택) → <kbd>Delete</kbd>",
    "<kbd>Ctrl</kbd>+<kbd>V</kbd> 로 붙여넣기",
], extra=code_block("1단계 코드", "01_첫자동화.gs", cid="code-first"), ok="편집기에 <code>function onOpen()</code> 으로 시작하는 코드가 보입니다.",
    figure=fig("m1-01", "붙여넣은 화면", editor(first_code[4:17], fn="myFunction", marks={})))}
{step("1-2", "저장하고 실행하기", "처음 한 번은 직접 실행해서 권한을 받아야 합니다.", [
    "💾 <span class='ui'>프로젝트 저장</span> 클릭 (또는 <kbd>Ctrl</kbd>+<kbd>S</kbd>)",
    "실행할 함수 목록에서 <span class='ui'>onOpen</span> 선택",
    "<span class='ui'>▷ 실행</span> 클릭",
], ok="‘승인 필요’ 창이 뜨면 정상입니다 → 다음 STEP",
    figure=fig("m1-02", "저장 → onOpen 선택 → 실행", editor(first_code[4:17], fn="onOpen", marks={"save": 1, "fn": 2, "run": 3})))}
{step("1-3", "권한 승인하기 (처음 한 번만)", "내가 만든 코드가 내 시트를 다룰 수 있게 허락합니다.", [
    "‘승인 필요’ 창에서 <span class='ui'>권한 검토</span>",
    "내 구글 계정 선택",
    "‘Google에서 확인하지 않은 앱’ 화면이 나오면 <span class='ui'>고급</span> → <span class='ui'>…(으)로 이동(안전하지 않음)</span>",
    "<span class='ui'>모두 선택</span> 체크 → <span class='ui'>계속</span> (예전 화면은 <span class='ui'>허용</span>)",
], ok="편집기 아래 실행 로그에 <b>실행이 완료됨</b> 이 표시됩니다.",
    stuck="‘확인하지 않은 앱’은 <b>내가 직접 만든 코드라서</b> 나오는 정상 경고입니다. 회 Workspace 계정이면 이 화면 없이 바로 넘어가기도 합니다. 자세히: 부록 A",
    extra="<div class='box info'><b>왜 묻나요?</b> 코드가 시트를 읽고 쓰고, 메일을 보내려면 계정 주인의 허락이 필요합니다. 한 번 허락하면 다음부터는 묻지 않습니다(새 기능을 추가하면 다시 물을 수 있음).</div>",
    figure=fig("m1-03", "승인 필요 → 권한 검토", editor(first_code[4:17], fn="onOpen") + auth_needed)
    + "<div style='height:10px'></div>" + fig("m1-04", "계정 선택", google_window("account"))
    + "<div style='height:10px'></div>" + fig("m1-05", "확인하지 않은 앱 → 고급 → 이동", google_window("unverified"))
    + "<div style='height:10px'></div>" + fig("m1-06", "모두 선택 → 계속", google_window("consent"))
    + "<div style='height:10px'></div>" + fig("m1-07", "실행 완료 로그", editor(first_code[4:17], fn="onOpen", log=[("알림", "실행이 시작됨"), ("알림", "실행이 완료됨")], marks={"log": 1})))}
{step("1-4", "시트에서 메뉴 확인 → 날짜 넣기", "만든 메뉴를 실제로 써 봅니다.", [
    "구글 시트 탭으로 돌아가 <kbd>F5</kbd> (새로고침)",
    "몇 초 뒤 메뉴 맨 오른쪽에 <span class='ui'>🗂 회원업무</span> 가 생기면 클릭",
    "빈 칸 하나를 선택한 뒤 <span class='ui'>오늘 날짜 넣기</span>",
], ok="선택한 칸에 오늘 날짜(예: 2026-11-04)가 들어갑니다. 🎉 첫 자동화 완성!",
    stuck="메뉴가 안 보이면 10초 기다린 뒤 다시 새로고침. 그래도 없으면 편집기에서 onOpen을 한 번 더 실행하세요.",
    figure=fig("m1-08", "새로 생긴 회원업무 메뉴", sheet(custom=True, custom_mark=2, dd_for=("🗂 회원업무", dropdown([("오늘 날짜 넣기", 3)], align="right")), rows=[r[:5] for r in APPLY[:6]])))}
<div class="box ok"><b>여기까지 배운 것</b> 코드 붙여넣기 → 💾 저장 → 함수 선택 → ▷ 실행 → (처음엔) 권한 승인 → 시트 새로고침.
앞으로 어떤 자동화든 <b>이 순서가 똑같습니다.</b></div>
</div>"""

# ── 2. 회원 추천 ──
dup_notes = {}
dup_colors = {}
rows_dup = [["추천기관", "성명", "등록번호", "이메일", "선정", "비고"]]
apply_body = APPLY[1:]
reg_count = {}
for r in apply_body:
    reg_count.setdefault(r[3], []).append(r[1])
show = [r for r in apply_body if len(reg_count[r[3]]) > 1][:6] + apply_body[:2]
for i, r in enumerate(show, start=1):
    orgs = reg_count[r[3]]
    note = ""
    if len(orgs) > 1:
        same = orgs.count(r[1]) > 1
        note = ("동일 기관 중복 · " if same else "") + f"중복 {len(orgs)}건: " + ", ".join(orgs)
        dup_colors[i] = "#f4cccc" if same else "#fff2cc"
    rows_dup.append([r[1], r[2], r[3], r[4], False, note])

menu_full = dropdown(["오늘 날짜 넣기", "-", ("① 추천: 중복 신청 확인", 2), "② 추천: 선정 메일 시험 발송(나에게)", "③ 추천: 선정 메일 실제 발송",
                      "④ 추천: 미선정자 목록 만들기", "-", "⑤ 현황: 연수·공익·회비 통합하기", "-", "작업 패널 열기"], width=250, align="right")
dup_alert = dialog("", "중복 신청자 4명을 찾았습니다.<br>· 노란색: 여러 기관에 신청<br>· 분홍색: 같은 기관에 두 번 이상 신청(2건)<br>[비고] 칸에서 내용을 확인하세요.",
                   '<span class="gbtn p">확인</span>')
sel_rows = apply_rows(6, selected={1, 2, 3})
for r in sel_rows[1:4]:
    r[4] = True
test_alert = dialog("", "시험 메일을 my.account@example.com 로 보냈습니다.<br>받은편지함에서 제목·본문을 확인한 뒤 [③ 실제 발송]을 실행하세요.<br>(실제 대상: 3명)", '<span class="gbtn p">확인</span>')
confirm = dialog("실제 발송", "3명에게 선정 안내 메일을 보냅니다. 진행할까요?", f'<span class="gbtn">아니요</span>{mk("<span class=gbtn p>예</span>", 2)}')
sent_rows = apply_rows(6, selected={1, 2, 3}, status={1: "발송완료", 2: "발송완료", 3: "발송완료"})
log_rows = [["발송일시", "성명", "등록번호", "이메일", "추천기관", "결과"]] + [
    ["2026-11-04 15:20:0" + str(i), r[2], r[3], r[4], r[1], "발송완료"] for i, r in enumerate(APPLY[1:4])]
tpl = FIX["메일양식"]
mail_body = tpl[1][1].replace("{성명}", APPLY[1][2]).replace("{추천기관}", APPLY[1][1]).replace("{등록번호}", str(APPLY[1][3]))
pages["p2"] = f"""<div class="wrap">
<h2 class="sec">2. 회원 추천 자동화<small>약 50분 · 중복 확인 → 선정 체크 → 시험 발송 → 실제 발송 → 미선정자 정리</small></h2>
<div class="flow"><div class="fs"><b>구글폼 응답</b>추천신청 탭</div><div class="ar">→</div><div class="fs"><b>① 중복 확인</b>색·비고 표시</div><div class="ar">→</div>
<div class="fs"><b>선정 체크</b>☑ 클릭</div><div class="ar">→</div><div class="fs"><b>② 시험 발송</b>나에게</div><div class="ar">→</div><div class="fs"><b>③ 실제 발송</b>+ 발송이력</div><div class="ar">→</div><div class="fs"><b>④ 미선정자</b>목록 탭</div></div>
{step("2-1", "전체 코드로 바꾸기", "1단계 코드를 지우고, 회원 업무 기능이 모두 들어 있는 전체 코드를 넣습니다.", [
    "Apps Script 편집기에서 <kbd>Ctrl</kbd>+<kbd>A</kbd> → <kbd>Delete</kbd>",
    "아래 <span class='ui'>전체 복사</span> → 편집기에 <kbd>Ctrl</kbd>+<kbd>V</kbd>",
    "💾 저장 → 함수 목록에서 <span class='ui'>onOpen</span> → <span class='ui'>▷ 실행</span> (권한을 다시 물으면 1-3과 같이 승인. 이번엔 ‘이메일 보내기’ 권한이 추가됩니다)",
    "시트 탭으로 돌아가 <kbd>F5</kbd>",
], extra=code_block("전체 코드 (2~4단계 공통)", "회원업무_전체코드.gs", tall=True, cid="code-full")
    + "<div class='box info'><b>코드를 다 읽을 필요는 없습니다.</b> 맨 위 <code>SHEET</code> 부분만 알면 됩니다. 실제 구글폼 응답 탭 이름이 ‘설문지 응답 시트1’처럼 다르면 <code>APPLY: '추천신청'</code>의 따옴표 안만 바꾸세요.</div>",
    ok="<span class='ui'>🗂 회원업무</span> 메뉴에 ①~⑤ 항목이 보입니다.",
    figure=fig("m2-01", "전체 코드 붙여넣기 → 저장 → onOpen 실행", editor(full_code[10:26], fn="onOpen", marks={"save": 1, "fn": 2, "run": 3}, project="회원업무 자동화"))
    + "<div style='height:10px'></div>" + fig("m2-02", "확장된 메뉴", sheet(custom=True, custom_mark=1, dd_for=("🗂 회원업무", menu_full), rows=apply_rows(6))))}
{step("2-2", "① 중복 신청 확인", "같은 사람(등록번호)이 여러 번 신청했는지 한 번에 찾습니다.", [
    "<span class='ui'>추천신청</span> 탭을 연 상태에서 <span class='ui'>🗂 회원업무</span> → <span class='ui'>① 추천: 중복 신청 확인</span>",
    "알림창 내용을 읽고 <span class='ui'>확인</span>",
    "오른쪽 끝에 새로 생긴 <span class='ui'>선정 · 비고 · 발송상태 · 발송일시</span> 열 확인",
], ok="중복 신청자 줄이 <span style='background:#fff2cc'>노란색</span>(여러 기관) 또는 <span style='background:#f4cccc'>분홍색</span>(같은 기관 두 번)으로 칠해지고, [비고]에 어느 기관에 냈는지 적힙니다.",
    extra="<div class='box info'><b>기준</b> 등록번호가 같으면 같은 사람으로 봅니다. 등록번호를 비워 낸 경우에는 <b>성명+연락처</b>로 비교합니다. 새 신청이 들어오면 다시 실행하면 됩니다(색·비고는 새로 계산).</div>",
    figure=fig("m2-03", "중복 확인 결과 알림", sheet(custom=True, rows=apply_rows(6), overlay=dup_alert))
    + "<div style='height:10px'></div>" + fig("m2-04", "중복자 색 표시와 비고", sheet(custom=True, rows=rows_dup, colors=dup_colors)))}
{step("2-3", "선정자 체크하기", "선정할 사람의 [선정] 칸에 체크합니다.", [
    "[선정] 열의 체크박스를 클릭해 ☑ 표시 (실습: 맨 위 3명)",
    "<b>실습 전용:</b> 체크한 3명의 [이메일]을 <b>내 메일 주소</b>로 바꾸기 (example.com은 실제로 받을 수 없음)",
], ok="체크한 칸이 파란 ☑ 로 바뀝니다.",
    figure=fig("m2-05", "선정 칸 체크", sheet(custom=True, rows=sel_rows, colors={})))}
{step("2-4", "메일 문구 확인·수정", "보낼 메일의 제목과 본문을 [메일양식] 탭에서 정합니다.", [
    "<span class='ui'>메일양식</span> 탭 열기",
    "<b>B1</b> = 제목, <b>B2</b> = 본문. 필요하면 문구 수정",
    "<code>{{성명}}</code> <code>{{추천기관}}</code> <code>{{등록번호}}</code> 처럼 <b>추천신청 탭 1행의 열 이름을 중괄호로 감싸면</b> 사람마다 자동으로 바뀝니다",
], ok="수정한 문구가 저장됩니다(구글 시트는 자동 저장).",
    figure=fig("m2-06", "메일양식 탭", sheet(custom=True, rows=[[r[0], r[1][:46] + ("…" if len(r[1]) > 46 else "")] for r in tpl], active="메일양식", tab_mark=("메일양식", 1))))}
{step("2-5", "② 나에게 시험 발송", "실제로 보내기 전에, 첫 번째 선정자용 메일을 내 메일함으로 보내 모양을 확인합니다.", [
    "<span class='ui'>🗂 회원업무</span> → <span class='ui'>② 추천: 선정 메일 시험 발송(나에게)</span>",
    "내 Gmail 받은편지함에서 <b>[시험]</b> 으로 시작하는 메일 열기",
    "이름·기관명이 제대로 바뀌었는지, 문구가 맞는지 확인",
], ok="받은편지함에 ‘[시험] [대한변리사회] … 추천 선정 안내’ 메일이 도착합니다. 시트의 [발송상태]는 바뀌지 않습니다.",
    figure=fig("m2-07", "시험 발송 알림", sheet(custom=True, rows=sel_rows, overlay=test_alert))
    + "<div style='height:10px'></div>" + fig("m2-08", "받은 시험 메일", gmail("[시험] " + tpl[0][1].replace("{추천기관}", APPLY[1][1]), mail_body)))}
{step("2-6", "③ 실제 발송", "체크한 사람에게 메일을 보내고 기록을 남깁니다.", [
    "<span class='ui'>🗂 회원업무</span> → <span class='ui'>③ 추천: 선정 메일 실제 발송</span>",
    "‘○명에게 보냅니다’ 확인 창에서 인원을 확인하고 <span class='ui'>예</span>",
    "[발송상태]·[발송일시] 칸과 새로 생긴 <span class='ui'>발송이력</span> 탭 확인",
], ok="[발송상태]에 <b>발송완료</b>가 찍히고 [발송이력] 탭에 한 줄씩 기록됩니다. 다시 실행해도 <b>발송완료인 사람에게는 다시 보내지 않습니다.</b>",
    stuck="[발송상태]가 ‘실패: 이메일 형식 오류’면 주소 오타를 고치고 다시 실행하세요. 하루 발송 한도를 넘으면 안내 후 멈춥니다(부록 E).",
    extra="<div class='box warn'><b>근거 기록</b> [발송이력] 탭은 지우지 마세요. 누가·언제·어떤 제목으로 받았는지가 남아 사후 확인 근거가 됩니다. 보낸 메일은 Gmail <b>보낸편지함</b>에도 남습니다.</div>",
    figure=fig("m2-09", "실제 발송 확인 창", sheet(custom=True, rows=sel_rows, overlay=confirm))
    + "<div style='height:10px'></div>" + fig("m2-10", "발송상태 기록", sheet(custom=True, rows=sent_rows, colors={}))
    + "<div style='height:10px'></div>" + fig("m2-11", "발송이력 탭", sheet(custom=True, rows=log_rows, tabs=["추천신청", "메일양식", "발송이력", "연수", "공익", "회비"], active="발송이력", tab_mark=("발송이력", 1))))}
{step("2-7", "④ 미선정자 목록 만들기", "선정되지 않은 사람만 따로 모아 안내·보관합니다.", [
    "<span class='ui'>🗂 회원업무</span> → <span class='ui'>④ 추천: 미선정자 목록 만들기</span>",
    "새로 생긴 <span class='ui'>미선정자</span> 탭 확인",
], ok="[미선정자] 탭에 추천기관·성명·등록번호·이메일이 정리됩니다. 실행할 때마다 새로 만들어집니다.",
    figure=fig("m2-12", "미선정자 탭", sheet(custom=True, rows=[["추천기관", "성명", "등록번호", "이메일"]] + [[r[1], r[2], r[3], r[4]] for r in APPLY[4:9]], tabs=["추천신청", "메일양식", "발송이력", "미선정자"], active="미선정자", tab_mark=("미선정자", 1))))}
{step("2-8", "실제 업무에 적용하기", "실습이 끝나면 실제 구글폼 응답 시트에 같은 코드를 넣습니다.", [
    "실제 응답 시트에서 <span class='ui'>확장 프로그램</span> → <span class='ui'>Apps Script</span> → 전체 코드 붙여넣기",
    "코드 맨 위 <code>APPLY: '추천신청'</code> 을 실제 응답 탭 이름으로 바꾸기",
    "응답 탭 1행에 <b>추천기관 · 성명 · 등록번호 · 이메일</b> 열이 있는지 확인(구글폼 질문 제목이 열 이름이 됩니다)",
    "[메일양식] 탭을 새로 만들고 A1 ‘제목’/B1, A2 ‘본문’/B2 입력",
    "반드시 <b>② 시험 발송</b>부터!",
], one=True, extra="<div class='box no'><b>주의</b> 구글폼 질문 제목이 ‘성함’, ‘변리사 등록번호’처럼 다르면 코드가 열을 찾지 못합니다. 이때는 오류 문구 그대로 <a href='#' data-go='p5'>AI에게 물어보거나</a>, 질문 제목을 위 이름으로 맞추세요.</div>")}
</div>"""

# ── 3. 현황 보드 ──
status_rows = [["등록번호", "성명", "연수 미이수", "공익 부족시간", "회비 미납액", "해당 항목 수", "지난번 대비"],
               [20036, "신*진", "O", 21.5, "300,000", 3, ""], [20008, "이*연", "O", 24, "", 2, ""], [20050, "조*희", "O", 15.5, "", 2, ""],
               [20022, "최*민", "", 19.5, "150,000", 2, ""], [20015, "박*호", "", 24, "", 1, ""], [20029, "홍*석", "O", "", "", 1, ""]]
status_colors = {1: "#f4cccc", 2: "#fce5cd", 3: "#fce5cd", 4: "#fce5cd"}
board_rows = [["항목", "인원"], ["전체 대상(1개 이상 해당)", 38], ["연수 미이수", 21], ["공익 미이수", 26], ["회비 미납", 12], ["2개 이상 해당", 18], ["3개 모두 해당", 3]]
chart = ('<div style="position:absolute;right:10px;top:118px;width:33%;background:#fff;border:1px solid #dadce0;border-radius:6px;padding:8px 10px;z-index:3">'
         '<div style="font-size:12px;margin-bottom:6px">항목별 인원</div>'
         + "".join(f'<div style="display:flex;align-items:center;gap:6px;margin:5px 0;font-size:11px"><span style="width:70px">{n}</span>'
                   f'<span style="height:12px;background:#4285f4;width:{v * 3}px;border-radius:2px"></span>{v}</div>' for n, v in (("연수", 21), ("공익", 26), ("회비", 12)))
         + "</div>")
pages["p3"] = f"""<div class="wrap">
<h2 class="sec">3. 연수·공익·회비 통합 현황 보드<small>2차 교육 · 약 40분 · 2주마다 받던 파일 대조를 버튼 하나로</small></h2>
<div class="box info"><b>받은 실제 자료를 분석해 보니</b> 공익 ‘미이수자’ 파일 4,543명 중 의무시간보다 수행시간이 적은 사람은 2,448명이었습니다.
나머지는 이미 채웠거나(1,902명) 의무가 없는(193명) 사람입니다. 그래서 이 보드는 <b>부족 시간이 있는 사람만</b> 미이수로 셉니다. 기준은 담당 부서와 확인 후 확정하세요.</div>
{step("3-1", "내려받은 파일 붙여넣기", "각 시스템에서 받은 파일 내용을 해당 탭에 그대로 붙여넣습니다.", [
    "연수 시스템 파일 → <span class='ui'>연수</span> 탭, 공익 → <span class='ui'>공익</span> 탭, 회비 → <span class='ui'>회비</span> 탭",
    "엑셀에서 전체 선택(<kbd>Ctrl</kbd>+<kbd>A</kbd>) → 복사 → 구글 시트 해당 탭 <b>A1</b> 칸 클릭 → 붙여넣기",
    "첫 줄 제목(예: ‘7차 연수 미이수자’)은 있어도 됩니다. 코드가 알아서 건너뜁니다",
], ok="세 탭에 각각 등록번호가 들어 있는 표가 보입니다.",
    extra="<table class='t'><tr><th>탭</th><th>꼭 있어야 하는 열</th></tr><tr><td>연수</td><td>등록번호, 성명, 사무소한글명(또는 사무소명)</td></tr>"
          "<tr><td>공익</td><td><b>등록번호 또는 변리사</b>, 성명, 의무시간, 수행시간</td></tr><tr><td>회비</td><td>등록번호, 성명, 미납액</td></tr></table>"
          "<div class='box warn'><b>회비 파일</b> 매일 바뀌므로, 보드를 갱신하기 직전에 그날 파일을 붙여넣으세요. 열 이름이 ‘미납액’과 다르면 알려주세요(코드 한 줄 수정).</div>",
    figure=fig("m3-01", "공익 탭 — 제목행과 ‘변리사’ 열 그대로", sheet(custom=True, rows=FIX["공익"][:7], active="공익", tab_mark=("공익", 1))))}
{step("3-2", "⑤ 통합하기 실행", "등록번호를 기준으로 세 자료를 한 줄로 합칩니다.", [
    "<span class='ui'>🗂 회원업무</span> → <span class='ui'>⑤ 현황: 연수·공익·회비 통합하기</span>",
    "<span class='ui'>통합현황</span> 탭: 사람별로 연수·공익·회비 해당 여부와 <b>해당 항목 수</b>",
    "<span class='ui'>현황보드</span> 탭: 항목별 인원과 그래프",
], ok="여러 항목에 걸린 사람이 맨 위로 정렬됩니다. <span style='background:#f4cccc'>분홍</span>=3개 모두, <span style='background:#fce5cd'>주황</span>=2개.",
    figure=fig("m3-02", "통합현황 탭", sheet(custom=True, rows=status_rows, colors=status_colors, tabs=["추천신청", "연수", "공익", "회비", "통합현황", "현황보드"], active="통합현황", tab_mark=("통합현황", 1)))
    + "<div style='height:10px'></div>" + fig("m3-03", "현황보드 탭", sheet(custom=True, rows=board_rows, tabs=["추천신청", "연수", "공익", "회비", "통합현황", "현황보드"], active="현황보드", overlay=chart)))}
{step("3-3", "2주 뒤: 새 파일로 다시 실행", "지난번과 비교해 새로 생긴 사람·해소된 사람을 자동으로 봅니다.", [
    "세 탭의 내용을 지우고(<kbd>Ctrl</kbd>+<kbd>A</kbd> → <kbd>Delete</kbd>) 새 파일 붙여넣기",
    "<span class='ui'>⑤ 통합하기</span> 다시 실행",
    "[통합현황]의 <b>지난번 대비</b> 열: <b>신규</b>(이번에 새로 생김) / <b>계속</b>(지난번에도 있었음)",
    "[현황보드]의 <b>지난번 대비 해소</b>: 지난번엔 있었는데 이번엔 없어진 인원",
], one=True, ok="2주마다 하던 수기 대조가 ‘붙여넣기 → 버튼 한 번’으로 끝납니다.")}
</div>"""

# ── 4. 버튼 패널 ──
panel_src = (CODE / "Panel.html").read_text(encoding="utf-8").splitlines()
add_dd = dropdown([("HTML", 2), "스크립트"], 60, 26, 120)
sidebar = ('<div class="sidebar"><div class="sb-t"><span>회원업무 패널</span><span>✕</span></div>'
           '<b style="font-size:12px;color:#0b1f4b">🗂 회원업무 패널</b><div style="font-size:10.5px;color:#5b626c;margin-top:4px">회원 추천</div>'
           + mk("<button>① 중복 신청 확인</button>", 1) + "<button>② 선정 메일 시험 발송(나에게)</button><button class='main'>③ 선정 메일 실제 발송</button>"
           "<button>④ 미선정자 목록 만들기</button><div style='font-size:10.5px;color:#5b626c;margin-top:4px'>현황</div><button>⑤ 연수·공익·회비 통합하기</button>"
           + mk("<div class='msg'>중복 신청자 4명을 찾았습니다.\n· 노란색: 여러 기관에 신청</div>", 2) + "</div>")
pages["p4"] = f"""<div class="wrap">
<h2 class="sec">4. 버튼 패널 만들기<small>2차 교육 · 약 20분 · 메뉴 대신 오른쪽 작업창에서 버튼으로 실행</small></h2>
{step("4-1", "HTML 파일 추가", "패널 화면을 담을 파일을 하나 더 만듭니다.", [
    "Apps Script 편집기 왼쪽 <span class='ui'>파일</span> 옆 <span class='ui'>＋</span>",
    "<span class='ui'>HTML</span> 선택",
    "파일 이름에 <b>Panel</b> 입력 후 <kbd>Enter</kbd> (.html은 자동으로 붙음, 대소문자 정확히)",
], ok="왼쪽 파일 목록에 <b>Panel.html</b> 이 생깁니다.",
    figure=fig("m4-01", "파일 ＋ → HTML", editor(["<!DOCTYPE html>", "<html>", "  <head>", "    <base target=\"_top\">", "  </head>", "  <body>", "  </body>", "</html>"],
                                               files=("Code.gs", "Panel.html"), active="Panel.html", fn="onOpen", marks={"add": 1}, project="회원업무 자동화", files_plus_dd=add_dd)))}
{step("4-2", "패널 코드 붙여넣기", "Panel.html 안의 내용을 모두 바꿉니다.", [
    "<b>Panel.html</b> 이 선택된 상태에서 <kbd>Ctrl</kbd>+<kbd>A</kbd> → <kbd>Delete</kbd>",
    "아래 코드 <span class='ui'>전체 복사</span> → <kbd>Ctrl</kbd>+<kbd>V</kbd> → 💾 저장",
], extra=code_block("패널 화면", "Panel.html", cid="code-panel"), ok="저장 후 오류 표시가 없으면 됩니다.",
    figure=fig("m4-02", "Panel.html 붙여넣기", editor(panel_src[0:16], files=("Code.gs", "Panel.html"), active="Panel.html", fn="onOpen", marks={"save": 1}, project="회원업무 자동화")))}
{step("4-3", "패널 열고 버튼 쓰기", "메뉴에서 패널을 열면 시트 오른쪽에 버튼 모음이 나타납니다.", [
    "시트에서 <span class='ui'>🗂 회원업무</span> → <span class='ui'>작업 패널 열기</span>",
    "오른쪽 패널의 버튼 클릭 → 결과가 패널 아래 회색 칸에 표시",
    "<span class='ui'>③ 실제 발송</span>은 인원 확인 창이 한 번 더 뜹니다",
], ok="메뉴를 찾지 않고 버튼으로 바로 실행할 수 있습니다. 패널을 연 채로 시트를 계속 볼 수 있습니다.",
    figure=fig("m4-03", "오른쪽 작업 패널", sheet(custom=True, rows=rows_dup[:6], colors=dup_colors, overlay=sidebar)))}
</div>"""

# ── 5. AI 활용 ──
pages["p5"] = f"""<div class="wrap">
<h2 class="sec">5. AI에게 요청하고 고치는 법<small>2차 교육 · 약 30분 · 오늘 만든 코드도 이 방법으로 만들었습니다</small></h2>
<div class="grid g3">
<div class="box ok"><b>✅ AI에게 줘도 되는 것</b><br>열 이름(1행), 탭 이름, 원하는 동작 설명, 오류 문구</div>
<div class="box no"><b>⛔ 주면 안 되는 것</b><br>회원 성명·등록번호·연락처·이메일이 들어 있는 실제 데이터, 파일 첨부</div>
<div class="box info"><b>💡 요령</b><br>“무엇을 → 어디서 → 어떤 결과로” 를 한 문장씩. 한 번에 한 기능만 요청.</div>
</div>
{step("5-1", "새 기능 요청하기", "열 이름만 알려주고 원하는 동작을 요청합니다.", [
    "아래 틀을 복사해 [ ] 부분만 내 상황으로 바꾸기",
    "Claude(또는 GPT)에 붙여넣기 → 받은 코드를 편집기에 붙여넣기 → 저장 → 실행",
    "결과가 다르면 ‘이렇게 됐는데 이렇게 바꿔줘’ 라고 이어서 요청",
], one=True, extra=prompt("""구글 시트 Apps Script 코드를 만들어줘. 나는 개발자가 아니라서 붙여넣고 실행만 할 거야.

[시트 정보] 탭 이름: [추천신청]
1행 열 이름: [타임스탬프, 추천기관, 성명, 등록번호, 이메일, 연락처, 선정]
(실제 데이터는 개인정보라 보여줄 수 없어. 열 이름만 보고 만들어줘.)

[원하는 기능] [선정 칸이 체크된 사람만 골라서 '선정자' 탭에 추천기관, 성명, 이메일만 정리]

[조건]
- 시트 위 메뉴에서 실행할 수 있게 onOpen 메뉴도 만들어줘
- 실행이 끝나면 몇 명을 처리했는지 알림창으로 알려줘
- 기존 데이터는 지우거나 바꾸지 마
- 어디에 붙여넣고 어떤 함수를 실행하는지 순서대로 알려줘"""))}
{step("5-2", "오류가 났을 때", "빨간 오류 문구를 그대로 복사해 붙여넣습니다.", [
    "편집기 아래 실행 로그(또는 알림창)의 오류 문구를 <b>전부</b> 복사",
    "아래 틀에 붙여넣어 AI에게 질문",
    "AI가 고쳐준 코드로 <b>전체 교체</b> → 저장 → 다시 실행",
], one=True, extra=prompt("""아래 Apps Script 코드를 실행했더니 오류가 났어. 원인과 고친 전체 코드를 알려줘.
개발자가 아니니 어디를 바꿨는지 쉽게 설명해줘.

[오류 문구]
(여기에 빨간 오류 문구를 그대로 붙여넣기)

[실행한 함수] (예: menuCheckDuplicates)
[시트 탭 이름과 1행 열 이름] (예: 추천신청 / 추천기관, 성함, 등록번호, 이메일)

[코드]
(편집기 코드를 전체 복사해서 붙여넣기)"""))}
{step("5-3", "오늘 코드를 조금 바꿔 보기 (연습)", "이미 만든 기능을 업무에 맞게 고쳐 달라고 요청합니다.", [
    "예 ①: “중복 확인할 때 등록번호 대신 <b>이메일</b>도 같으면 중복으로 봐줘”",
    "예 ②: “선정 메일에 <b>참고 파일 링크</b> 한 줄을 추가하고 싶어. 메일양식 B3에 링크를 넣으면 본문 끝에 붙게 해줘”",
    "예 ③: “통합현황에서 <b>3개 모두 해당</b>인 사람만 따로 탭으로 뽑아줘”",
], one=True, extra=prompt("""아래는 지금 쓰고 있는 Apps Script 전체 코드야. 다른 기능은 그대로 두고 [바꾸고 싶은 내용]만 반영한 전체 코드를 줘.
바뀐 부분은 주석으로 '// 변경'이라고 표시해줘.

[바꾸고 싶은 내용] (예: 중복 확인할 때 이메일이 같아도 중복으로 보기)

[현재 코드]
(편집기 코드 전체 붙여넣기)"""))}
<div class="box warn"><b>AI 답변을 그대로 믿지 않기</b> ① 항상 실습 시트(사본)에서 먼저 실행 ② 메일 기능은 시험 발송부터 ③ 이상하면 <b>파일 → 버전 기록</b>으로 되돌리기(부록 D)</div>
</div>"""

# ── 부록 ──
pages["ap"] = """<div class="wrap">
<h2 class="sec">부록</h2>
<h3 style="margin-top:20px">A. 권한 승인 화면이 무서울 때</h3>
<table class="t"><tr><th>화면</th><th>뜻</th><th>할 일</th></tr>
<tr><td>승인 필요</td><td>코드가 내 시트·메일을 쓰려면 허락이 필요함</td><td><span class="ui">권한 검토</span></td></tr>
<tr><td>Google에서 확인하지 않은 앱</td><td>구글 심사를 받지 않은 <b>내가 만든 코드</b>라는 뜻(외부 앱 아님)</td><td><span class="ui">고급</span> → <span class="ui">…(으)로 이동(안전하지 않음)</span></td></tr>
<tr><td>추가 액세스 요청(체크박스)</td><td>시트 수정, 메일 보내기 등 필요한 권한 목록</td><td><span class="ui">모두 선택</span> → <span class="ui">계속</span></td></tr>
<tr><td>이 앱은 차단되었습니다</td><td>회 Workspace 관리자가 막아 둔 경우</td><td>관리자에게 Apps Script 허용 요청 또는 개인 계정으로 실습</td></tr></table>
<h3>B. 자주 보는 오류</h3>
<table class="t"><tr><th>오류 문구(일부)</th><th>원인</th><th>해결</th></tr>
<tr><td>[추천신청] 탭을 찾을 수 없습니다</td><td>탭 이름이 다름</td><td>탭 이름을 바꾸거나 코드 맨 위 SHEET의 이름 수정</td></tr>
<tr><td>… 열이 필요합니다</td><td>1행 열 이름이 다름(예: ‘성함’)</td><td>1행 이름을 안내된 이름으로 맞추기</td></tr>
<tr><td>필요한 권한이 없습니다 / Authorization is required</td><td>새 기능에 대한 승인이 아직 안 됨</td><td>편집기에서 onOpen 실행 → 권한 승인</td></tr>
<tr><td>Service invoked too many times for one day: email</td><td>하루 메일 발송 한도 초과</td><td>다음 날 다시 실행(발송완료 건은 건너뜀)</td></tr>
<tr><td>Script function not found: …</td><td>코드 일부만 붙여넣었거나 저장 안 함</td><td>전체 다시 붙여넣기 → 💾 저장</td></tr>
<tr><td>메뉴가 안 보여요</td><td>새로고침 전이거나 onOpen 실행 전</td><td>F5 → 10초 대기 → 그래도 없으면 편집기에서 onOpen 실행</td></tr></table>
<h3>C. 실행 기록 보는 곳</h3>
<p>Apps Script 편집기 왼쪽 <span class="ui">≡ 실행</span> 메뉴 → 언제 어떤 함수가 실행됐고 성공/실패했는지 목록으로 보입니다. 실패 줄을 누르면 오류 문구가 나옵니다.</p>
<h3>D. 잘못했을 때 되돌리기</h3>
<p>시트: <span class="ui">파일</span> → <span class="ui">버전 기록</span> → <span class="ui">버전 기록 보기</span> → 이전 시점 선택 → <span class="ui">이 버전 복원</span>. 
코드: 편집기에서 <kbd>Ctrl</kbd>+<kbd>Z</kbd>, 또는 원래 코드를 이 교안에서 다시 복사해 붙여넣기.</p>
<h3>E. 메일 발송 한도</h3>
<table class="t"><tr><th>계정</th><th>하루 받는 사람 수(대략)</th></tr><tr><td>개인 Gmail</td><td>약 100명</td></tr><tr><td>Google Workspace(회 도메인)</td><td>약 1,500명</td></tr></table>
<p class="foot-note" style="margin-top:0">정확한 남은 수는 코드가 발송 직전에 확인하고, 모자라면 보내지 않고 알려줍니다.</p>
<h3>F. 개인정보 체크리스트</h3>
<ul style="margin-left:20px"><li>실습은 가상 데이터로만 했는가</li><li>AI에는 열 이름과 오류 문구만 넣었는가</li><li>실제 시트 공유 대상은 업무 담당자로 한정했는가(<span class="ui">공유</span> → ‘링크가 있는 모든 사용자’ 금지)</li><li>[발송이력] 탭을 지우지 않았는가</li></ul>
<h3>G. 화면 캡처 목록(교안 실제 화면 교체용)</h3>
<p>아래 화면 ID 이름으로 실제 캡처를 <code>appscript/shots/</code> 폴더에 PNG로 저장하면, 교안을 열 때 모형 화면 대신 실제 캡처가 자동으로 보입니다.</p>
<div id="shotlist"></div>
</div>"""

TABS = [("home", "", "홈"), ("p0", "0", "준비"), ("p1", "1", "첫 자동화"), ("p2", "2", "회원 추천"), ("p3", "3", "현황 보드"),
        ("p4", "4", "버튼 패널"), ("p5", "5", "AI 활용"), ("ap", "+", "부록")]

SCRIPT = r"""
const tabs = document.querySelectorAll('.tab');
function go(id, push){
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('show', p.id === id));
  tabs.forEach(t => t.classList.toggle('on', t.dataset.p === id));
  if (push !== false) history.replaceState(null, '', '#' + id);
  window.scrollTo(0, 0);
}
tabs.forEach(t => t.addEventListener('click', () => go(t.dataset.p)));
document.querySelectorAll('[data-go]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); go(a.dataset.go); }));
go((location.hash || '#home').slice(1) in {home:1,p0:1,p1:1,p2:1,p3:1,p4:1,p5:1,ap:1} ? location.hash.slice(1) || 'home' : 'home', false);

async function copyText(text, btn){
  try { await navigator.clipboard.writeText(text); }
  catch (e) { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
  const old = btn.textContent; btn.textContent = '복사됨 ✓'; btn.classList.add('done');
  setTimeout(() => { btn.textContent = old; btn.classList.remove('done'); }, 1600);
}
document.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', () => copyText(document.getElementById(b.dataset.copy).textContent, b)));
document.querySelectorAll('[data-copy-text]').forEach(b => b.addEventListener('click', () => {
  const box = b.parentElement.cloneNode(true); box.querySelector('button').remove(); copyText(box.textContent.trim(), b);
}));

// 실제 캡처(shots/<ID>.png)가 있으면 모형 대신 표시
const list = document.getElementById('shotlist');
const rows = [];
document.querySelectorAll('figure.shot').forEach(f => {
  const id = f.dataset.shot; rows.push([id, f.dataset.cap]);
  const img = new Image();
  img.onload = () => {
    const mock = f.querySelector('.mock'); mock.style.display = 'none';
    img.alt = f.dataset.cap; f.insertBefore(img, mock);
    const t = document.createElement('button'); t.className = 'tog'; t.textContent = '모형 보기';
    t.onclick = () => { const showMock = mock.style.display === 'none'; mock.style.display = showMock ? '' : 'none'; img.style.display = showMock ? 'none' : ''; t.textContent = showMock ? '실제 화면 보기' : '모형 보기'; };
    f.querySelector('figcaption').appendChild(t);
  };
  img.src = 'shots/' + id + '.png';
});
if (list) {
  const t = document.createElement('table'); t.className = 't';
  t.innerHTML = '<tr><th>화면 ID(파일 이름)</th><th>찍을 화면</th></tr>';
  rows.forEach(([id, cap]) => { const tr = t.insertRow(); tr.insertCell().textContent = id + '.png'; tr.insertCell().textContent = cap; });
  list.appendChild(t);
}
"""

nav = "".join(f'<button class="tab" data-p="{pid}">{f"<span class=tnum>{num}</span>" if num else ""}{label}</button>' for pid, num, label in TABS)
body = "".join(f'<main class="page" id="{pid}">{pages[pid]}</main>' for pid, _, _ in TABS)
css = (ROOT / "src" / "style.css").read_text(encoding="utf-8")
out = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>구글 시트 Apps Script 실습 교안 | 대한변리사회 회원서비스실</title>
<meta name="description" content="구글 시트와 Apps Script로 회원 추천·중복 확인·선정 메일·연수·공익·회비 통합 현황을 따라 만드는 실습 교안">
<style>{css}</style>
</head>
<body>
<nav class="nav"><div class="nav-inner"><div class="brand"><div class="logo">AS</div><div><div class="bt">Apps Script 실습</div><div class="bs">대한변리사회 회원서비스실</div></div></div><div class="tabs">{nav}</div></div></nav>
{body}
<script>{SCRIPT}</script>
</body>
</html>
"""
(ROOT / "index.html").write_text(out, encoding="utf-8")
print("wrote", ROOT / "index.html", len(out), "bytes;", out.count('class="shot"'), "screens")
