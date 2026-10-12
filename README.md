# KPAA — 정책홍보실 AX 교육 자료

대한변리사회 정책홍보실 **AI 업무혁신(AX) 교육** 통합 교안과 부속 자료를 배포하는 저장소입니다.

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
| `assets/patent-3person-review.svg` | 특허 3인 협의심사 제도 안내 인포그래픽 (벡터 원본) |
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
