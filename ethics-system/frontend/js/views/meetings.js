import { api } from '../api.js';
import { h, mount, badge, empty, field, input, select, toast, modal, fmtDT } from '../ui.js';
import { canEdit, COMMITTEES } from '../state.js';

const MST = { PLANNED: '예정', HELD: '개최', MINUTES_DRAFT: '회의록 작성 중', APPROVED: '회의록 승인', CANCELLED: '취소' };

export default async function meetings(view) {
  const list = await api.get('/api/meetings');
  mount(view,
    h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, '위원회 회의'), h('p', {}, '광고심사·윤리·징계위원회 및 상임이사회 안건 관리, 회의자료·회의록 작성')),
      canEdit() ? h('button', { class: 'primary', onclick: createDialog }, '+ 회의 등록') : null),
    h('div', { class: 'panel', style: 'padding:0;overflow-x:auto' }, list.length ? h('table', {},
      h('thead', {}, h('tr', {}, ...['위원회', '회의명', '일시', '장소', '안건', '상태', '수당'].map(t => h('th', {}, t)))),
      h('tbody', {}, ...list.map(m => h('tr', { class: 'clickable', onclick: () => location.hash = `#/meetings/${m.id}` },
        h('td', {}, badge(m.committee_label)), h('td', {}, m.title), h('td', { class: 'nowrap' }, fmtDT(m.scheduled_at)), h('td', {}, m.location || '-'),
        h('td', {}, m.item_count), h('td', {}, badge(MST[m.status], m.status === 'APPROVED' ? 'ok' : '')), h('td', {}, m.allowance_paid ? '지급' : '-')))))
      : empty('등록된 회의가 없습니다.')));
}

function createDialog() {
  const committee = select('committee', Object.entries(COMMITTEES), 'AD_REVIEW');
  const title = input('title', '', { placeholder: '예: 2026년 제3차 광고심사위원회' });
  const at = input('scheduled_at', '', { type: 'datetime-local' });
  const loc = input('location', '본회 회관 회의실');
  const members = h('textarea', { rows: 5, placeholder: '위원 명단 (한 줄에 한 명, "이름, 직위")\n예) 홍길동, 위원장' });
  modal('회의 등록', h('div', { class: 'form-grid' }, field('위원회', committee), field('회의명 *', title), field('일시', at), field('장소', loc), field('위원 명단', members, 'full')),
    { actions: [{ label: '등록', primary: true, onClick: async () => {
      if (!title.value.trim()) throw new Error('회의명을 입력하세요.');
      const mem = members.value.split('\n').map(s => s.trim()).filter(Boolean).map(s => { const [name, role] = s.split(',').map(x => x.trim()); return { name, role: role || '위원', attend: null }; });
      const r = await api.post('/api/meetings', { committee: committee.value, title: title.value.trim(), scheduled_at: at.value ? at.value.replace('T', ' ') : null, location: loc.value || null, members: mem });
      toast('회의를 등록했습니다.'); location.hash = `#/meetings/${r.id}`;
    } }] });
}
