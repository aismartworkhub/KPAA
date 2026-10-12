import { api } from '../api.js';
import { h, mount, badge, empty, field, input, select, textarea, toast, modal, formData, fmtDT, bytes, tabs } from '../ui.js';
import { state, isAdmin } from '../state.js';

let tab = 'status';
const SETTINGS = [
  ['org_name', '기관명'], ['dept_name', '부서명'], ['ad_case_owner', '광고 담당자(공문 문의처)'], ['ethics_case_owner', '윤리·징계 담당자(공문 문의처)'],
  ['contact_phone', '담당 전화번호'], ['contact_email', '담당 메일'], ['approval_line', '결재선 (예: 차장 OOO 실장 OOO 사무총장 OOO 이사 OOO)'], ['cooperation_line', '협조자'],
  ['explanation_days', '소명 기한(일)'], ['correction_days', '시정 기한 기본값(일)'], ['discipline_after_days', '시정 기한 경과 후 징계발의 가능(일)'],
  ['objection_days', '이의신청 기간(일)'], ['limitation_years', '징계시효(년)'], ['doc_no_prefix', '시행번호 접두어'],
];

export default async function admin(view) {
  const body = h('div');
  const reload = () => admin(view);
  const defs = [['status', '시스템 상태'], ['settings', '기본 설정']];
  if (isAdmin()) defs.push(['users', '사용자'], ['templates', '공문 양식'], ['backup', '백업'], ['audit', '감사 로그']);
  if (!defs.find(d => d[0] === tab)) tab = 'status';
  const setTab = async (t) => { tab = t; await render(); };
  async function render() {
    const c = await ({ status, settings, users, templates, backup, audit })[tab](reload);
    mount(body, tabs(defs, setTab, tab), c);
  }
  await render();
  mount(view, h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, '관리'), h('p', {}, '설정·사용자·공문 양식·백업·감사 로그'))), body);
}

async function status() {
  const s = await api.get('/api/admin/status');
  const labels = { cases: '사건', evidence: '채증 자료', articles: '조문', precedents: '선례', source_documents: '원문 문서', doc_chunks: '원문 색인 조각', documents: '공문', meetings: '회의', users: '사용자' };
  return h('div', {},
    h('div', { class: 'panel' }, h('h2', {}, `버전 ${s.version}`),
      h('div', { class: s.ai_available ? 'alert ok' : 'alert warn' }, s.ai_available ? `AI 보조 사용 가능 — 모델 ${s.ai_model} (근거 제한 모드)` : 'AI 보조 미설정 — ANTHROPIC_API_KEY 환경변수를 설정하면 근거 제한 AI 분석·녹취 요약·사례 추출이 활성화됩니다. 미설정 상태에서도 규칙·검색 기반 기능은 모두 동작합니다.'),
      h('div', { class: s.smtp_configured ? 'alert ok' : 'alert info' }, s.smtp_configured ? '메일 발송(SMTP) 설정됨 — 공문을 시스템에서 직접 발송하고 Message-ID를 근거로 기록합니다.' : '메일 발송(SMTP) 미설정 — 그룹웨어로 발송 후 [발송 기록]에 근거를 입력하는 방식으로 동작합니다.'),
      s.db_path ? h('div', { class: 'small muted' }, `DB: ${s.db_path}`) : null),
    h('div', { class: 'grid g4' }, ...Object.entries(s.counts).map(([k, v]) => h('div', { class: 'panel kpi' }, h('div', { class: 'v' }, v), h('div', { class: 'l' }, labels[k] || k)))));
}

async function settings(reload) {
  const s = await api.get('/api/admin/settings');
  const f = h('div', { class: 'form-grid' }, ...SETTINGS.map(([k, l]) => field(l, input(k, s[k] || '', { disabled: !isAdmin() }), k === 'approval_line' ? 'full' : '')));
  return h('div', { class: 'panel' }, h('p', { class: 'small muted' }, '공문 자동 작성 시 문의처·결재선·기한 계산에 사용됩니다.'), f,
    isAdmin() ? h('button', { class: 'primary', style: 'margin-top:12px', onclick: async () => {
      const d = formData(f); const values = {};
      Object.entries(d).forEach(([k, v]) => { values[k] = v ?? ''; });
      await api.put('/api/admin/settings', { values }); toast('설정을 저장했습니다.'); window.dispatchEvent(new Event('meta-changed')); reload();
    } }, '저장') : null);
}

async function users(reload) {
  const list = await api.get('/api/users');
  const ROLE = { admin: '관리자', staff: '담당자', viewer: '조회 전용' };
  return h('div', { class: 'panel' },
    h('div', { class: 'row' }, h('h2', { style: 'margin:0' }, '사용자'), h('span', { class: 'spacer' }), h('button', { class: 'primary', onclick: () => userDialog(null, reload) }, '+ 사용자 추가')),
    h('table', {}, h('thead', {}, h('tr', {}, ...['아이디', '이름', '권한', '메일', '상태', '최근 로그인', ''].map(t => h('th', {}, t)))),
      h('tbody', {}, ...list.map(u => h('tr', {}, h('td', {}, u.username), h('td', {}, u.name), h('td', {}, ROLE[u.role]), h('td', {}, u.email || '-'),
        h('td', {}, u.active ? badge('사용', 'ok') : badge('중지')), h('td', {}, fmtDT(u.last_login_at)),
        h('td', {}, h('button', { class: 'small', onclick: () => userDialog(u, reload) }, '수정')))))));
}

function userDialog(u, done) {
  const f = h('div', { class: 'form-grid' },
    u ? null : field('아이디', input('username')),
    field('이름', input('name', u?.name)), field('권한', select('role', [['staff', '담당자'], ['admin', '관리자'], ['viewer', '조회 전용']], u?.role || 'staff')),
    field('메일', input('email', u?.email)),
    u ? field('상태', select('active', [['true', '사용'], ['false', '중지']], u.active ? 'true' : 'false')) : null,
    field(u ? '비밀번호 재설정 (변경 시에만 입력)' : '초기 비밀번호', input(u ? 'reset_password' : 'password', '', { type: 'password', autocomplete: 'new-password' })));
  modal(u ? '사용자 수정' : '사용자 추가', h('div', {}, f, h('p', { class: 'small muted' }, '초기/재설정 비밀번호로 로그인하면 비밀번호 변경이 요구됩니다.')),
    { actions: [{ label: '저장', primary: true, onClick: async () => {
      const d = formData(f);
      if (u) { d.active = d.active === 'true'; if (!d.reset_password) delete d.reset_password; await api.patch(`/api/users/${u.id}`, d); }
      else await api.post('/api/users', d);
      toast('저장했습니다.'); window.dispatchEvent(new Event('meta-changed')); done();
    } }] });
}

async function templates(reload) {
  const list = await api.get('/api/templates');
  return h('div', { class: 'panel' }, h('h2', {}, '공문 양식'),
    h('p', { class: 'small muted' }, '{{변수}} 자리에 사건 정보가 자동으로 채워집니다. 값이 없으면 {{확인 필요: 항목}}으로 표시되어 결재 전 반드시 보완하도록 합니다.'),
    h('table', {}, h('tbody', {}, ...list.map(t => h('tr', {}, h('td', {}, h('b', {}, t.name), h('div', { class: 'small muted' }, t.code)), h('td', { class: 'small' }, t.subject),
      h('td', { class: 'nowrap' }, h('button', { class: 'small', onclick: () => templateDialog(t, reload) }, '편집'), ' ',
        h('button', { class: 'small', onclick: async () => { if (confirm('기본 양식으로 되돌릴까요?')) { await api.post(`/api/templates/${t.code}/reset`); toast('되돌렸습니다.'); reload(); } } }, '기본값')))))));
}

function templateDialog(t, done) {
  const name = input('name', t.name); const subject = input('subject', t.subject); const body = textarea('body', t.body, { rows: 26, class: 'mono' });
  modal(`양식 편집 — ${t.name}`, h('div', {}, field('양식명', name), field('제목', subject), field('본문', body)), { wide: true, actions: [{ label: '저장', primary: true, onClick: async () => {
    await api.put(`/api/templates/${t.code}`, { name: name.value, subject: subject.value, body: body.value }); toast('저장했습니다.'); done();
  } }] });
}

async function backup(reload) {
  const list = await api.get('/api/admin/backups');
  return h('div', { class: 'panel' }, h('div', { class: 'row' }, h('h2', { style: 'margin:0' }, '백업'), h('span', { class: 'spacer' }),
    h('button', { class: 'primary', onclick: async (e) => { const btn = e.currentTarget; btn.disabled = true; try { const r = await api.post('/api/admin/backups'); toast(`백업 생성: ${r.db}`); reload(); } catch (err) { toast(err.message, true); btn.disabled = false; } } }, '지금 백업')),
    h('p', { class: 'small muted' }, 'DB는 운영 중에도 일관성이 보장되는 온라인 백업으로, 첨부파일은 tar.gz로 보관합니다. 매일 자동 백업은 설치 가이드의 cron 설정을 참고하세요. 백업 파일은 외부 저장소(NAS 등)에 주기적으로 복사하세요.'),
    list.length ? h('table', {}, h('thead', {}, h('tr', {}, ...['파일', '크기', '생성', ''].map(x => h('th', {}, x)))),
      h('tbody', {}, ...list.map(b => h('tr', {}, h('td', {}, b.name), h('td', {}, bytes(b.size)), h('td', {}, b.created),
        h('td', {}, h('button', { class: 'small', onclick: () => api.download(`/api/admin/backups/${encodeURIComponent(b.name)}`, b.name) }, '내려받기'))))))
      : empty('백업이 없습니다.'));
}

async function audit() {
  const list = await api.get('/api/admin/audit?limit=300');
  return h('div', { class: 'panel', style: 'overflow-x:auto' }, h('h2', {}, '감사 로그 (최근 300건)'),
    h('table', {}, h('thead', {}, h('tr', {}, ...['일시', '사용자', '작업', '대상', 'IP', '상세'].map(x => h('th', {}, x)))),
      h('tbody', {}, ...list.map(a => h('tr', {}, h('td', { class: 'nowrap' }, a.ts), h('td', {}, a.user_name || '-'), h('td', {}, a.action),
        h('td', {}, `${a.entity || ''} ${a.entity_id || ''}`), h('td', {}, a.ip || '-'), h('td', { class: 'small' }, (a.detail || '').slice(0, 200)))))));
}
