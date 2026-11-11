# 제5회 스마트워크톤 배너 (2026. 11. 20 · 서울시청 시민청)

| # | 배너 | 크기 | 용도 |
|---|---|---|---|
| 01 | 행사 메인 | X배너 600×1800mm | 행사명·일시·장소·트랙 소개 |
| 02 | 경진 안내 | X배너 600×1800mm | AI 활용도 평가(10:00–10:30, 1·2·3등 상금) → 트랙 A/B → 시상 |
| 03 | 강당 입구 안내 | X배너 600×1800mm | 시민청 강당 앞 — 접수·명찰·착석 3단계, 10:00 시작 안내 |
| 04 | 후기 이벤트 | X배너 600×1800mm | 참여자 전원 증정 — EVENT 01(SNS)·02(블로그·카페), 참여 방법 3단계, 구글폼 QR |
| 05 | 플리마켓 | 1006×576 (mm 또는 px) | 가로형 — 구경·체험·득템 |

## 파일 (output/)

- `*.pdf` — **인쇄소에 보낼 파일.** 실제 크기(mm), 글꼴 포함, 글자는 벡터
- `*_인쇄용.jpg` — PDF를 받지 않는 인쇄소용 고해상도(약 150dpi)
- `*_미리보기.png` — 화면 확인용
- `05_…_화면용_1006x576px.png` — 플리마켓 배너를 모니터·TV로 띄울 때 쓰는 원본 크기

## 로고 (assets/)

- `aish_logo_원본.png` — 받은 로고 원본 (534×307px)
- `aish_logo.svg` — 원본을 벡터로 바꾼 것 (원래 색, 밝은 배경용 · 04번에 사용)
- `aish_logo_white.svg` — 흰색 반전본 (어두운 배경용 · 01·02·03·05번에 사용)
- 다시 만들기: `python3 assets/trace_logo.py` (`pip install potracer` 필요)

## 후기 이벤트 구글폼 · QR (review-form/)

1. `review-form/createReviewForm.gs` 를 script.google.com 새 프로젝트에 붙여넣고 `createReviewForm` 실행
   → 구글폼 + 응답 시트(선물 발송 명단)가 내 드라이브에 만들어지고, 실행 로그에 짧은 주소(forms.gle/…)가 나옴
2. `python3 review-form/make_qr.py https://forms.gle/…` → `assets/review_qr.svg` (`pip install segno` 필요)
3. `node render.mjs 04_후기이벤트_X배너.html`

QR이 비어 있는 상태로 출력하면 render.mjs 가 경고를 띄웁니다. 경품·마감일을 바꾸면 배너 HTML과 .gs 의 CONFIG 를 같이 고치세요.

## 문구 고치기

1. 해당 `.html` 파일을 열어 글자를 고칩니다 (색·글꼴은 `banner.css`)
2. 다시 출력합니다:

```bash
node render.mjs                 # 전체
node render.mjs 04_후기이벤트_X배너.html   # 하나만
```

캔버스 단위는 **1px = 실제 1mm** 입니다. 글꼴은 Google Fonts(Black Han Sans · Noto Sans KR · Montserrat)를 쓰므로 출력할 때 인터넷이 필요합니다.
