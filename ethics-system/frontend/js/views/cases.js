import { api, qs } from '../api.js';
import { h, mount, badge, fmtDate, empty, modal, field, input, select, textarea, formData, toast } from '../ui.js';
import { state, canEdit } from '../state.js';

function params() {
  const q = location.hash.split('?')[1] || '';
  return Object.fromEntries(new URLSearchParams(q));
}

export function newCaseDialog(prefill = {}) {
  const m = state.meta;
  const body = h('div', { class: 'form-grid' },
    field('사건 유형', select('case_type', Object.entries(m.case_types), prefill.case_type || 'AD')),
    field('접수 경로', select('source', Object.entries(m.sources), prefill.source || 'HOMEPAGE')),
    field('제목 *', input('title', prefill.title || '', { placeholder: '예: ○○특허 블로그 광고 최상급 표현 민원' }), 'full'),
    field('피민원 사무소명', input('respondent_office')),
    field('변리사 성명', input('respondent_name')),
    field('등록번호', input('respondent_reg_no')),
    field('사무소 대표 메일', input('respondent_email', '', { type: 'email' })),
    field('회원 여부', select('respondent_is_member', [['true', '등록 회원'], ['false', '미등록·비회원(자체 처분 곤란)']], 'true')),
    field('중요도', select('priority', [['NORMAL', '일반'], ['SERIOUS', '중대(회장 결재)']], 'NORMAL')),
    field('민원인 성명', input('complainant_name')),
    field('민원인 연락처(메일)', input('complainant_contact')),
    field('위반(광고 게재) 일자', input('violation_date', '', { type: 'date' })),
    field('접수일', input('received_at', new Date().toISOString().slice(0, 10), { type: 'date' })),
    field('사실관계', textarea('facts', prefill.facts || '', { rows: 5, placeholder: '누가, 언제, 어디에(URL), 어떤 표현/행위를 했는지 사실 위주로 기재' }), 'full'));
  modal('민원·사건 접수', body, { actions: [{ label: '접수', primary: true, onClick: async () => {
    const d = formData(body);
    if (!d.title) throw new Error('제목을 입력하세요.');
    d.respondent_is_member = d.respondent_is_member !== 'false';
    const r = await api.post('/api/cases', d);
    toast(`${r.case_no} 접수되었습니다.`);
    location.hash = `#/cases/${r.id}`;
  } }] });
}

export default async function cases(view) {
  const p = params();
  const m = state.meta;
  const filters = h('div', { class: 'row' },
    select('case_type', [['', '전체 유형'], ...Object.entries(m.case_types)], p.case_type, { style: 'width:120px' }),
    select('status', [['', '전체 단계'], ...Object.entries(m.statuses)], p.status, { style: 'width:150px' }),
    select('assignee_id', [['', '전체 담당자'], ...m.users.map(u => [u.id, u.name])], p.assignee_id, { style: 'width:140px' }),
    input('q', p.q || '', { placeholder: '사건번호·제목·사무소·사실관계 검색', style: 'width:280px' }),
    h('button', { onclick: () => {
      const d = formData(filters);
      location.hash = '#/cases' + qs(d);
    } }, '검색'));
  filters.querySelector('input[name=q]').addEventListener('keydown', (e) => { if (e.key === 'Enter') filters.querySelector('button').click(); });
  const data = await api.get('/api/cases' + qs({ status: p.status, case_type: p.case_type, q: p.q, assignee_id: p.assignee_id, size: 200 }));
  const table = data.items.length ? h('table', {},
    h('thead', {}, h('tr', {}, ...['사건번호', '유형', '제목', '피민원인', '단계', '담당', '접수일', '경보'].map(t => h('th', {}, t)))),
    h('tbody', {}, ...data.items.map(c => h('tr', { class: 'clickable', onclick: () => location.hash = `#/cases/${c.id}` },
      h('td', { class: 'nowrap' }, c.case_no),
      h('td', {}, badge(c.type_label, c.case_type)),
      h('td', {}, c.title, c.priority === 'SERIOUS' ? [' ', badge('중대', 'SERIOUS')] : null),
      h('td', {}, c.respondent_office || '-', c.respondent_name ? ` / ${c.respondent_name}` : ''),
      h('td', { class: 'nowrap st' }, c.status_label),
      h('td', { class: 'nowrap' }, c.assignee_name || '-'),
      h('td', { class: 'nowrap' }, fmtDate(c.received_at)),
      h('td', {}, ...c.alerts.map(a => h('div', {}, badge(a.text, a.level)))))))) : empty('조건에 맞는 사건이 없습니다.');
  mount(view,
    h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, '사건 관리'), h('p', {}, `민원 접수 → 검토 → 소명 → 위원회 심의 → 종결 (총 ${data.total}건)`)),
      canEdit() ? h('button', { class: 'primary', onclick: () => newCaseDialog() }, '+ 민원·사건 접수') : null),
    h('div', { class: 'panel' }, filters),
    h('div', { class: 'panel', style: 'padding:0;overflow-x:auto' }, table));
  if (p.new && canEdit()) newCaseDialog();
}
