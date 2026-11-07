# KPAA — 정책홍보실 AX 교육 자료

대한변리사회 정책홍보실 **AI 업무혁신(AX) 교육** 통합 교안과 부속 자료를 배포하는 저장소입니다.

## 회원서비스실 Apps Script 실습 교안

구글 시트로 회원 추천(중복 확인·선정 메일)과 연수·공익·회비 통합 현황을 만드는 실습 교안입니다 → [`appscript/`](appscript/README.md)
(Pages 배포 시 https://aismartworkhub.github.io/KPAA/appscript/)

## 회원서비스실 Claude 업무 실습 교안

변리사법 위반 신고 처리(근거 인용 프로젝트 지침, 보고 메일·소명 공문·쟁점 비교표, 징계 사례 DB, 진행경과 시트)와 회원 안내 이미지 고정 틀을 따라 만드는 교안입니다 → [`claude-work/`](claude-work/README.md)
(Pages 배포 시 https://aismartworkhub.github.io/KPAA/claude-work/)

## 윤리·징계·광고 업무지원 시스템

회원서비스실 윤리·징계·광고 업무용 웹 시스템은 [`ethics-system/`](ethics-system/README.md)에 있습니다.
사내 서버에 설치해 사용하며(GitHub Pages로는 동작하지 않음), 설치 방법은 [`ethics-system/docs/DEPLOY.md`](ethics-system/docs/DEPLOY.md)를 참고하세요.

## 배포 주소

GitHub Pages로 배포하면 아래 주소에서 열립니다.

- 통합 교안 → https://aismartworkhub.github.io/KPAA/

> 교안 HTML에는 `noindex, nofollow`가 걸려 있어 검색엔진에는 노출되지 않습니다.
> 다만 저장소가 **Public**이므로 주소를 아는 사람은 누구나 열람할 수 있습니다.

## 구성

| 경로 | 내용 |
|---|---|
| `index.html` | 통합 교안 (커리큘럼 5회차 + 심화 · 실습 2종 · 모듈 A~D). 단일 파일, 외부 의존성 없음 |
| `.claude/skills/step-lesson-builder/` | 교안 제작 스킬 — 이 교안들과 같은 형식(단계 카드·번호 모형 화면·모바일·미리보기·배포)으로 새 교안을 만든다. 이 저장소로 시작한 Claude Code 세션에서 자동으로 쓸 수 있음 |
| `og_thumbnail.png` | 통합 교안 카카오톡·SNS 링크 미리보기 이미지(1200×630) — 원본 `assets/og/og_thumbnail.html`, 생성 `node assets/og/make_og.mjs` |
| `assets/patent-3person-review.svg` | 특허 3인 협의심사 제도 안내 인포그래픽 (벡터 원본) |
| `appscript/` | 회원서비스실 구글 시트 Apps Script 실습 교안 (1차 11/4, 2차 11/13) + 실습 코드·가상 데이터 |
| `claude-work/` | 회원서비스실 Claude 업무 실습 교안 (신고 처리·사례 DB·안내 이미지 틀) + 프로젝트 지침·프롬프트·가상 실습 자료 |
| `ethics-system/` | 윤리·징계·광고 업무지원 시스템 (FastAPI + SQLite + 웹 화면) |
| `assets/patent-3person-review.pdf` | 같은 인포그래픽의 벡터 PDF — 캔바 등 편집 도구 가져오기용 |

## GitHub Pages 켜기

1. 저장소 → **Settings** → 좌측 **Pages**
2. **Source** 를 `Deploy from a branch` 로 두고, Branch 를 `main` / `/ (root)` 로 지정 → **Save**
3. 1~2분 뒤 위 주소에서 열립니다

## 교안 사용법

- 상단 탭으로 **커리큘럼 / 실습 / 모듈** 세 묶음을 오갑니다
- 프롬프트 박스의 **복사** 버튼으로 실습용 프롬프트를 그대로 가져갈 수 있습니다
- 브라우저 인쇄(`Ctrl+P`)하면 전 회차가 페이지 단위로 나뉘어 출력됩니다

## 자료 갱신

```bash
git add .
git commit -m "교안 업데이트"
git push
```

푸시 후 1~2분이면 배포본에 반영됩니다.
