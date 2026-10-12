import { api, qs } from '../api.js';
import { h, mount, badge, empty, field, input, select, textarea, toast, modal } from '../ui.js';
import { state, isAdmin } from '../state.js';
import { analysisView } from '../components.js';

export default async function regs(view) {
  const p = Object.fromEntries(new URLSearchParams(location.hash.split('?')[1] || ''));
  const [sources, articles] = await Promise.all([api.get('/api/articles/sources'), api.get('/api/articles' + qs({ source: p.source, q: p.q }))]);
  const reload = () => regs(view);

  // 근거 매칭
  const facts = textarea('facts', '', { rows: 5, placeholder: '민원 또는 모니터링 사실관계를 입력하세요.\n예) A특허사무소가 블로그에 "상표등록 100% 보장, 미등록 시 전액 환불"이라고 광고함' });
  const ctype = select('case_type', [['', '유형 자동'], ['AD', '광고'], ['ETHICS', '윤리']], '');
  const useAi = h('input', { type: 'checkbox', disabled: !state.meta.ai_available });
  const out = h('div');
  const matcher = h('div', { class: 'panel' }, h('h2', {}, '사실관계 → 적용 규정 매칭'),
    h('p', { class: 'small muted' }, '등록된 변리사법·윤리강령·광고규정·위원회 운영규정 원문 안에서만 근거를 찾습니다. AI 사용 시에도 제공된 조문 밖의 답변·인용은 서버에서 자동 차단됩니다.'),
    facts, h('div', { class: 'row', style: 'margin-top:8px' }, ctype,
      h('label', { class: 'row', style: 'margin:0' }, useAi, ' AI 근거 제한 분석', state.meta.ai_available ? '' : ' (미설정)'),
      h('button', { class: 'primary', onclick: async (e) => {
        if (!facts.value.trim()) return;
        const btn = e.currentTarget; btn.disabled = true; mount(out, h('div', { class: 'muted' }, '분석 중…'));
        try { mount(out, analysisView(await api.post('/api/articles/match', { facts: facts.value, case_type: ctype.value || null, use_ai: useAi.checked }))); }
        catch (err) { mount(out, h('div', { class: 'alert danger' }, err.message)); }
        finally { btn.disabled = false; }
      } }, '매칭')), out);

  // 조문 열람
  const q = input('q', p.q || '', { placeholder: '조문 검색 (예: 광고, 비밀, 소명)' });
  const go = () => { location.hash = '#/regs' + qs({ source: p.source, q: q.value.trim() }); };
  q.addEventListener('keydown', (e) => { if (e.key === 'Enter') go(); });
  const browse = h('div', { class: 'panel' }, h('h2', {}, '법령·회규 원문'),
    h('div', { class: 'row' },
      h('a', { class: 'btn small' + (!p.source ? ' primary' : ''), href: '#/regs' + qs({ q: p.q }) }, '전체'),
      ...sources.map(s => h('a', { class: 'btn small' + (p.source === s.source ? ' primary' : ''), href: '#/regs' + qs({ source: s.source, q: p.q }) }, `${s.source_name} (${s.count})`)),
      h('span', { class: 'spacer' }), h('div', { style: 'width:260px' }, q), h('button', { onclick: go }, '검색'),
      isAdmin() ? h('button', { onclick: () => importDialog(reload) }, '개정 원문 반영') : null),
    h('p', { class: 'small muted' }, sources.map(s => `${s.source_name} 최종 반영 ${String(s.updated_at).slice(0, 10)}`).join(' · ')),
    articles.length ? h('div', { class: 'card-list' }, ...articles.map(a => h('div', { class: 'item' },
      h('div', { class: 'head' }, h('b', {}, a.citation), a.chapter ? badge(a.chapter) : null, h('span', { class: 'spacer' }),
        isAdmin() ? h('button', { class: 'small', onclick: () => editDialog(a, reload) }, '수정') : null),
      h('div', { class: 'quote' }, a.body)))) : empty('조문이 없습니다.'));
  mount(view, h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, '규정·근거 매칭'), h('p', {}, '변리사법 및 본회 규정 원문 열람과 사실관계별 적용 조항 매칭'))), matcher, browse);
}

function editDialog(a, done) {
  const title = input('title', a.title);
  const body = textarea('body', a.body, { rows: 14 });
  modal(`조문 수정 — ${a.citation}`, h('div', {}, h('div', { class: 'alert warn small' }, '조문 원문은 매칭·AI 분석의 유일한 근거입니다. 개정 시에만 수정하세요(변경 전 내용은 감사로그에 보관).'),
    field('제목', title), field('본문', body)), { wide: true, actions: [{ label: '저장', primary: true, onClick: async () => {
      await api.put(`/api/articles/${a.id}`, { title: title.value || null, body: body.value }); toast('저장되었습니다.'); done();
    } }] });
}

function importDialog(done) {
  const file = h('input', { type: 'file', accept: '.hwp,.hwpx,.docx,.txt,.pdf' });
  const name = input('source_name', '', { placeholder: "문서에 '< 규정명 >' 머리표가 없을 때만 입력" });
  modal('개정 법령·회규 원문 반영', h('div', {},
    h('p', { class: 'small' }, 'HWP/HWPX/DOCX/TXT/PDF 원문을 올리면 조문 단위로 분해해 반영합니다. 같은 규정의 기존 조문은 갱신되고, 원문에서 사라진 조문은 삭제됩니다.'),
    h('p', { class: 'small muted' }, "여러 규정을 한 파일에 넣을 때는 각 규정 앞에 '< 변리사 광고에 관한 규정 >'처럼 머리표를 둡니다."),
    field('파일', file), field('규정명', name)), { actions: [{ label: '반영', primary: true, onClick: async () => {
      if (!file.files[0]) throw new Error('파일을 선택하세요.');
      const fd = new FormData(); fd.append('file', file.files[0]); if (name.value.trim()) fd.append('source_name', name.value.trim());
      const r = await api.upload('/api/articles/import', fd); toast(`${r.count}개 조문 반영 (${r.sources.join(', ')})`); done();
    } }] });
}
