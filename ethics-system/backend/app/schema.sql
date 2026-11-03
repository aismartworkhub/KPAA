-- KPAA 윤리·징계·광고 업무지원 시스템 스키마 (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);

CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('admin','staff','viewer')),
    email           TEXT,
    password_hash   TEXT NOT NULL,
    must_change_pw  INTEGER NOT NULL DEFAULT 0,
    active          INTEGER NOT NULL DEFAULT 1,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    TEXT,
    last_login_at   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    expires_at  TEXT NOT NULL,
    ip          TEXT,
    user_agent  TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY,
    ts        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    user_id   INTEGER REFERENCES users(id),
    action    TEXT NOT NULL,
    entity    TEXT,
    entity_id TEXT,
    detail    TEXT,
    ip        TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 법령·회규 조문 (근거 매칭의 유일한 근거 출처)
CREATE TABLE IF NOT EXISTS articles (
    id          INTEGER PRIMARY KEY,
    source      TEXT NOT NULL,      -- PAA / ETHICS / ETHICS_COMMITTEE / DISCIPLINE_COMMITTEE / AD_REG / CUSTOM...
    source_name TEXT NOT NULL,
    chapter     TEXT,
    article_no  TEXT NOT NULL,      -- 예: 제8조의5, 부칙(2023. 5. 19.) 제1조
    title       TEXT,
    body        TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE (source, article_no)
);

-- 업로드 원문 (징계사례집 PDF/HWP 등)
CREATE TABLE IF NOT EXISTS source_documents (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL CHECK (kind IN ('precedent_book','regulation','meeting','other')),
    title       TEXT NOT NULL,
    filename    TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    size        INTEGER NOT NULL,
    pages       INTEGER,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS doc_chunks (
    id          INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    page        INTEGER,
    seq         INTEGER NOT NULL,
    text        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON doc_chunks(document_id);

-- 징계 선례 (변호사 징계사례집, 본회 광고위반 사례 등)
CREATE TABLE IF NOT EXISTS precedents (
    id              INTEGER PRIMARY KEY,
    origin          TEXT NOT NULL DEFAULT 'KBA',   -- KBA(변호사 징계사례집) / KPAA(본회) / OTHER
    volume          TEXT,                          -- 집 (예: 제8집)
    case_ref        TEXT,                          -- 사건번호
    title           TEXT NOT NULL,
    decided_on      TEXT,
    category        TEXT,                          -- 광고 / 수임 / 품위 / 비밀유지 ...
    sanction_type   TEXT,                          -- 견책 / 과태료 / 정직 / 제명 / 영구제명 / 경고 / 시정요구 / 기타
    sanction_detail TEXT,
    facts           TEXT,
    holding         TEXT,                          -- 결정 요지
    related_rules   TEXT,
    keywords        TEXT,
    source_document_id INTEGER REFERENCES source_documents(id) ON DELETE SET NULL,
    source_page     INTEGER,
    created_by      INTEGER REFERENCES users(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 사건 (민원·모니터링 공통)
CREATE TABLE IF NOT EXISTS cases (
    id                  INTEGER PRIMARY KEY,
    case_no             TEXT NOT NULL UNIQUE,
    case_type           TEXT NOT NULL CHECK (case_type IN ('AD','ETHICS')),
    source              TEXT NOT NULL CHECK (source IN ('MONITORING','HOMEPAGE','PHONE','EMAIL','OTHER')),
    title               TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'RECEIVED',
    priority            TEXT NOT NULL DEFAULT 'NORMAL' CHECK (priority IN ('NORMAL','SERIOUS')),
    respondent_office   TEXT,
    respondent_name     TEXT,
    respondent_reg_no   TEXT,
    respondent_email    TEXT,
    respondent_is_member INTEGER NOT NULL DEFAULT 1,   -- 0: 미등록·비회원 (자체 처분 불가)
    complainant_name    TEXT,
    complainant_contact TEXT,
    facts               TEXT,
    review_opinion      TEXT,
    explanation_summary TEXT,
    violation_date      TEXT,
    received_at         TEXT NOT NULL,
    assignee_id         INTEGER REFERENCES users(id),
    explanation_due     TEXT,
    correction_due      TEXT,
    objection_due       TEXT,
    closed_reason       TEXT,
    created_by          INTEGER REFERENCES users(id),
    created_at          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);

CREATE TABLE IF NOT EXISTS case_events (
    id          INTEGER PRIMARY KEY,
    case_id     INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    ts          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    user_id     INTEGER REFERENCES users(id),
    type        TEXT NOT NULL,      -- CREATED / STATUS / NOTE / DOC / MAIL / EVIDENCE / FINDING / ARTICLE
    from_status TEXT,
    to_status   TEXT,
    note        TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_case ON case_events(case_id);

-- 채증 자료
CREATE TABLE IF NOT EXISTS evidence (
    id          INTEGER PRIMARY KEY,
    case_id     INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    url         TEXT,
    office_name TEXT,
    ad_text     TEXT,
    captured_at TEXT NOT NULL,
    file_name   TEXT,
    stored_path TEXT,
    mime        TEXT,
    size        INTEGER,
    sha256      TEXT,
    note        TEXT,
    created_by  INTEGER REFERENCES users(id),
    created_at  TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_evidence_case ON evidence(case_id);

-- 광고 1차 스크리닝 결과
CREATE TABLE IF NOT EXISTS ad_findings (
    id           INTEGER PRIMARY KEY,
    case_id      INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    evidence_id  INTEGER REFERENCES evidence(id) ON DELETE CASCADE,
    rule_code    TEXT NOT NULL,
    rule_label   TEXT NOT NULL,
    article_refs TEXT NOT NULL,     -- JSON 배열 [ "AD_REG|제7조", ... ]
    matched_text TEXT NOT NULL,
    context      TEXT,
    confidence   TEXT NOT NULL,     -- HIGH / MEDIUM / LOW
    decision     TEXT,              -- NULL(미검토) / CONFIRMED / REJECTED
    created_at   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 사건에 적용된 조문
CREATE TABLE IF NOT EXISTS case_articles (
    case_id    INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    reason     TEXT,
    added_by   INTEGER REFERENCES users(id),
    added_at   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (case_id, article_id)
);

CREATE TABLE IF NOT EXISTS case_precedents (
    case_id      INTEGER NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    precedent_id INTEGER NOT NULL REFERENCES precedents(id) ON DELETE CASCADE,
    note         TEXT,
    PRIMARY KEY (case_id, precedent_id)
);

-- 공문 양식
CREATE TABLE IF NOT EXISTS templates (
    code       TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    category   TEXT NOT NULL,       -- CASE / MEETING
    subject    TEXT NOT NULL,
    body       TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 공문 (작성 → 결재 → 발송 기록)
CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY,
    case_id       INTEGER REFERENCES cases(id) ON DELETE CASCADE,
    meeting_id    INTEGER REFERENCES meetings(id) ON DELETE CASCADE,
    template_code TEXT,
    doc_no        TEXT,
    subject       TEXT NOT NULL,
    recipient     TEXT,
    recipient_email TEXT,
    body          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT','APPROVED','SENT','CANCELLED')),
    approver_note TEXT,
    approved_by   INTEGER REFERENCES users(id),
    approved_at   TEXT,
    sent_at       TEXT,
    sent_via      TEXT,
    sent_ref      TEXT,             -- 메일 Message-ID / 발송 메모 (근거기록)
    created_by    INTEGER REFERENCES users(id),
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 위원회 회의
CREATE TABLE IF NOT EXISTS meetings (
    id             INTEGER PRIMARY KEY,
    committee      TEXT NOT NULL CHECK (committee IN ('AD_REVIEW','ETHICS','DISCIPLINE','STANDING_BOARD')),
    title          TEXT NOT NULL,
    scheduled_at   TEXT,
    location       TEXT,
    status         TEXT NOT NULL DEFAULT 'PLANNED' CHECK (status IN ('PLANNED','HELD','MINUTES_DRAFT','APPROVED','CANCELLED')),
    members        TEXT,            -- JSON [{name, role, attend: null|true|false}]
    checklist      TEXT,            -- JSON {item: bool}
    transcript     TEXT,
    minutes        TEXT,
    approved_at    TEXT,
    allowance_paid INTEGER NOT NULL DEFAULT 0,
    created_by     INTEGER REFERENCES users(id),
    created_at     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS meeting_items (
    id            INTEGER PRIMARY KEY,
    meeting_id    INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    case_id       INTEGER REFERENCES cases(id) ON DELETE SET NULL,
    seq           INTEGER NOT NULL,
    title         TEXT NOT NULL,
    decision      TEXT NOT NULL DEFAULT 'PENDING',  -- PENDING/CORRECTION/WARNING/DISCIPLINE_REFERRAL/DISMISS/DEFER/EXTERNAL
    decision_note TEXT,
    vote_for      INTEGER,
    vote_against  INTEGER
);
