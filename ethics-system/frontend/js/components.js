// 여러 화면에서 공유하는 컴포넌트: 근거 분석 결과, 공문 작성기, 스크리닝 결과
import { api } from './api.js';
import { h, mount, badge, toast, modal, field, input, select, textarea, docView, empty } from './ui.js';
import { canEdit } from './state.js';

const CONF = { HIGH: '높음', MEDIUM: '보통', LOW: '낮음' };

export function findingsList(findings, { onDecide } = {}) {
  if (!findings.length) return empty('위반 의심 표현이 발견되지 않았습니다. (규칙에 없는 유형일 수 있으니 원문을 직접 확인하세요)');
  return h('div', { class: 'card-list' }, ...findings.map(f => h('div', { class: 'item' },
    h('div', { class: 'head' }, badge(`신뢰도 ${CONF[f.confidence]}`, f.confidence), h('b', {}, f.rule_label),
      f.decision ? badge(f.decision === 'CONFIRMED' ? '위반 인정' : '해당 없음', f.decision) : null,
      h('span', { class: 'spacer' }),
      onDecide && canEdit() ? [
        h('button', { class: 'small', onclick: () => onDecide(f, 'CONFIRMED') }, '위반 소지 인정'),
        h('button', { class: 'small', onclick: () => onDecide(f, 'REJECTED') }, '해당 없음')] : null),
    h('div', { class: 'quote' }, f.context || f.matched_text),
    h('div', { class: 'small' }, '근거: ', ...(f.refs || []).map((r, i) => [i ? ' · ' : '', r.citation ? h('span', { title: r.body || '' }, r.citation) : `${r.article_no}${r.item || ''}`])),
    f.guide ? h('div', { class: 'small muted' }, '확인 포인트: ', f.guide) : null)));
}

export function analysisView(result, { onApplyArticle, onLinkPrecedent } = {}) {
  const out = h('div', {});
  if (result.ai_error) out.append(h('div', { class: 'alert warn' }, result.ai_error));
  if (result.ai) {
    const ai = result.ai;
    out.append(h('div', { class: 'panel', style: 'border-color:#b3c8ec' },
      h('h2', {}, 'AI 근거 제한 분석 ', badge(ai.model, 'info')),
      h('p', {}, ai.summary),
      ai.insufficient ? h('div', { class: 'alert warn' }, '근거 부족: ', (ai.missing_info || []).join(' / ')) : null,
      ...ai.issues.map(it => h('div', { class: 'item', style: 'border:1px solid var(--line);border-radius:6px;padding:10px;margin:8px 0' },
        h('div', { class: 'head' }, badge('근거 검증 통과', 'ok'), badge(`가능성 ${it.likelihood}`, it.likelihood === '높음' ? 'HIGH' : it.likelihood === '보통' ? 'MEDIUM' : 'LOW'), h('b', {}, it.issue)),
        h('div', { class: 'small' }, it.citation),
        h('div', { class: 'quote' }, '“', it.quote, '”'),
        h('div', {}, it.reasoning),
        onApplyArticle && canEdit() ? h('button', { class: 'small', onclick: () => onApplyArticle(it.article_db_id, it.issue) }, '이 조문 적용') : null)),
      ai.precedents.length ? h('div', {}, h('h3', {}, 'AI가 지목한 유사 선례'), ...ai.precedents.map(p => h('div', { class: 'small' }, `· ${p.title} — ${p.relevance} (징계: ${p.sanction})`))) : null,
      ai.rejected.length ? h('details', {}, h('summary', {}, `근거 검증 실패로 제외된 항목 ${ai.rejected.length}건 (환각 차단)`),
        ...ai.rejected.map(r => h('div', { class: 'alert danger small' }, `${r.issue || ''} — ${r.reject_reason}`))) : null));
  }
  if (result.findings?.length) {
    out.append(h('h3', {}, '규칙 기반 위반 의심 표현'), findingsList(result.findings));
  }
  out.append(h('h3', {}, '적용 후보 조문 (근거: 등록된 법령·회규 원문)'));
  out.append(result.articles.length ? h('div', { class: 'card-list' }, ...result.articles.map(a => h('div', { class: 'item' },
    h('div', { class: 'head' }, h('b', {}, a.citation), a.items.length ? badge(a.items.join(', '), 'info') : null, badge(`점수 ${a.score}`),
      h('span', { class: 'spacer' }), onApplyArticle && canEdit() ? h('button', { class: 'small', onclick: () => onApplyArticle(a.id, a.reasons[0]) }, '사건에 적용') : null),
    h('div', { class: 'small muted' }, a.reasons.join(' / ')),
    h('details', {}, h('summary', {}, '조문 원문'), h('div', { class: 'quote' }, a.body))))) : empty('일치하는 조문이 없습니다.'));
  out.append(h('h3', {}, '유사 징계 선례'));
  out.append(result.precedents.length ? h('div', { class: 'card-list' }, ...result.precedents.map(p => h('div', { class: 'item' },
    h('div', { class: 'head' }, h('b', {}, p.title), badge(p.sanction_type || '징계 미기재', 'warn'), h('span', { class: 'muted small' }, `${p.volume || ''} ${p.case_ref || ''}`),
      h('span', { class: 'spacer' }), onLinkPrecedent && canEdit() ? h('button', { class: 'small', onclick: () => onLinkPrecedent(p.id) }, '참고 선례로 연결') : null),
    p.holding ? h('div', { class: 'small' }, '요지: ', p.holding) : null))) : empty('등록된 선례 중 유사한 사례가 없습니다. [징계 선례·사례집] 메뉴에서 사례를 등록하세요.'));
  if (result.book_passages?.length) {
    out.append(h('h3', {}, '사례집 원문 검색 결과'));
    out.append(h('div', { class: 'card-list' }, ...result.book_passages.map(c => h('div', { class: 'item' },
      h('div', { class: 'head' }, h('b', {}, c.document_title), c.page ? badge(`${c.page}쪽`) : null, badge(`점수 ${c.score}`)),
      h('div', { class: 'quote' }, c.text.slice(0, 600) + (c.text.length > 600 ? '…' : ''))))));
  }
  return out;
}

// 공문 작성기: 양식 선택 → 자동 작성 → 수정 → 저장
export async function composeDocument({ caseId = null, meetingId = null, category = 'CASE', defaultCode = null, onSaved }) {
  const templates = (await api.get('/api/templates')).filter(t => t.category === category);
  const tplSel = select('template_code', templates.map(t => [t.code, t.name]), defaultCode || templates[0]?.code);
  const extraBox = h('div', { class: 'form-grid' },
    field('시행번호', input('doc_no', '', { placeholder: '예: 대한변리사회-1234' })),
    field('추가 입력 (선택)', input('extra_hint', '', { placeholder: '보완 요청 자료·처리 결과 등' })));
  const subj = input('subject');
  const recip = input('recipient');
  const recipEmail = input('recipient_email', '', { type: 'email' });
  const body = textarea('body', '', { rows: 24, class: 'mono' });
  const missBox = h('div');
  const preview = h('div');
  const refresh = async () => {
    const code = tplSel.value;
    const extra = { doc_no: extraBox.querySelector('[name=doc_no]').value };
    const hint = extraBox.querySelector('[name=extra_hint]').value;
    if (hint) Object.assign(extra, { supplement_items: hint, result_text: hint, decision_text: hint, committee_reason: hint });
    const r = await api.post('/api/documents/preview', { template_code: code, case_id: caseId, meeting_id: meetingId, extra });
    subj.value = r.subject; body.value = r.body; recip.value = r.recipient || ''; recipEmail.value = r.recipient_email || '';
    mount(missBox, r.missing.length ? h('div', { class: 'alert warn' }, `확인 필요 ${r.missing.length}건: ${r.missing.join(', ')} — 본문에서 직접 채우거나 [관리 > 기본 설정]에 담당자 연락처·결재선을 등록하세요.`) : h('div', { class: 'alert ok' }, '모든 항목이 채워졌습니다.'));
    mount(preview, docView(r.body));
  };
  tplSel.addEventListener('change', refresh);
  const ui = h('div', {},
    h('div', { class: 'form-grid' }, field('양식', tplSel), h('div', { style: 'align-self:end' }, h('button', { onclick: refresh }, '다시 자동 작성'))),
    extraBox, missBox,
    h('div', { class: 'form-grid' }, field('제목', subj, 'full'), field('수신(표시)', recip), field('수신 메일', recipEmail)),
    field('본문 (직접 수정 가능)', body),
    h('details', {}, h('summary', {}, '미리보기(확인 필요 항목 강조)'), preview));
  body.addEventListener('input', () => mount(preview, docView(body.value)));
  modal('공문 작성', ui, { wide: true, actions: [{ label: '초안 저장', primary: true, onClick: async () => {
    const r = await api.post('/api/documents', {
      template_code: tplSel.value, case_id: caseId, meeting_id: meetingId,
      doc_no: extraBox.querySelector('[name=doc_no]').value || null,
      subject: subj.value, recipient: recip.value || null, recipient_email: recipEmail.value || null, body: body.value });
    toast('공문 초안이 저장되었습니다.');
    onSaved?.(r.id);
  } }] });
  await refresh();
}
