import { api } from '../api.js';
import { h, mount, badge, empty, field, input, select, textarea, toast, modal, fmtDT, tabs, confirmBox, docView } from '../ui.js';
import { state, canEdit } from '../state.js';
import { composeDocument } from '../components.js';
import { openDocument } from './documents.js';

let tab = 'agenda';
let lastId = null;

export default async function meetingDetail(view, id) {
  if (lastId !== id) { tab = 'agenda'; lastId = id; }
  const m = await api.get(`/api/meetings/${id}`);
  const reload = () => meetingDetail(view, id);
  const ro = !canEdit();
  const body = h('div');
  const setTab = (t) => { tab = t; render(); };

  const head = h('div', { class: 'panel' },
    h('a', { href: '#/meetings', class: 'small' }, '← 목록'),
    h('div', { class: 'row', style: 'margin-top:6px' }, h('h1', {}, m.title), badge(m.committee_label, 'info'),
      badge(({ PLANNED: '예정', HELD: '개최', MINUTES_DRAFT: '회의록 작성 중', APPROVED: '회의록 승인', CANCELLED: '취소' })[m.status])),
    h('div', { class: 'muted' }, `${fmtDT(m.scheduled_at)} · ${m.location || '장소 미정'}`));

  function render() {
    const c = { agenda, prep, minutesTab }[tab]();
    mount(body, tabs([['agenda', `안건·의결 (${m.items.length})`], ['prep', '준비·참석'], ['minutesTab', '녹취 요약·회의록']], setTab, tab), c);
  }

  function agenda() {
    const caseSel = h('select', {}, h('option', { value: '' }, '— 상정 대상 사건 선택 —'), ...m.candidates.map(c => h('option', { value: c.id }, `${c.case_no} ${c.title} [${state.meta.statuses[c.status]}]`)));
    const freeTitle = input('t', '', { placeholder: '또는 일반 안건명 입력 (규정 개정 등)' });
    const items = m.items.map(it => {
      const dec = select('decision', Object.entries(m.decisions), it.decision, { disabled: ro });
      const vf = input('vote_for', it.vote_for ?? '', { type: 'number', min: 0, style: 'width:70px', disabled: ro });
      const va = input('vote_against', it.vote_against ?? '', { type: 'number', min: 0, style: 'width:70px', disabled: ro });
      const note = input('decision_note', it.decision_note || '', { placeholder: '의결 내용·시정 기한 등', disabled: ro });
      return h('div', { class: 'item' },
        h('div', { class: 'head' }, h('b', {}, `제${it.seq}호`), it.case_id ? h('a', { href: `#/cases/${it.case_id}` }, it.case_no) : null, it.title,
          it.case_status_label ? badge(it.case_status_label, 'info') : null, h('span', { class: 'spacer' }),
          canEdit() ? h('button', { class: 'small danger', onclick: async () => { if (confirmBox('안건을 삭제할까요?')) { await api.del(`/api/meetings/items/${it.id}`); reload(); } } }, '삭제') : null),
        h('div', { class: 'row', style: 'margin-top:6px' }, h('div', { style: 'width:170px' }, dec), '찬성', vf, '반대', va, h('div', { style: 'flex:1;min-width:200px' }, note),
          canEdit() ? h('button', { class: 'small', onclick: async () => {
            await api.patch(`/api/meetings/items/${it.id}`, { decision: dec.value, decision_note: note.value || null,
              vote_for: vf.value === '' ? null : Number(vf.value), vote_against: va.value === '' ? null : Number(va.value) });
            toast('저장했습니다.'); reload();
          } }, '저장') : null));
    });
    return h('div', {},
      canEdit() ? h('div', { class: 'panel' }, h('h2', {}, '안건 추가'), h('div', { class: 'row' }, h('div', { style: 'flex:1;min-width:260px' }, caseSel), h('div', { style: 'flex:1;min-width:200px' }, freeTitle),
        h('button', { class: 'primary', onclick: async () => {
          if (!caseSel.value && !freeTitle.value.trim()) return;
          await api.post(`/api/meetings/${id}/items`, { case_id: caseSel.value ? Number(caseSel.value) : null, title: freeTitle.value.trim() || null }); reload();
        } }, '추가'))) : null,
      h('div', { class: 'panel' }, h('div', { class: 'row' }, h('h2', { style: 'margin:0' }, '안건 및 의결'), h('span', { class: 'spacer' }),
        h('button', { onclick: showAgenda }, '회의자료 자동 작성'),
        h('button', { onclick: () => api.download(`/api/meetings/${id}/agenda.docx`, 'agenda.docx') }, '회의자료 .docx'),
        canEdit() ? h('button', { class: 'primary', onclick: applyDecisions }, '의결 결과 사건에 반영') : null),
        h('p', { class: 'small muted' }, '회의자료는 각 사건의 위반 사실·관련 규정·소명 내용·검토의견·참고 선례·처리 경과로 자동 구성됩니다. 의결 반영 시 시정요구→시정 요구, 징계위 회부→징계위원회 회부, 종결/경고→종결로 사건 단계가 바뀝니다.'),
        items.length ? h('div', { class: 'card-list' }, ...items) : empty('안건이 없습니다.')),
      h('div', { class: 'panel' }, h('div', { class: 'row' }, h('h2', { style: 'margin:0' }, '관련 공문'), h('span', { class: 'spacer' }),
        canEdit() ? h('button', { onclick: () => composeDocument({ meetingId: m.id, category: 'MEETING', onSaved: (did) => { reload(); openDocument(did, reload); } }) }, '+ 개최 안내 공문') : null),
        m.documents.length ? h('div', {}, ...m.documents.map(d => h('div', {}, h('a', { href: '#', onclick: (e) => { e.preventDefault(); openDocument(d.id, reload); } }, d.subject), ` — ${d.status}`))) : empty('없음')));
  }

  async function showAgenda() {
    const r = await api.get(`/api/meetings/${id}/agenda`);
    modal('회의자료(안)', docView(r.text), { wide: true, actions: [{ label: '.docx 내려받기', onClick: async () => { await api.download(`/api/meetings/${id}/agenda.docx`, 'agenda.docx'); return false; } }] });
  }

  async function applyDecisions() {
    if (!confirmBox('의결 결과를 각 사건의 처리 단계에 반영할까요? (위원회 상정 상태의 사건만 반영)')) return;
    const r = await api.post(`/api/meetings/${id}/apply-decisions`);
    modal('반영 결과', h('div', {},
      ...r.applied.map(a => h('div', { class: 'alert ok' }, `${a.case_no} → ${a.to}`)),
      ...r.skipped.map(a => h('div', { class: 'alert warn' }, `${a.case_no}: ${a.reason}`)),
      !r.applied.length && !r.skipped.length ? empty('반영할 의결(시정 요구·경고·징계위 회부·종결·이관)이 없습니다.') : null));
    reload();
  }

  function prep() {
    const members = m.members_list;
    const memberRows = members.map((mem, i) => h('tr', {}, h('td', {}, mem.name), h('td', {}, mem.role),
      h('td', {}, select(`attend_${i}`, [['', '미정'], ['true', '참석'], ['false', '불참']], mem.attend === null || mem.attend === undefined ? '' : String(mem.attend), { disabled: ro }))));
    const newName = input('n', '', { placeholder: '이름' }); const newRole = input('r', '위원', { placeholder: '직위' });
    const checks = m.checklist_items.map(k => h('label', { class: 'row', style: 'margin:4px 0;color:var(--ink)' },
      h('input', { type: 'checkbox', 'data-k': k, checked: !!m.checklist_map[k], disabled: ro }), k));
    const info = h('div', { class: 'form-grid' },
      field('회의명', input('title', m.title, { disabled: ro })), field('일시', input('scheduled_at', (m.scheduled_at || '').replace(' ', 'T').slice(0, 16), { type: 'datetime-local', disabled: ro })),
      field('장소', input('location', m.location, { disabled: ro })),
      field('상태', select('status', [['PLANNED', '예정'], ['HELD', '개최'], ['MINUTES_DRAFT', '회의록 작성 중'], ['APPROVED', '회의록 승인(위원장 결재)'], ['CANCELLED', '취소']], m.status, { disabled: ro })));
    const save = async () => {
      const mem = members.map((mm, i) => { const v = body.querySelector(`[name=attend_${i}]`).value; return { ...mm, attend: v === '' ? null : v === 'true' }; });
      const cl = {}; body.querySelectorAll('input[data-k]').forEach(el => { cl[el.dataset.k] = el.checked; });
      const g = (n) => info.querySelector(`[name=${n}]`).value;
      await api.patch(`/api/meetings/${id}`, { title: g('title'), scheduled_at: g('scheduled_at') ? g('scheduled_at').replace('T', ' ') : null, location: g('location') || null, status: g('status'), members: mem, checklist: cl });
      toast('저장했습니다.'); reload();
    };
    const attendCount = members.filter(x => x.attend === true).length;
    return h('div', { class: 'grid g2' },
      h('div', {}, h('div', { class: 'panel' }, h('h2', {}, '회의 정보'), info),
        h('div', { class: 'panel' }, h('h2', {}, `위원 참석 (${attendCount}/${members.length})`),
          h('p', { class: 'small muted' }, '카톡 투표 등으로 확인한 참석 여부를 기록합니다. 의결 정족수: 광고심사위 과반 출석·출석 2/3 찬성, 윤리위 과반 출석·출석 과반 찬성, 징계위 과반 출석·출석 2/3 찬성.'),
          members.length ? h('table', {}, h('tbody', {}, ...memberRows)) : empty('위원 명단이 없습니다.'),
          canEdit() ? h('div', { class: 'row', style: 'margin-top:8px' }, h('div', { style: 'width:140px' }, newName), h('div', { style: 'width:120px' }, newRole),
            h('button', { class: 'small', onclick: async () => {
              if (!newName.value.trim()) return;
              await api.patch(`/api/meetings/${id}`, { members: [...members, { name: newName.value.trim(), role: newRole.value.trim() || '위원', attend: null }] }); reload();
            } }, '위원 추가')) : null)),
      h('div', { class: 'panel' }, h('h2', {}, '준비 체크리스트'), ...checks,
        h('div', { class: 'row', style: 'margin-top:10px' }, canEdit() ? h('button', { class: 'primary', onclick: save }, '저장') : null,
          canEdit() ? h('label', { class: 'row', style: 'margin:0;color:var(--ink)' }, h('input', { type: 'checkbox', checked: !!m.allowance_paid, onchange: async (e) => {
            const v = e.currentTarget.checked;
            await api.patch(`/api/meetings/${id}`, { allowance_paid: v, checklist: { ...m.checklist_map, '수당 지급': v } });
            toast(v ? '수당 지급 완료로 표시했습니다.' : '수당 지급 표시를 해제했습니다.'); reload();
          } }), ' 수당 지급 완료') : null)));
  }

  function minutesTab() {
    const tr = textarea('transcript', m.transcript || '', { rows: 12, class: 'mono', placeholder: '클로바노트 등에서 내보낸 녹취록을 붙여넣으세요.\n형식 예)\n홍길동 00:01\n발언 내용…\n또는  홍길동: 발언 내용' });
    const useAi = h('input', { type: 'checkbox', disabled: !state.meta.ai_available });
    const out = h('div');
    const minutes = textarea('minutes', m.minutes || '', { rows: 22, class: 'mono' });
    return h('div', {},
      h('div', { class: 'panel' }, h('h2', {}, '① 녹취록 → 발언 요지·의결사항 분리'), tr,
        h('div', { class: 'row', style: 'margin-top:8px' }, h('label', { class: 'row', style: 'margin:0' }, useAi, ' AI 요약', state.meta.ai_available ? '' : ' (미설정 — 규칙 기반)'),
          canEdit() ? h('button', { class: 'primary', onclick: async (e) => {
            if (tr.value.trim().length < 10) return toast('녹취록을 입력하세요.', true);
            const btn = e.currentTarget; btn.disabled = true; mount(out, h('div', { class: 'muted' }, '정리 중…'));
            try {
              const r = await api.post(`/api/meetings/${id}/summarize`, { transcript: tr.value, use_ai: useAi.checked });
              mount(out, summaryView(r));
              if (!minutes.value.trim() || confirmBox('요약 결과로 회의록 초안을 새로 채울까요? (기존 내용 대체)')) minutes.value = r.draft;
            } catch (err) { mount(out, h('div', { class: 'alert danger' }, err.message)); }
            finally { btn.disabled = false; }
          } }, '정리 실행') : null), out),
      h('div', { class: 'panel' }, h('h2', {}, '② 회의록'), minutes,
        h('div', { class: 'row', style: 'margin-top:8px' },
          canEdit() ? h('button', { class: 'primary', onclick: async () => { await api.patch(`/api/meetings/${id}`, { minutes: minutes.value, status: m.status === 'PLANNED' || m.status === 'HELD' ? 'MINUTES_DRAFT' : m.status }); toast('회의록을 저장했습니다.'); reload(); } }, '저장') : null,
          canEdit() ? h('button', { onclick: async () => { if (!confirmBox('위원장 전자결재 승인 완료로 표시할까요?')) return; await api.patch(`/api/meetings/${id}`, { minutes: minutes.value, status: 'APPROVED' }); toast('승인 완료로 표시했습니다.'); reload(); } }, '위원장 승인 완료') : null,
          h('button', { onclick: () => api.download(`/api/meetings/${id}/minutes.docx`, 'minutes.docx') }, '회의록 .docx'))));
  }

  render();
  mount(view, head, body);
}

function summaryView(r) {
  return h('div', {},
    r.ai_error ? h('div', { class: 'alert warn' }, r.ai_error) : null,
    h('div', { class: 'alert info small' }, r.notice),
    r.overview ? h('p', {}, r.overview) : null,
    h('h3', {}, '의결 관련 발언'),
    r.resolutions.length ? h('div', {}, ...r.resolutions.map(x => h('div', { class: 'alert ' + (x.verified === false ? 'danger' : 'ok') },
      x.speaker ? `[${x.speaker}] ` : '', x.text, x.verified === false ? ' — 근거 문장 검증 실패' : '', x.evidence_quote ? h('div', { class: 'small' }, '근거: ', x.evidence_quote) : null))) : empty('의결 표현을 찾지 못했습니다.'),
    h('h3', {}, '위원별 핵심 발언'),
    ...r.speakers.map(s => h('div', { class: 'item', style: 'margin-bottom:8px' }, h('b', {}, s.name), h('ul', {}, ...s.points.map(p => h('li', {}, p))))),
    r.follow_ups.length ? h('div', {}, h('h3', {}, '후속 조치'), h('ul', {}, ...r.follow_ups.map(f => h('li', {}, f.text)))) : null);
}
