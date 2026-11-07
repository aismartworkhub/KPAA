"""Claude 웹(claude.ai) 화면 모형 부품 — 이 교안 전용. build(..., extra_css=CL_CSS)로 스타일을 넣는다.
실제 화면을 단순화한 것이며, 메뉴 문구는 계정 언어·업데이트에 따라 조금 다를 수 있다."""
from lessonkit import E, app_window, mk

CL_CSS = """
.nav-inner{max-width:1260px}
@media (min-width:900px){.tab{padding:13px 8px}}
.cl{display:grid;grid-template-columns:118px 1fr 176px;min-height:270px;font-size:12px;background:#fff}
.cl.two{grid-template-columns:118px 1fr}
.cl-side{background:#f5f4ef;padding:8px 6px;border-right:1px solid #e5e2da;display:flex;flex-direction:column;gap:2px}
.cl-side>div,.cl-side>.mk{padding:4px 7px;border-radius:6px}
.cl-side .on{background:#e9e6dc;font-weight:700}
.cl-side .new{color:#c96442;font-weight:800}
.cl-main{padding:12px 14px}
.cl-main h5{font-size:16px;margin-bottom:2px}
.cl-main .desc{color:#6b6b6b;margin-bottom:10px}
.cl-in{border:1px solid #d6d3cc;border-radius:12px;padding:10px 12px;color:#777;background:#fff;display:flex;justify-content:space-between;gap:8px}
.cl-in .send{background:#c96442;color:#fff;border-radius:8px;padding:0 9px}
.cl-hist{margin-top:12px;color:#555}.cl-hist div{border-bottom:1px solid #eee;padding:5px 0}
.cl-right{border-left:1px solid #e5e2da;padding:10px 8px;background:#fbfaf7}
.cl-box{border:1px solid #e5e2da;border-radius:8px;padding:7px 8px;margin-bottom:8px;background:#fff}
.cl-box .h{display:flex;justify-content:space-between;font-weight:700;margin-bottom:3px}
.cl-box .t{color:#777;font-size:11px;white-space:pre-wrap;line-height:1.45}
.cl-file{display:block;font-size:10.5px;border:1px solid #e5e2da;border-radius:6px;padding:3px 6px;margin-top:4px;background:#fff;word-break:break-all}
.cl-btn{display:inline-block;border:1px solid #d6d3cc;border-radius:8px;padding:4px 10px;background:#fff;font-weight:700}
.cl-btn.p{background:#c96442;border-color:#c96442;color:#fff}
.cl-ta{border:1px solid #d6d3cc;border-radius:8px;padding:8px;min-height:96px;color:#444;font-size:11.5px;white-space:pre-wrap;line-height:1.45;background:#fff;text-align:left}
.cl-set{display:grid;grid-template-columns:130px 1fr;min-height:250px;font-size:12px}
.cl-set .nav2{background:#f5f4ef;padding:10px 6px;border-right:1px solid #e5e2da}
.cl-set .nav2 div{padding:4px 8px;border-radius:6px}.cl-set .nav2 .on{background:#e9e6dc;font-weight:700}
.cl-set .body{padding:14px}
.cl-set .row{display:flex;justify-content:space-between;align-items:center;gap:12px;border-bottom:1px solid #eee;padding:10px 0}
.cl-set .row small{display:block;color:#777;font-size:11px}
.tg{display:inline-block;width:36px;height:20px;border-radius:10px;background:#c96442;position:relative;flex:none}
.tg::after{content:"";position:absolute;top:2px;left:18px;width:16px;height:16px;border-radius:50%;background:#fff}
.tg.off{background:#c4c4c4}.tg.off::after{left:2px}
.att{display:inline-block;border:1px solid #d6d3cc;background:#fff;border-radius:8px;padding:2px 8px;font-size:11px;margin-bottom:4px}
.mtbl{border-collapse:collapse;font-size:10.5px;margin-top:6px;width:100%}
.mtbl td,.mtbl th{border:1px solid #ddd;padding:3px 5px;vertical-align:top;text-align:left}
.mtbl th{background:#f3f1ec}
.drv{font-size:12px}.drv .r{display:grid;grid-template-columns:24px 1fr 90px;border-bottom:1px solid #eee;padding:6px 4px}
.drv .r.h{color:#777;font-weight:700}
.np{font-family:Consolas,monospace;font-size:11.5px;white-space:pre-wrap;line-height:1.5;padding:10px;min-height:220px}
.np .hl{background:#fff2a8}
"""

SIDE = ["＋ 새 채팅", "채팅", "프로젝트", "아티팩트"]


def cl_side(on="프로젝트", marks=None):
    marks = marks or {}
    out = []
    for s in SIDE:
        cls = "on" if s == on else ("new" if s.startswith("＋") else "")
        h = f'<div class="{cls}">{E(s)}</div>'
        out.append(mk(h, marks[s], block=True) if s in marks else h)
    return f'<div class="cl-side">{"".join(out)}<div style="margin-top:auto;color:#999">최근</div></div>'


def claude_projects_list(marks=None, overlay=""):
    """프로젝트 목록 화면: 오른쪽 위 '＋ 새 프로젝트'"""
    marks = marks or {}
    btn = '<span class="cl-btn p">＋ 새 프로젝트</span>'
    btn = mk(btn, marks["new"]) if "new" in marks else btn
    body = (f'<div class="cl two">{cl_side("프로젝트", {"프로젝트": marks["side"]} if "side" in marks else None)}'
            f'<div class="cl-main"><div style="display:flex;justify-content:space-between;align-items:center"><h5>프로젝트</h5>{btn}</div>'
            f'<div class="desc">주제별로 채팅과 자료를 한곳에 모아 둡니다</div>'
            f'<div class="cl-hist"><div>📁 예시 프로젝트 · 1주 전</div></div></div></div>')
    return app_window("Claude", body, icon_color="#c96442", overlay=overlay)


def claude_project(name, instr="", files=(), chats=(), marks=None, overlay="", input_text="이 프로젝트에서 새 채팅 시작…"):
    """프로젝트 첫 화면: 가운데 입력창 + 오른쪽 '지침'·'파일' 상자. marks 키: instr, files, input, send"""
    marks = marks or {}

    def m(key, h, block=False):
        return mk(h, marks[key], block=block) if key in marks else h
    instr_html = E(instr) if instr else "Claude가 이 프로젝트에서 어떻게 답할지 정합니다"
    ih = f'<div class="cl-box"><div class="h"><span>지침</span><span>✎</span></div><div class="t">{instr_html}</div></div>'
    fl = "".join(f'<span class="cl-file">📄 {E(f)}</span>' for f in files) or '<div class="t">문서·PDF·표를 올려 두면 모든 채팅에서 참고합니다</div>'
    fh = f'<div class="cl-box"><div class="h"><span>파일</span><span>＋</span></div>{fl}</div>'
    inp = m("input", f'<span>{E(input_text)}</span>') + m("send", '<span class="send">↑</span>')
    hist = "".join(f"<div>💬 {E(c)}</div>" for c in chats)
    body = (f'<div class="cl">{cl_side("프로젝트")}'
            f'<div class="cl-main"><h5>📁 {E(name)}</h5><div class="desc">비공개 · 나만 볼 수 있음</div>'
            f'<div class="cl-in">{inp}</div><div class="cl-hist">{hist}</div></div>'
            f'<div class="cl-right">{m("instr", ih, True)}{m("files", fh, True)}</div></div>')
    return app_window("Claude", body, icon_color="#c96442", overlay=overlay)


def claude_settings(marks=None):
    marks = marks or {}
    nav = "".join(f'<div class="{"on" if n == "개인정보 보호" else ""}">{mk(E(n), marks["nav"]) if n == "개인정보 보호" and "nav" in marks else E(n)}</div>'
                  for n in ["일반", "계정", "개인정보 보호", "결제", "기능"])
    tg = mk('<span class="tg off"></span>', marks["toggle"]) if "toggle" in marks else '<span class="tg off"></span>'
    body = (f'<div class="cl-set"><div class="nav2">{nav}</div><div class="body"><b style="font-size:14px">개인정보 보호</b>'
            f'<div class="row"><span>Claude(AI 모델) 개선에 도움<small>켜 두면 내 채팅이 앞으로의 모델 학습에 쓰일 수 있습니다</small></span>{tg}</div>'
            f'<div class="row"><span>위치 메타데이터<small>답변에 대략적인 위치 정보 활용</small></span><span class="tg off"></span></div>'
            f'<div class="row"><span>데이터 내보내기</span><span class="cl-btn">내보내기</span></div></div></div>')
    return app_window("Claude · 설정", body, icon_color="#c96442")


def chat(messages, marks=None, input_text="답장…"):
    """첨부·표가 들어가는 대화. messages=[(who, html)] — html은 이미 안전한 조각(E() 처리)"""
    marks = marks or {}
    out = []
    for i, (who, h) in enumerate(messages):
        m = f'<div class="msg {who}">{h}</div>'
        out.append(mk(m, marks[i], block=True) if i in marks else m)
    inp = f'<span>{E(input_text)}</span>'
    inbox = f'<div class="inbox">{mk(inp, marks["input"]) if "input" in marks else inp}{mk("<span class=send>↑</span>", marks["send"]) if "send" in marks else "<span class=send>↑</span>"}</div>'
    return (f'<div class="win-top"><span class="win-icon" style="background:#c96442"></span><span class="win-title">Claude · 📁 변리사법 위반 신고 검토</span></div>'
            f'<div class="chat">{"".join(out)}{inbox}</div>')


def mtable(headers, rows):
    head = "".join(f"<th>{E(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{E(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="mtbl"><tr>{head}</tr>{body}</table>'


def att(name):
    return f'<span class="att">📎 {E(name)}</span><br>'
