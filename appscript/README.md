# 구글 시트 Apps Script 실습 교안 (회원서비스실)

대한변리사회 회원서비스실 **회원 관리 업무 AI 활용 교육**용 실습 교안입니다.
회의(회원 관리 업무 AI 활용 방안)에서 정한 내용 — 회원 추천 중복 확인·선정 메일 자동 발송, 연수·공익·회비 통합 현황 — 을 구글 시트와 Apps Script로 따라 만듭니다.

- 교안 열기: `index.html` (GitHub Pages 배포 시 `https://aismartworkhub.github.io/KPAA/appscript/`)
- 인쇄: 브라우저 인쇄(Ctrl+P) 시 전 단계가 출력됩니다.

| 회차 | 내용 |
|---|---|
| 1차 (11. 4.) | 0 준비 · 1 첫 자동화(메뉴·권한 승인) · 2 회원 추천 자동화 |
| 2차 (11. 13.) | 3 통합 현황 보드 · 4 버튼 패널 · 5 AI에게 요청·수정하는 법 |

## 구성
| 경로 | 내용 |
|---|---|
| `index.html` | 교안 (빌드 결과물 — 직접 고치지 말고 `src/` 수정 후 빌드) |
| `code/01_첫자동화.gs` | 1단계 코드 (메뉴 + 오늘 날짜) |
| `code/회원업무_전체코드.gs` | 2~4단계 전체 코드 (중복 확인, 시험/실제 메일, 미선정자, 통합 현황·보드, 패널 열기) |
| `code/Panel.html` | 오른쪽 작업 패널 화면 |
| `practice/회원업무_실습데이터.xlsx` | 실습용 **가상** 데이터 (추천신청·메일양식·연수·공익·회비) |
| `og_image.jpg` | 카카오톡·SNS 링크 미리보기 이미지(1200×630) — `src/og.html` 수정 후 `node src/make_og.mjs` |
| `shots/` | 실제 화면 캡처를 넣는 곳 (넣으면 교안의 모형 화면이 자동 교체) |
| `src/build.py`, `src/style.css` | 교안 생성기 — 코드 파일 내용을 그대로 교안에 넣음 |
| `tests/gas_mock_test.mjs` | Apps Script 코드를 모의 시트에서 실행해 검증 (16개 항목) |
| `tests/make_practice_data.py` | 가상 실습 데이터 생성기 |

## 고치고 다시 만들기
```bash
python3 appscript/tests/make_practice_data.py appscript/practice/회원업무_실습데이터.xlsx appscript/tests/practice_fixture.json  # 데이터 바꿀 때만
node appscript/tests/gas_mock_test.mjs     # 코드 검증
python3 appscript/src/build.py             # 교안 다시 만들기
```

## 개인정보
실습 데이터는 모두 가상입니다(등록번호 20001번대, 이메일 example.com). 실제 회원 자료는 이 저장소(Public)에 올리지 않습니다.
교안의 실제 자료 분석 수치(공익 4,543명 중 실제 미이수 2,448명 등)는 집계값만 사용했습니다.
