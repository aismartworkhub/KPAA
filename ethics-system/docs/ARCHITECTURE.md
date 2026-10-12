# 시스템 아키텍처 · 데이터베이스 · API

## 1. 구성
```
[브라우저 SPA (Vanilla JS, 빌드 불필요)]
        │ HTTPS (리버스 프록시) · 세션 쿠키 + CSRF 헤더
[FastAPI 앱 (uvicorn)] ── /api/*  REST
   ├─ routers/  auth · cases · evidence · knowledge · documents · meetings · admin
   ├─ services/ workflow(상태·기한) · ad_rules(광고 규칙) · reg_parser(조문 분해)
   │            search(2-gram TF-IDF) · matcher(조문·선례 매칭) · llm(근거 제한 AI)
   │            minutes(녹취 정리) · doc_templates(공문) · docx_export · mailer(SMTP)
   │            text_extract(HWP·HWPX·PDF·DOCX) · storage(업로드) · backup
   └─ SQLite (WAL) + data/uploads (첨부) + data/backups
        │ (선택) Anthropic Claude API — 키가 있을 때만
```

### 기술 선택 이유
| 선택 | 이유 |
|---|---|
| Python 3.11+ / FastAPI | HWP·PDF·DOCX 처리 라이브러리 풍부, 타입 검증(pydantic), 자동 API 문서(`/api/docs`) |
| SQLite (WAL) | 부서 단위 사용자(수 명~수십 명)에 충분, 설치·백업이 파일 복사 수준. 사용자 증가 시 `db.py`만 교체해 PostgreSQL 이전 가능(SQL 표준 위주 작성) |
| Vanilla JS ES Modules | 빌드 도구 없이 유지보수 가능, CSP `script-src 'self'` 적용, DOM은 textContent로만 생성(XSS 차단) |
| 형태소 분석기 없는 2-gram 검색 | 외부 서비스·대용량 사전 없이 한국어 조사·어미 변화에 강함 |
| AI는 선택 기능 | 키·네트워크가 없어도 업무 중단 없음. AI 응답은 반드시 서버 검증 통과분만 표시 |

## 2. AI 환각 방지 설계 (요청 분야 2)
1. 질의 시 시스템이 먼저 조문 DB·선례 DB에서 후보를 검색(검색 증강).
2. 모델에는 후보만 `[A12]`, `[P3]` 형태 ID로 제공하고 "제공 자료 밖 지식 금지, 근거 부족 시 insufficient=true" 지시.
3. 응답은 JSON 스키마(structured outputs)로 강제.
4. 서버 검증: 제공하지 않은 ID 인용 → 폐기 / 인용문이 조문 원문에 글자 그대로 없으면 → 폐기. 폐기 내역은 "근거 검증 실패"로 화면에 표시.
5. 회의록 요약·사례 추출도 같은 방식으로 근거 문장의 원문 존재 여부를 검증.

## 3. 데이터베이스 스키마 (요약 — 전체는 `backend/app/schema.sql`)
| 테이블 | 용도 | 주요 컬럼 |
|---|---|---|
| users / sessions | 계정·세션 | role(admin/staff/viewer), password_hash, failed_attempts, locked_until / token_hash, csrf_token, expires_at |
| audit_log | 감사 로그 | user_id, action, entity, entity_id, detail, ip |
| settings | 기한·담당자·결재선 | key, value |
| articles | 법령·회규 조문(근거의 유일한 출처) | source, source_name, chapter, article_no, title, body |
| cases | 사건 | case_no, case_type(AD/ETHICS), source, status, priority, 피민원인·민원인, facts, review_opinion, explanation_summary, violation_date, explanation_due, correction_due, objection_due |
| case_events | 처리 경과(추가만 가능) | case_id, ts, type(STATUS/MAIL/DOC/…), from_status, to_status, note |
| evidence | 채증 | case_id(NULL=미배정), url, office_name, ad_text, captured_at, stored_path, sha256 |
| ad_findings | 스크리닝 결과 | rule_code, article_refs(JSON), matched_text, confidence, decision |
| case_articles / case_precedents | 사건-조문·선례 연결 | reason / note |
| precedents | 징계 선례 | origin(KBA/KPAA), volume, case_ref, title, sanction_type, facts, holding, related_rules |
| source_documents / doc_chunks | 사례집·원문 파일과 검색 조각 | sha256(중복 차단), pages / page, seq, text |
| templates / documents | 공문 양식 / 공문 | status(DRAFT→APPROVED→SENT), approver_note, sent_via(SMTP/MANUAL), sent_ref |
| meetings / meeting_items | 위원회·안건 | committee, members(JSON), checklist(JSON), transcript, minutes, allowance_paid / decision, vote_for/against |

## 4. API 목록
전체 스펙: 실행 후 `http://서버/api/docs` (OpenAPI). 모든 변경 요청은 `X-CSRF-Token` 헤더 필요.

| 메서드 | 경로 | 분류 | 설명 |
|---|---|---|---|
| POST | `/api/auth/login` | auth | Login |
| POST | `/api/auth/logout` | auth | Logout |
| GET | `/api/auth/me` | auth | Me |
| POST | `/api/auth/password` | auth | Change Password |
| GET | `/api/users` | auth | List Users |
| POST | `/api/users` | auth | Create User |
| PATCH | `/api/users/{uid}` | auth | Update User |
| GET | `/api/meta` | cases | Meta |
| GET | `/api/dashboard` | cases | Dashboard |
| GET | `/api/cases` | cases | List Cases |
| POST | `/api/cases` | cases | Create Case |
| GET | `/api/cases/{cid}` | cases | Get Case |
| PATCH | `/api/cases/{cid}` | cases | Update Case |
| POST | `/api/cases/{cid}/transition` | cases | Transition |
| POST | `/api/cases/{cid}/notes` | cases | Add Note |
| POST | `/api/cases/{cid}/articles` | cases | Link Article |
| DELETE | `/api/cases/{cid}/articles/{aid}` | cases | Unlink Article |
| POST | `/api/cases/{cid}/precedents` | cases | Link Precedent |
| DELETE | `/api/cases/{cid}/precedents/{pid}` | cases | Unlink Precedent |
| PATCH | `/api/findings/{fid}` | cases | Decide Finding |
| POST | `/api/cases/{cid}/analyze` | cases | Analyze Case |
| POST | `/api/screen` | evidence | Screen |
| GET | `/api/screen/rules` | evidence | Rules |
| GET | `/api/monitoring/keywords` | evidence | Monitoring Keywords |
| POST | `/api/screen/batch` | evidence | 모니터링 결과 CSV 일괄 스크리닝. 열: url, office_name, ad_text (헤더 필수, UTF-8 또는 CP9 |
| POST | `/api/evidence` | evidence | Create Evidence |
| GET | `/api/evidence` | evidence | List Evidence |
| GET | `/api/evidence/{eid}` | evidence | Get Evidence |
| DELETE | `/api/evidence/{eid}` | evidence | Delete Evidence |
| GET | `/api/evidence/{eid}/file` | evidence | Evidence File |
| POST | `/api/evidence/{eid}/assign` | evidence | Assign Evidence |
| POST | `/api/evidence/{eid}/create-case` | evidence | Case From Evidence |
| GET | `/api/articles/sources` | knowledge | Article Sources |
| GET | `/api/articles` | knowledge | List Articles |
| GET | `/api/articles/{aid}` | knowledge | Get Article |
| PUT | `/api/articles/{aid}` | knowledge | Update Article |
| POST | `/api/articles/match` | knowledge | Match |
| POST | `/api/articles/import` | knowledge | 개정 법령·회규 원문 업로드(HWP/HWPX/DOCX/TXT/PDF). '< 규정명 >' 머리표가 없으면 source_name |
| GET | `/api/precedents` | knowledge | List Precedents |
| POST | `/api/precedents` | knowledge | Create Precedent |
| GET | `/api/precedents/facets` | knowledge | Precedent Facets |
| GET | `/api/precedents/{pid}` | knowledge | Get Precedent |
| PUT | `/api/precedents/{pid}` | knowledge | Update Precedent |
| DELETE | `/api/precedents/{pid}` | knowledge | Delete Precedent |
| POST | `/api/precedents/import-csv` | knowledge | Import Precedents Csv |
| POST | `/api/precedents/search` | knowledge | Search Precedents |
| GET | `/api/source-docs` | knowledge | List Docs |
| POST | `/api/source-docs` | knowledge | Upload Doc |
| DELETE | `/api/source-docs/{did}` | knowledge | Delete Doc |
| GET | `/api/source-docs/{did}/chunks` | knowledge | Doc Chunks |
| POST | `/api/source-docs/extract` | knowledge | 선택한 원문 조각에서 사례 후보 추출 → 담당자 검토 후 '선례 등록'. AI 미사용 시 규칙 기반 후보. |
| GET | `/api/templates` | documents | List Templates |
| PUT | `/api/templates/{code}` | documents | Update Template |
| POST | `/api/templates/{code}/reset` | documents | Reset Template |
| POST | `/api/documents/preview` | documents | Preview |
| GET | `/api/documents` | documents | List Documents |
| POST | `/api/documents` | documents | Create Document |
| GET | `/api/documents/{did}` | documents | Get Document |
| PUT | `/api/documents/{did}` | documents | Update Document |
| POST | `/api/documents/{did}/approve` | documents | Approve Document |
| POST | `/api/documents/{did}/send` | documents | Send Document |
| POST | `/api/documents/{did}/cancel` | documents | Cancel Document |
| GET | `/api/documents/{did}/docx` | documents | Document Docx |
| GET | `/api/meetings` | meetings | List Meetings |
| POST | `/api/meetings` | meetings | Create Meeting |
| GET | `/api/meetings/{mid}` | meetings | Get Meeting |
| PATCH | `/api/meetings/{mid}` | meetings | Update Meeting |
| POST | `/api/meetings/{mid}/items` | meetings | Add Item |
| PATCH | `/api/meetings/items/{iid}` | meetings | Update Item |
| DELETE | `/api/meetings/items/{iid}` | meetings | Delete Item |
| GET | `/api/meetings/{mid}/agenda` | meetings | Agenda |
| GET | `/api/meetings/{mid}/agenda.docx` | meetings | Agenda Docx |
| POST | `/api/meetings/{mid}/summarize` | meetings | Summarize |
| POST | `/api/meetings/{mid}/apply-decisions` | meetings | 의결 결과를 사건 상태에 반영(위원회 상정 상태인 사건만). |
| GET | `/api/meetings/{mid}/minutes.docx` | meetings | Minutes Docx |
| GET | `/api/admin/status` | admin | Status |
| GET | `/api/admin/settings` | admin | Get Settings |
| PUT | `/api/admin/settings` | admin | Put Settings |
| GET | `/api/admin/backups` | admin | List Backups |
| POST | `/api/admin/backups` | admin | Create Backup |
| GET | `/api/admin/backups/{name}` | admin | Download Backup |
| GET | `/api/admin/audit` | admin | Audit Log |
| GET | `/api/health` |  | Health |
