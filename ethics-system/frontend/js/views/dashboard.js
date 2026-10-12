import { api } from '../api.js';
import { h, mount, badge, fmtDT, empty } from '../ui.js';
import { COMMITTEES } from '../state.js';

export default async function dashboard(view) {
  const d = await api.get('/api/dashboard');
  const kpi = (label, value, href, cls = '') => h('a', { href, class: 'panel kpi', style: 'display:block;color:inherit;text-decoration:none' },
    h('div', { class: 'v ' + cls }, value), h('div', { class: 'l' }, label));
  const danger = d.alerts.filter(a => a.level === 'danger').length;
  const order = ['RECEIVED', 'REVIEW', 'PENDING_APPROVAL', 'EXPLANATION_REQUESTED', 'EXPLANATION_REVIEW', 'COMMITTEE', 'CORRECTION_ORDERED', 'DISCIPLINE', 'EXTERNAL'];
  mount(view,
    h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, '대시보드'), h('p', {}, '진행 중 사건과 기한 경보를 한눈에 확인합니다.')),
      h('a', { class: 'btn primary', href: '#/cases?new=1' }, '+ 민원·사건 접수')),
    h('div', { class: 'grid g4' },
      kpi('진행 중 사건', d.open_count, '#/cases'),
      kpi(`기한 경보 (긴급 ${danger})`, d.alerts.length, '#/cases', danger ? 'st' : ''),
      kpi('미배정 채증 자료', d.unassigned_evidence, '#/monitoring'),
      kpi('미발송 공문', d.unsent_documents, '#/documents')),
    h('div', { class: 'panel' }, h('h2', {}, '처리 단계별 현황'),
      h('div', { class: 'pipeline' }, ...order.map(s => h('a', { class: 'p', href: `#/cases?status=${s}`, style: 'color:inherit' },
        h('b', {}, d.by_status[s] || 0), d.statuses[s])))),
    h('div', { class: 'grid g2' },
      h('div', { class: 'panel' }, h('h2', {}, '기한·조치 경보'),
        d.alerts.length ? h('div', {}, ...d.alerts.slice(0, 20).map(a => h('div', { class: `alert ${a.level}` },
          h('a', { href: `#/cases/${a.case_id}`, style: 'color:inherit;font-weight:600' }, a.case_no), ' ', a.title, h('br'), a.text)))
          : empty('경보가 없습니다.')),
      h('div', {},
        h('div', { class: 'panel' }, h('h2', {}, '예정 회의'),
          d.upcoming_meetings.length ? h('table', {}, h('tbody', {}, ...d.upcoming_meetings.map(m => h('tr', { class: 'clickable', onclick: () => location.hash = `#/meetings/${m.id}` },
            h('td', {}, badge(COMMITTEES[m.committee])), h('td', {}, m.title), h('td', { class: 'nowrap' }, fmtDT(m.scheduled_at))))))
            : empty('예정된 회의가 없습니다.')),
        h('div', { class: 'panel' }, h('h2', {}, '최근 처리 내역'),
          d.recent.length ? h('ul', { class: 'timeline' }, ...d.recent.map(e => h('li', { class: e.type },
            h('div', { class: 'small muted' }, `${fmtDT(e.ts)} · ${e.user_name || ''}`),
            h('a', { href: `#/cases/${e.case_id}` }, e.case_no), ' ', e.note || (e.to_status ? d.statuses[e.to_status] : ''))))
            : empty('처리 내역이 없습니다.')))));
}
