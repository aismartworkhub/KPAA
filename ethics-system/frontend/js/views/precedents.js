import { api, qs } from '../api.js';
import { h, mount, badge, empty, field, input, select, textarea, toast, modal, formData, bytes, fmtDT, confirmBox, tabs } from '../ui.js';
import { state, canEdit, isAdmin } from '../state.js';

const ORIGIN = { KBA: '변호사 징계사례집', KPAA: '본회 사례', OTHER: '기타', DEMO: '가상 예시' };
let tab = 'search';

export default async function precedents(view) {
  const p = Object.fromEntries(new URLSearchParams(location.hash.split('?')[1] || ''));
  const reload = () => precedents(view);
  const body = h('div');
  const head = h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, '징계 선례·사례집'),
    h('p', {}, '변호사 징계사례집(1~8집) 원문과 정리된 선례를 교차 검색해 판결 요지·징계 수위를 빠르게 확인합니다.')),
    canEdit() ? h('div', { class: 'row' }, h('button', { onclick: () => precedentDialog(null, reload) }, '+ 선례 등록'), h('button', { onclick: () => csvDialog(reload) }, 'CSV 일괄 등록')) : null);
  const setTab = (t) => { tab = t; render(); };
  async function render() {
    const content = tab === 'search' ? await searchTab() : tab === 'list' ? await listTab(p, reload) : await booksTab(reload);
    mount(body, tabs([['search', '유사 사례 검색'], ['list', '선례 목록'], ['books', '사례집 원문']], setTab, tab), content);
  }
  await render();
  mount(view, head, body);
}

async function searchTab() {
  const text = textarea('text', '', { rows: 4, placeholder: '사건의 핵심 사실을 입력하세요. 예) 블로그에 승소율 95% 표기, 무료 상담 후 수임 유도' });
  const out = h('div');
  return h('div', { class: 'panel' }, h('h2', {}, '사실관계로 선례·원문 동시 검색'), text,
    h('div', { class: 'row', style: 'margin-top:8px' }, h('button', { class: 'primary', onclick: async () => {
      if (text.value.trim().length < 2) return;
      const r = await api.post('/api/precedents/search', { text: text.value, top_k: 10 });
      mount(out,
        h('h3', {}, `정리된 선례 (${r.precedents.length})`),
        r.precedents.length ? h('table', {}, h('thead', {}, h('tr', {}, ...['사례', '징계 수위', '요지', '유사도'].map(t => h('th', {}, t)))),
          h('tbody', {}, ...r.precedents.map(x => h('tr', {},
            h('td', {}, h('b', {}, x.title), h('div', { class: 'small muted' }, `${ORIGIN[x.origin] || ''} ${x.volume || ''} ${x.case_ref || ''}`)),
            h('td', {}, badge(x.sanction_type || '미기재', 'warn'), h('div', { class: 'small' }, x.sanction_detail || '')),
            h('td', { class: 'small' }, x.holding || '-'), h('td', {}, x.score))))) : h('div', { class: 'empty' }, '유사한 선례가 없습니다.'),
        h('h3', {}, `사례집 원문 (${r.passages.length})`),
        r.passages.length ? h('div', { class: 'card-list' }, ...r.passages.map(c => h('div', { class: 'item' },
          h('div', { class: 'head' }, h('b', {}, c.document_title), c.page ? badge(`${c.page}쪽`) : null, badge(`유사도 ${c.score}`), h('span', { class: 'spacer' }),
            canEdit() ? h('button', { class: 'small', onclick: () => extractDialog([c.id]) }, '이 부분을 선례로 정리') : null),
          h('div', { class: 'quote' }, c.text)))) : h('div', { class: 'empty' }, '업로드된 사례집이 없거나 일치하는 부분이 없습니다. [사례집 원문] 탭에서 PDF/HWP를 올리세요.'));
    } }, '검색')), out);
}

async function listTab(p, reload) {
  const [items, facets] = await Promise.all([api.get('/api/precedents' + qs({ q: p.q, sanction_type: p.sanction_type, origin: p.origin })), api.get('/api/precedents/facets')]);
  const q = input('q', p.q || '', { placeholder: '제목·요지·키워드 검색' });
  const st = select('sanction_type', [['', '전체 징계 수위'], ...facets.sanction_types.map(s => [s, s])], p.sanction_type);
  const go = () => { location.hash = '#/precedents' + qs({ q: q.value.trim(), sanction_type: st.value }); };
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
  return h('div', {},
    h('div', { class: 'panel row' }, h('div', { style: 'width:280px' }, q), h('div', { style: 'width:180px' }, st), h('button', { onclick: go }, '검색'),
      h('span', { class: 'spacer' }), h('span', { class: 'small muted' }, facets.stats.map(s => `${s.sanction_type || '미기재'} ${s.n}`).join(' · '))),
    h('div', { class: 'panel', style: 'padding:0;overflow-x:auto' }, items.length ? h('table', {},
      h('thead', {}, h('tr', {}, ...['출처', '사례', '분류', '징계 수위', '관련 규정', ''].map(t => h('th', {}, t)))),
      h('tbody', {}, ...items.map(x => h('tr', {},
        h('td', { class: 'small nowrap' }, ORIGIN[x.origin] || x.origin, h('div', { class: 'muted' }, `${x.volume || ''} ${x.case_ref || ''}`)),
        h('td', {}, h('b', {}, x.title), x.holding ? h('div', { class: 'small' }, x.holding.slice(0, 200)) : null),
        h('td', {}, x.category || '-'), h('td', {}, badge(x.sanction_type || '미기재', 'warn')), h('td', { class: 'small' }, x.related_rules || '-'),
        h('td', { class: 'nowrap' }, canEdit() ? [h('button', { class: 'small', onclick: () => precedentDialog(x, reload) }, '수정'), ' ',
          h('button', { class: 'small danger', onclick: async () => { if (confirmBox('삭제할까요?')) { await api.del(`/api/precedents/${x.id}`); reload(); } } }, '삭제')] : null)))))
      : empty('등록된 선례가 없습니다.')));
}

async function booksTab(reload) {
  const docs = await api.get('/api/source-docs?kind=precedent_book');
  const file = h('input', { type: 'file', accept: '.pdf,.hwp,.hwpx,.docx,.txt' });
  const title = input('title', '', { placeholder: '예: 변호사 징계사례집 제8집' });
  const chunkOut = h('div');
  return h('div', {},
    canEdit() ? h('div', { class: 'panel' }, h('h2', {}, '사례집 업로드'),
      h('p', { class: 'small muted' }, '대한변협 홈페이지에서 내려받은 징계사례집 PDF(또는 HWP)를 집별로 올리면 본문을 추출해 검색 색인을 만듭니다. 스캔 이미지 PDF는 OCR 처리 후 올려야 합니다. 파일이 클수록 처리에 시간이 걸립니다.'),
      h('div', { class: 'form-grid' }, field('자료명', title), field('파일 (최대 200MB)', file)),
      h('button', { class: 'primary', style: 'margin-top:8px', onclick: async (e) => {
        if (!file.files[0] || !title.value.trim()) return toast('자료명과 파일을 입력하세요.', true);
        const fd = new FormData(); fd.append('file', file.files[0]); fd.append('title', title.value.trim()); fd.append('kind', 'precedent_book');
        const btn = e.currentTarget; btn.disabled = true; btn.textContent = '추출 중…';
        try { const r = await api.upload('/api/source-docs', fd); toast(`${r.pages}쪽 / ${r.chunks}개 조각 색인 완료`); reload(); }
        catch (err) { toast(err.message, true); btn.disabled = false; btn.textContent = '업로드 및 색인'; }
      } }, '업로드 및 색인')) : null,
    h('div', { class: 'panel' }, h('h2', {}, '등록된 사례집'),
      docs.length ? h('table', {}, h('thead', {}, h('tr', {}, ...['자료명', '파일', '쪽수', '색인 조각', '등록일', ''].map(t => h('th', {}, t)))),
        h('tbody', {}, ...docs.map(d => h('tr', {}, h('td', {}, d.title), h('td', { class: 'small' }, `${d.filename} (${bytes(d.size)})`), h('td', {}, d.pages ?? '-'),
          h('td', {}, d.chunk_count), h('td', { class: 'nowrap' }, fmtDT(d.uploaded_at)),
          h('td', { class: 'nowrap' }, h('button', { class: 'small', onclick: () => browseChunks(d, chunkOut) }, '원문 보기'), ' ',
            isAdmin() ? h('button', { class: 'small danger', onclick: async () => { if (confirmBox('사례집과 색인을 삭제할까요?')) { await api.del(`/api/source-docs/${d.id}`); reload(); } } }, '삭제') : null)))))
        : empty('등록된 사례집이 없습니다.')),
    chunkOut);
}

async function browseChunks(d, out) {
  const q = input('q', '', { placeholder: '원문 내 단어 검색 (예: 광고, 정직)' });
  const list = h('div');
  const load = async () => {
    const rows = await api.get(`/api/source-docs/${d.id}/chunks` + qs({ q: q.value.trim() }));
    mount(list, rows.length ? h('div', { class: 'card-list' }, ...rows.map(c => h('div', { class: 'item' },
      h('div', { class: 'head' }, c.page ? badge(`${c.page}쪽`) : null, h('span', { class: 'spacer' }),
        canEdit() ? h('button', { class: 'small', onclick: () => extractDialog([c.id]) }, '선례로 정리') : null),
      h('div', { class: 'quote' }, c.text)))) : empty('결과가 없습니다.'));
  };
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') load(); });
  mount(out, h('div', { class: 'panel' }, h('h2', {}, d.title), h('div', { class: 'row' }, h('div', { style: 'width:300px' }, q), h('button', { onclick: load }, '검색')), list));
  await load();
}

async function extractDialog(chunkIds) {
  const useAi = state.meta.ai_available && confirm('AI로 사례 요지·징계 수위를 추출할까요? (취소 = 규칙 기반 후보)');
  const r = await api.post('/api/source-docs/extract', { chunk_ids: chunkIds, use_ai: useAi });
  const cands = r.candidates;
  if (!cands.length) return toast('추출된 사례가 없습니다.', true);
  const forms = cands.map(c => precedentForm({ origin: 'KBA', ...c }));
  modal(`선례 후보 ${cands.length}건 — 원문과 대조 후 등록`, h('div', {},
    h('div', { class: 'alert info small' }, r.notice || 'AI 추출 결과입니다. 원문 근거 문장 검증 결과를 확인하고 수정한 뒤 등록하세요.'),
    ...cands.map((c, i) => h('div', { class: 'panel' }, c.verified === false ? h('div', { class: 'alert danger small' }, '징계 결과 문장이 원문에서 확인되지 않았습니다 — 반드시 원문 대조') : null,
      c.source_quote ? h('div', { class: 'quote small' }, '근거: ', c.source_quote) : null, forms[i]))),
  { wide: true, actions: [{ label: '모두 등록', primary: true, onClick: async () => {
    for (const f of forms) await api.post('/api/precedents', precedentPayload(f));
    toast(`${forms.length}건 등록했습니다.`);
  } }] });
}

function precedentForm(x = {}) {
  return h('div', { class: 'form-grid' },
    field('출처', select('origin', Object.entries(ORIGIN).filter(([k]) => k !== 'DEMO'), x.origin || 'KBA')),
    field('집·권', input('volume', x.volume)), field('사건번호', input('case_ref', x.case_ref)), field('결정일', input('decided_on', x.decided_on, { type: 'date' })),
    field('제목 *', input('title', x.title), 'full'),
    field('분류', input('category', x.category, { placeholder: '광고 / 수임 / 품위 / 비밀유지 …' })),
    field('징계 수위', input('sanction_type', x.sanction_type, { placeholder: '견책 / 과태료 / 정직 / 제명 …' })),
    field('징계 상세', input('sanction_detail', x.sanction_detail), 'full'),
    field('사실관계', textarea('facts', x.facts, { rows: 4 }), 'full'),
    field('결정 요지', textarea('holding', x.holding, { rows: 4 }), 'full'),
    field('관련 규정', input('related_rules', x.related_rules)), field('키워드', input('keywords', x.keywords)),
    h('input', { type: 'hidden', name: 'source_document_id', value: x.source_document_id ?? '' }),
    h('input', { type: 'hidden', name: 'source_page', value: x.source_page ?? '' }));
}
function precedentPayload(f) {
  const d = formData(f);
  d.source_document_id = d.source_document_id ? Number(d.source_document_id) : null;
  d.source_page = d.source_page ? Number(d.source_page) : null;
  if (!d.title) throw new Error('제목을 입력하세요.');
  return d;
}

function precedentDialog(x, done) {
  const f = precedentForm(x || {});
  modal(x ? '선례 수정' : '선례 등록', f, { wide: true, actions: [{ label: '저장', primary: true, onClick: async () => {
    const d = precedentPayload(f);
    if (x) await api.put(`/api/precedents/${x.id}`, d); else await api.post('/api/precedents', d);
    toast('저장되었습니다.'); done();
  } }] });
}

function csvDialog(done) {
  const file = h('input', { type: 'file', accept: '.csv' });
  modal('선례 CSV 일괄 등록', h('div', {},
    h('p', { class: 'small' }, '머리행 열 이름: origin, volume, case_ref, title(필수), decided_on, category, sanction_type, sanction_detail, facts, holding, related_rules, keywords'),
    h('p', { class: 'small muted' }, 'origin 값: KBA(변호사 징계사례집) / KPAA(본회) / OTHER. 엑셀에서 "CSV UTF-8"로 저장하세요.'),
    file), { actions: [{ label: '등록', primary: true, onClick: async () => {
      if (!file.files[0]) throw new Error('파일을 선택하세요.');
      const fd = new FormData(); fd.append('file', file.files[0]);
      const r = await api.upload('/api/precedents/import-csv', fd); toast(`${r.imported}건 등록 (제외 ${r.skipped})`); done();
    } }] });
}
