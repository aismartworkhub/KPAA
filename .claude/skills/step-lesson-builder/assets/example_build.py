"""예시 교안 — 모든 부품 사용법을 보여주는 최소 예제(2개 실습 탭 + 홈 + 부록).
실행: python3 example_build.py <출력폴더>   → <출력폴더>/index.html
새 교안을 만들 때 이 파일을 복사해 내용만 바꾸는 것이 가장 빠르다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lessonkit import (Page, box, build, cards, chat_view, code_block, dialog, dropdown, fig, figs, flow, gbtn, google_auth,
                       hero, kbd, mk, prompt, section, sheets_window, shot_list_section, step, table, ui, wrap)

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "example_out")
PC = "편집 작업은 휴대폰에서 하기 어렵습니다. 휴대폰에서는 화면 확인·복습용으로 보세요. 그림은 탭하면 크게 볼 수 있습니다."
rows = [["이름", "부서", "완료"], ["김*수", "총무", False], ["이*연", "홍보", True], ["박*호", "회원", False]]

home = hero("예시 기관 · 실습 교안", "구글 시트로<br><em>업무 체크리스트 자동화</em>",
            "화면 순서대로 따라 하면 누구나 버튼 하나로 체크리스트를 정리할 수 있습니다.") + wrap(
    section("오늘 만드는 것", "실제 업무 그대로 실습합니다")
    + cards([("🧭", "메뉴 만들기", "시트 위에 나만의 메뉴"), ("✅", "자동 정리", "완료 항목 표시"), ("🤖", "AI 활용", "요청·수정하는 법")], cols=3)
    + section("진행 순서") + flow([("1. 준비", "시트 만들기"), ("2. 자동화", "메뉴·실행"), ("3. AI", "요청하기")])
    + table(["회차", "일시", "내용"], [["1차", "11. 4.(수) 15:00", "1·2단계"], ["2차", "11. 13.", "3단계"]])
    + box("info", "원칙", "개인정보는 시트 안에서만 처리하고 AI에는 열 이름만 알려줍니다."))

p1 = wrap(section("1. 준비", "약 10분") + step(
    "1-1", "확장 프로그램 열기", "자동화 코드를 넣을 편집기를 엽니다.",
    [f"메뉴 {ui('확장 프로그램')} 클릭", f"{ui('Apps Script')} 클릭"],
    ok="새 탭에 코드 편집기가 열립니다.", stuck="메뉴가 없으면 관리자에게 Apps Script 허용을 요청하세요.",
    figure=fig("m1-01", "확장 프로그램 → Apps Script", sheets_window(
        rows, title="체크리스트", marks={"확장 프로그램": 1},
        dd_for=("확장 프로그램", dropdown(["부가기능", "매크로", ("Apps Script", 2)], align="right"))))), pc_note=PC)

p2 = wrap(section("2. 자동화", "약 20분") + step(
    "2-1", "코드 붙여넣고 실행", "코드를 넣고 처음 한 번 권한을 승인합니다.",
    [f"아래 {ui('전체 복사')}", f"편집기에서 {kbd('Ctrl', 'A')} → {kbd('Ctrl', 'V')}", f"💾 저장 → {ui('▷ 실행')}", f"{ui('권한 검토')} → 계정 선택 → {ui('고급')} → 이동 → {ui('계속')}"],
    extra=code_block("예시 코드", text="function onOpen() {\n  SpreadsheetApp.getUi().createMenu('업무').addItem('정리', 'tidy').addToUi();\n}\n", cid="code-ex"),
    ok="시트를 새로고침하면 메뉴에 '업무'가 생깁니다.",
    figure=figs(fig("m2-01", "승인 필요 → 권한 검토", sheets_window(rows, title="체크리스트", overlay=dialog("승인 필요", "이 프로젝트에서 내 데이터에 액세스하려면 승인이 필요합니다.", gbtn("취소") + gbtn("권한 검토", True, 1)))),
                fig("m2-02", "확인하지 않은 앱 → 고급 → 이동", google_auth("unverified")),
                fig("m2-03", "새로 생긴 메뉴", sheets_window(rows, title="체크리스트", extra_menus=("업무",), marks={"업무": 1},
                                                          dd_for=("업무", dropdown([("정리", 2)], align="right")))))
) + step("2-2", "AI에게 수정 요청", "열 이름만 알려주고 기능을 요청합니다.",
         ["아래 틀을 복사해 [ ] 부분만 바꾸기", "AI 답변의 코드를 편집기에 붙여넣기"],
         extra=prompt("구글 시트 Apps Script 코드를 만들어줘.\n[탭 이름] 체크리스트\n[1행 열 이름] 이름, 부서, 완료\n[원하는 기능] 완료가 체크된 줄을 회색으로"),
         ok="AI가 붙여넣을 위치와 실행할 함수 이름을 알려 주면 성공입니다.",
         figure=fig("m2-04", "AI에게 요청", chat_view([("user", "완료된 줄을 회색으로 칠하는 코드를 만들어줘"), ("ai", "아래 코드를 붙여넣고 tidy를 실행하세요…")],
                                                  marks={0: 1, "send": 2}))), pc_note=PC)

ap = wrap(section("부록") + "<h3>자주 보는 오류</h3>" + table(["오류", "해결"], [["탭을 찾을 수 없습니다", "탭 이름 확인"]]) + shot_list_section())

build(OUT / "index.html", [Page("home", "", "홈", home), Page("p1", "1", "준비", p1), Page("p2", "2", "자동화", p2), Page("ap", "+", "부록", ap)],
      title="예시 교안", description="lessonkit 예시", brand=("EX", "예시 교안", "예시 기관"),
      site_url="https://example.github.io/repo/lesson/", og_image="og_image.jpg")
print("wrote", OUT / "index.html")
