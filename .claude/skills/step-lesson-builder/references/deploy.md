# 배포와 공유 링크 (GitHub Pages 기준)

## 기본 흐름
1. 교안 폴더(예: `<저장소>/<교안이름>/`)에 `index.html`, `og_image.jpg`, `code/`, `practice/`, `shots/`, `src/`를 둔다.
   저장소가 Public이면 **실제 개인정보·내부 자료를 절대 넣지 않는다**(가상 실습 데이터만).
2. 작업 브랜치에 커밋·푸시 → PR 생성 → main에 병합. (사용자가 "링크까지 완성"을 원하면 병합까지 진행하고,
   그렇지 않으면 PR까지만 만들고 병합 여부를 묻는다.) 이미 병합된 브랜치에 이어서 작업할 때는 최신 main에서 브랜치를 다시 시작한다.
3. Pages 배포 확인: GitHub Actions의 `pages build and deployment` 실행이 병합 커밋 SHA로 `success`인지 확인(보통 1분 내외).
   Pages가 꺼져 있으면 사용자에게: 저장소 Settings → Pages → Source `Deploy from a branch`, Branch `main` / `/ (root)`.
4. 링크: `https://<계정>.github.io/<저장소>/<교안이름>/`

## 미리보기(카카오톡·SNS)
- `build(..., site_url="https://<계정>.github.io/<저장소>/<교안이름>/", og_image="og_image.jpg")` → og:title/description/image/url 자동.
- 이미지 1200×630, JPG 100KB 안팎 권장. 이미지 주소는 절대경로여야 카카오톡이 읽는다.
- 카카오톡은 처음 가져간 미리보기를 캐시한다. 바뀐 이미지가 안 보이면
  카카오 공유 디버거(https://developers.kakao.com/tool/debugger/sharing)에서 주소 입력 → 캐시 초기화 안내.
- 저장소의 다른 페이지가 og:image로 없는 파일을 가리키고 있지 않은지도 확인한다(이미지 없는 미리보기 원인).

## 접속 확인
- 작업 환경에서 github.io 접속이 막혀 있으면 배포 성공(Actions)과 main의 파일·메타 태그까지만 확인했다고 **정직하게** 알리고,
  사용자에게 PC·휴대폰에서 직접 열어 보고 본인 카톡방에 먼저 보내 미리보기를 확인하라고 안내한다.

## GitHub 이외
- 사내 서버: 교안 폴더를 그대로 정적 파일로 올리면 된다(서버 코드 불필요).
- 파일로 전달: 폴더를 zip으로 묶어 보내고 "압축 풀고 index.html을 크롬으로 열기" 안내(그래야 실습 파일 내려받기 링크가 동작).
