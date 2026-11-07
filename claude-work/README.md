# 회원서비스실 Claude 업무 실습 교안 (변리사법 위반 신고 처리 + 회원 안내 이미지 틀)

회의(AI 도입과 업무 처리 방식 개선 / AI 활용 회원 관리와 개인정보 보안) 내용을 바탕으로 만든 단계별 따라 하기 교안입니다.
회원 추천·연수·공익·회비 현황은 `appscript/` 교안에서 다룹니다.

| 회차 | 일시(예정) | 탭 |
|---|---|---|
| 1차 | 11. 13.(금) 15:00~17:00 | 0 준비 · 1 프로젝트 · 2 신고 검토 · 3 보고·공문 |
| 2차 | 11. 27.(금) 15:00~17:00 | 4 사례 DB · 5 비교·사례 · 6 진행경과 |
| 3차 | 12월 중(협의) | 7 이미지 틀 · 8 AI 활용 · 복습 |

## 구성
| 경로 | 내용 |
|---|---|
| `index.html` | 교안(빌드 결과물 — `src/` 수정 후 다시 빌드) |
| `code/프로젝트_지침_신고검토.txt` | Claude 프로젝트 지침(근거 인용·없으면 없다·[추정]·원문 워딩·보안) |
| `code/프롬프트_모음.txt` | 교안의 모든 프롬프트(src/prompts.py에서 자동 생성) |
| `practice/` | **가상** 실습 파일 9종(법령 발췌, 가상 신고서·소명서, 사례 DB·사건관리 시트, 가상 메일, 안내 이미지 틀, 가상 사례집 PDF) |
| `shots/` | 실제 화면 캡처를 `<그림ID>.png`로 넣으면 모형 대신 보임 |
| `src/` | build.py · prompts.py · mocks_claude.py · make_practice.py · make_pdf.mjs · og.html |

## 다시 만들기
```bash
python3 claude-work/src/make_practice.py   # 실습 파일(가상)
node claude-work/src/make_pdf.mjs          # 가상 사례집 PDF
python3 claude-work/src/build.py           # 교안 + 프롬프트 모음
```
배포 주소(Pages): https://aismartworkhub.github.io/KPAA/claude-work/

## 개인정보
실습 자료의 사람·사무소·연락처·사건·사례는 모두 가상입니다. 법령·규정 발췌는 `ethics-system/backend/seed/regulations.txt`의 원문에서 조항만 잘라 왔습니다.
