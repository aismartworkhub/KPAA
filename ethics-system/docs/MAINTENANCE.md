# 유지보수·확장 계획

## 코드 위치 안내
| 바꾸고 싶은 것 | 파일 |
|---|---|
| 광고 위반 의심 표현 규칙 추가 | `backend/app/services/ad_rules.py` (+ `tests/test_rules_and_parsing.py`에 사례 추가) |
| 처리 단계·기한·경보 | `backend/app/services/workflow.py` |
| 공문 기본 양식 | `backend/app/services/doc_templates.py` (운영 중 수정은 관리 > 공문 양식) |
| AI 지시문·검증 | `backend/app/services/llm.py` |
| 화면 | `frontend/js/views/*.js`, 스타일 `frontend/styles.css` |
| DB 구조 | `backend/app/schema.sql` (컬럼 추가 시 `ALTER TABLE` 마이그레이션을 `db.init_db`에 추가하고 `SCHEMA_VERSION` 증가) |

## 테스트
```bash
cd ethics-system/backend && python -m pytest -q          # 37개 단위·통합 테스트
# 화면 E2E (Playwright 필요): 서버를 --demo 데이터·KPAA_ADMIN_PASSWORD='Admin!2345pw'로 실행한 뒤
node ../tests_e2e/ui_flow.mjs ./shots
```

## 운영 점검(월 1회 권장)
- 관리 > 감사 로그: 비정상 다운로드·삭제 확인
- 백업 파일 외부 복사 여부, 복구 리허설(분기 1회)
- 규정 개정 반영 여부(조문 최종 반영일 표시 확인)
- 스크리닝 오탐 사례 수집 → 규칙 보완

## 향후 확장(우선순위 순)
1. **변리사 등록 정보 연동**: 회원 DB와 연결해 미등록·비회원 자동 판별, 사무소 대표메일 자동 기입
2. **그룹웨어 전자결재·메일 연동**: 결재 완료·발송 이력 자동 수신
3. **캡처 이미지 OCR**: 채증 이미지에서 광고 문구 자동 추출 → 즉시 스크리닝
4. **모니터링 반자동화**: 공식 검색 API(네이버 검색 API 등) 키를 받아 정기 검색 결과를 채증함으로 수집(약관 범위 내)
5. **통계 리포트**: 연도별 위반 유형·처분 현황, 위원회 보고용 자동 집계
6. **PostgreSQL 전환**: 동시 사용자 증가 시 `db.py` 교체
7. **SSO**: 사내 계정(LDAP/AD) 연동
