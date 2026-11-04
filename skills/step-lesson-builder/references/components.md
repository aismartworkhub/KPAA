# lessonkit 부품 목록

`from lessonkit import *` 후 문자열(HTML 조각)을 이어 붙여 페이지를 만든다. 사용자 문자열은 부품이 이스케이프한다
(todo·ok·stuck·goal처럼 HTML을 받는 인자에 사용자 원문을 넣을 때는 `E()`로 감쌀 것).

## 페이지 뼈대
| 함수 | 용도 |
|---|---|
| `hero(eyebrow, title_html, desc)` | 홈 상단. title_html에서 강조는 `<em>` |
| `wrap(inner, pc_note=None)` | 탭 본문 래퍼. pc_note → 휴대폰 전용 "실습은 PC에서" 안내 |
| `section(title, sub)` | 큰 제목 + 작은 설명 |
| `cards([(아이콘, 제목, 설명HTML)], cols)` | 기능 카드 |
| `flow([(제목, 설명)])` | 화살표 흐름도 (휴대폰에선 2열) |
| `table(headers, rows, raw=False)` | 일반 표 (raw=True면 셀에 HTML 허용) |
| `box(kind, title, body_html)` | ok / warn / no / info 안내 상자 |
| `downloads([(href, 라벨, 'g'|'')])` | 내려받기 버튼 |
| `Page(pid, num, label, html)` + `build(out, pages, title=, description=, brand=(로고글자, 제목, 부제), site_url=, og_image=)` | 최종 HTML 생성 |

## 단계·코드
| 함수 | 용도 |
|---|---|
| `step(no, title, goal, todo, ok=, stuck=, figure=, extra=, one=)` | 단계 카드 (one=True: 그림 없이 1열) |
| `fig(sid, cap, inner)` / `figs(*fig)` | 그림 1장 / 여러 장 세로 배치 |
| `code_block(title, path= or text=, cid=, download_href=, tall=)` | 코드 상자 + 전체 복사(+내려받기). cid는 페이지에서 고유 |
| `prompt(text)` | AI 프롬프트 카드(복사) |
| `ui(label)`, `kbd(*keys)`, `mk(html, n)` | 화면 이름 표기, 키보드, 빨간 번호 |

## 모형 화면
| 함수 | 그리는 것 | 번호 다는 법 |
|---|---|---|
| `sheets_window(rows, title, marks={'파일':1}, dd_for=('파일', dropdown(...)), extra_menus=('🗂 메뉴',), tabs, active, tab_marks={'탭':1}, colors={행:'#색'}, overlay=)` | 구글 시트 | marks / dropdown 항목 튜플 / tab_marks |
| `grid(rows, colors)` | 표 격자만(앱 창 안에 넣을 때). True/False → 체크박스 | — |
| `code_editor(lines, files, active, fn, marks={'save':1,'fn':2,'run':3,'add':1,'project':1,'log':1,'file:이름':1}, log=[(유형,메시지)], files_dd=dropdown(...,left=,top=))` | 코드 편집기(Apps Script형) | marks 키 |
| `google_auth('account'|'unverified'|'consent', app_name)` | 구글 권한 승인 화면 3종 | 고정(1·2) |
| `dialog(title, body_html, buttons_html)` + `gbtn(label, primary, n)` | 확인창(overlay로) | gbtn의 n |
| `sidebar(title, inner_html)` | 오른쪽 작업 패널(overlay로) | inner에서 mk |
| `mail_view(subject, body, sender, to)` | 받은 메일 | 제목 1, 본문 2 |
| `chat_view([('user'|'ai', 텍스트)], input_text, app, marks={0:1,'input':2,'send':3})` | AI 대화(Claude·GPT 등) | 메시지 순번 / input / send |
| `app_window(title, body_html, icon_color, menus=[...], marks, dd_for, overlay)` | 범용 웹·앱(캔바·노션·사내 시스템) | menus marks + body에서 mk |
| `dropdown(items, align='left'|'right', width)` | 펼친 메뉴. items에 `('항목', 번호)`, `'-'` 구분선 | 튜플 |

예: 캔바 "디자인 만들기" 버튼
```python
app_window("Canva", f'{mk(gbtn("디자인 만들기", True), 1)} <span class="minput">검색</span>' + grid([["템플릿","크기"],["카드뉴스","1080x1080"]]), icon_color="#7d2ae8")
```

## 런타임(자동)
탭 전환(#주소 유지), 코드·프롬프트 복사, `shots/<ID>.png` 실제 캡처 자동 교체·토글, 부록 촬영 목록(`shot_list_section()` 자리),
휴대폰 그림 폭 맞춤·탭 확대, 인쇄 시 전체 출력.
