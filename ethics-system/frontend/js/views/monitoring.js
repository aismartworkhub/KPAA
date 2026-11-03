import { api } from '../api.js';
import { h, mount, badge, empty, field, input, textarea, toast, fmtDate, modal } from '../ui.js';
import { canEdit, state } from '../state.js';
import { findingsList } from '../components.js';

export default async function monitoring(view) {
  const [kw, inbox] = await Promise.all([api.get('/api/monitoring/keywords'), api.get('/api/evidence?unassigned=true')]);
  const reload = () => monitoring(view);

  // 1) 빠른 스크리닝
  const text = textarea('text', '', { rows: 6, placeholder: '광고 문구를 붙여넣으세요. 예) 국내 최고 특허사무소! 상표 등록률 98%, 미등록 시 전액 환불' });
  const out = h('div');
  const quick = h('div', { class: 'panel' }, h('h2', {}, '① 광고 문구 즉시 스크리닝'),
    h('p', { class: 'small muted' }, '수집한 광고 문구가 광고규정 어느 조항에 해당할 소지가 있는지 즉시 분류합니다(저장되지 않음).'),
    text, h('div', { class: 'row', style: 'margin-top:8px' }, h('button', { class: 'primary', onclick: async () => {
      if (!text.value.trim()) return;
      const r = await api.post('/api/screen', { text: text.value });
      mount(out, h('div', { class: 'alert info small' }, r.notice), findingsList(r.findings));
    } }, '스크리닝'),
      canEdit() ? h('button', { onclick: () => saveEvidenceDialog(text.value, reload) }, '채증 자료로 저장') : null), out);

  // 2) 검색어 세트
  const kwPanel = h('div', { class: 'panel' }, h('h2', {}, '② 정기 모니터링 검색어'),
    h('p', { class: 'small muted' }, '위반 빈발 표현으로 포털·SNS를 바로 검색합니다. 의심 사례는 사무소명과 광고 내용이 보이도록 캡처 후 아래 ③ 또는 사건 화면에서 등록하세요.'),
    h('table', {}, h('tbody', {}, ...kw.flatMap(g => g.queries.map((q, i) => h('tr', {},
      h('td', { class: 'small muted nowrap' }, i === 0 ? g.group : ''), h('td', {}, h('b', {}, q.q)),
      h('td', { class: 'row' }, ...[['naver', '네이버'], ['naver_blog', '네이버 블로그'], ['google', '구글'], ['daum', '다음'], ['instagram', '인스타그램']].map(([k, l]) =>
        h('a', { class: 'btn small', href: q[k], target: '_blank', rel: 'noopener noreferrer' }, l)))))))));

  // 3) CSV 일괄
  const fileIn = h('input', { type: 'file', accept: '.csv' });
  const saveChk = h('input', { type: 'checkbox' });
  const batchOut = h('div');
  const batch = h('div', { class: 'panel' }, h('h2', {}, '③ 수집 결과 일괄 분류 (CSV)'),
    h('p', { class: 'small muted' }, '열 이름: url, office_name, ad_text (엑셀에서 CSV로 저장). 위반 소지가 있는 행을 규정별로 분류하고, 선택 시 채증 자료함에 저장합니다.'),
    h('div', { class: 'row' }, fileIn, canEdit() ? h('label', { class: 'row', style: 'margin:0' }, saveChk, ' 의심 건 채증 자료함에 저장') : null,
      h('button', { class: 'primary', onclick: async () => {
        if (!fileIn.files[0]) return toast('CSV 파일을 선택하세요.', true);
        const fd = new FormData(); fd.append('file', fileIn.files[0]); fd.append('save', saveChk.checked ? 'true' : 'false');
        const r = await api.upload('/api/screen/batch', fd);
        mount(batchOut, h('div', { class: 'alert info' }, `총 ${r.total}건 중 위반 의심 ${r.flagged}건`),
          h('table', {}, h('thead', {}, h('tr', {}, ...['행', '사무소', '광고 문구', '분류', '신뢰도'].map(t => h('th', {}, t)))),
            h('tbody', {}, ...r.items.map(it => h('tr', {}, h('td', {}, it.row), h('td', {}, it.office_name || '-'),
              h('td', { class: 'small' }, it.url ? h('a', { href: it.url, target: '_blank', rel: 'noopener noreferrer' }, it.ad_text) : it.ad_text),
              h('td', {}, h('div', { class: 'chips' }, ...it.labels.map(l => h('span', { class: 'chip' }, l)))),
              h('td', {}, it.max_confidence ? badge(it.max_confidence, it.max_confidence) : badge('없음')))))));
        if (saveChk.checked) reload();
      } }, '분류 실행')), batchOut);

  // 4) 미배정 채증함
  const inboxPanel = h('div', { class: 'panel' }, h('h2', {}, `④ 미배정 채증 자료함 (${inbox.length})`),
    inbox.length ? h('table', {}, h('thead', {}, h('tr', {}, ...['#', '채증일', '사무소', '광고 문구', '분류', ''].map(t => h('th', {}, t)))),
      h('tbody', {}, ...inbox.map(e => h('tr', {},
        h('td', {}, e.id), h('td', { class: 'nowrap' }, fmtDate(e.captured_at)), h('td', {}, e.office_name || '-'),
        h('td', { class: 'small' }, e.url ? h('a', { href: e.url, target: '_blank', rel: 'noopener noreferrer' }, (e.ad_text || e.url).slice(0, 120)) : (e.ad_text || '').slice(0, 120)),
        h('td', {}, h('div', { class: 'chips' }, ...(e.labels || '').split(',').filter(Boolean).map(l => h('span', { class: 'chip' }, l)))),
        h('td', { class: 'nowrap' }, canEdit() ? [
          h('button', { class: 'small primary', onclick: async () => { const r = await api.post(`/api/evidence/${e.id}/create-case`, {}); toast(`${r.case_no} 사건 생성`); location.hash = `#/cases/${r.id}`; } }, '사건 생성'),
          ' ', h('button', { class: 'small', onclick: () => assignDialog(e, reload) }, '기존 사건에 연결')] : null)))))
      : empty('미배정 채증 자료가 없습니다.'));

  mount(view, h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, '광고 모니터링'),
    h('p', {}, '검색 → 채증 → 규정별 1차 분류 → 사건화까지 한 화면에서 처리합니다.'))),
  quick, kwPanel, batch, inboxPanel);
}

function saveEvidenceDialog(adText, done) {
  const b = h('div', { class: 'form-grid' }, field('URL', input('url')), field('사무소명', input('office_name')),
    field('채증일', input('captured_at', new Date().toISOString().slice(0, 10), { type: 'date' })),
    field('캡처 파일', h('input', { type: 'file', name: 'file', accept: 'image/*,.pdf' })),
    field('광고 문구', textarea('ad_text', adText, { rows: 4 }), 'full'));
  modal('채증 자료 저장', b, { actions: [{ label: '저장', primary: true, onClick: async () => {
    const fd = new FormData();
    b.querySelectorAll('input[name], textarea[name]').forEach(el => {
      if (el.type === 'file') { if (el.files[0]) fd.append('file', el.files[0]); } else if (el.value.trim()) fd.append(el.name, el.value.trim());
    });
    await api.upload('/api/evidence', fd); toast('채증 자료함에 저장했습니다.'); done();
  } }] });
}

async function assignDialog(e, done) {
  const list = await api.get('/api/cases?case_type=AD&include_closed=false&size=200');
  const sel = h('select', {}, ...list.items.map(c => h('option', { value: c.id }, `${c.case_no} ${c.title}`)));
  modal('기존 사건에 연결', field('사건', sel), { actions: [{ label: '연결', primary: true, onClick: async () => {
    await api.post(`/api/evidence/${e.id}/assign`, { case_id: Number(sel.value) }); toast('연결했습니다.'); done();
  } }] });
}
