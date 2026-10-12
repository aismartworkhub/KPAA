import { api } from '../api.js';
import { h, mount, badge, fmtDate, fmtDT, empty, modal, field, input, select, textarea, formData, toast, tabs, bytes, confirmBox } from '../ui.js';
import { state, canEdit, isAdmin, STATUS_FLOW } from '../state.js';
import { analysisView, findingsList, composeDocument } from '../components.js';
import { openDocument } from './documents.js';

let activeTab = 'overview';
let lastCaseId = null;

export default async function caseDetail(view, id) {
  if (lastCaseId !== id) { activeTab = 'overview'; lastCaseId = id; }
  const c = await api.get(`/api/cases/${id}`);
  const reload = () => caseDetail(view, id);
  const meta = state.meta;

  const curIdx = STATUS_FLOW.indexOf(c.status);
  const stepper = h('div', { class: 'stepper' }, ...STATUS_FLOW.map((s, i) => h('div', {
    class: 's ' + (s === c.status ? 'cur' : (curIdx > i ? 'done' : '')) }, meta.statuses[s])));

  const head = h('div', { class: 'panel' },
    h('div', { class: 'row' },
      h('a', { href: '#/cases', class: 'small' }, '← 목록'),
      h('span', { class: 'spacer' }),
      canEdit() ? h('button', { onclick: () => transitionDialog(c, reload) }, '단계 변경') : null),
    h('div', { class: 'row', style: 'margin-top:6px' },
      h('h1', {}, c.case_no), badge(c.type_label, c.case_type), c.priority === 'SERIOUS' ? badge('중대', 'SERIOUS') : null,
      badge(c.status_label, 'info'), h('span', { class: 'muted' }, c.source_label, ' 접수 · ', fmtDate(c.received_at))),
    h('div', { style: 'font-size:16px;margin:4px 0 8px' }, c.title),
    stepper,
    ...c.alerts.map(a => h('div', { class: `alert ${a.level}` }, a.text)),
    h('div', { class: 'row small muted', style: 'margin-top:6px' },
      c.explanation_due ? h('span', {}, `소명 기한 ${c.explanation_due}`) : null,
      c.correction_due ? h('span', {}, `· 시정 기한 ${c.correction_due}`) : null,
      c.objection_due ? h('span', {}, `· 이의신청 기한 ${c.objection_due}`) : null,
      c.closed_reason ? h('span', {}, `· 종결 사유: ${c.closed_reason}`) : null));

  const body = h('div');
  const setTab = (t) => { activeTab = t; render(); };
  function render() {
    const tabDefs = [['overview', '개요·검토의견'], ['evidence', `채증·스크리닝 (${c.evidence.length})`], ['analysis', `근거 분석 (${c.articles.length})`],
      ['documents', `공문 (${c.documents.length})`], ['history', `처리 경과 (${c.events.length})`]];
    const content = { overview, evidence, analysis, documents, history }[activeTab]();
    mount(body, tabs(tabDefs, setTab, activeTab), content);
  }

  function overview() {
    const ro = !canEdit();
    const f = h('div', { class: 'form-grid' },
      field('제목', input('title', c.title, { disabled: ro }), 'full'),
      field('피민원 사무소명', input('respondent_office', c.respondent_office, { disabled: ro })),
      field('변리사 성명', input('respondent_name', c.respondent_name, { disabled: ro })),
      field('등록번호', input('respondent_reg_no', c.respondent_reg_no, { disabled: ro })),
      field('사무소 대표 메일', input('respondent_email', c.respondent_email, { disabled: ro })),
      field('회원 여부', select('respondent_is_member', [['true', '등록 회원'], ['false', '미등록·비회원']], c.respondent_is_member ? 'true' : 'false', { disabled: ro })),
      field('중요도', select('priority', [['NORMAL', '일반'], ['SERIOUS', '중대(회장 결재)']], c.priority, { disabled: ro })),
      field('민원인', input('complainant_name', c.complainant_name, { disabled: ro })),
      field('민원인 연락처', input('complainant_contact', c.complainant_contact, { disabled: ro })),
      field('위반(게재) 일자', input('violation_date', c.violation_date, { type: 'date', disabled: ro })),
      field('담당자', select('assignee_id', [['', '미지정'], ...meta.users.filter(u => u.role !== 'viewer').map(u => [u.id, u.name])], c.assignee_id, { disabled: ro })),
      field('사실관계', textarea('facts', c.facts, { rows: 5, disabled: ro }), 'full'),
      field('소명 내용 요약 (회의자료에 사용)', textarea('explanation_summary', c.explanation_summary, { rows: 4, disabled: ro }), 'full'),
      field('사무국 검토의견 (회의자료에 사용)', textarea('review_opinion', c.review_opinion, { rows: 4, disabled: ro }), 'full'));
    return h('div', { class: 'panel' }, f,
      canEdit() ? h('div', { class: 'row', style: 'margin-top:12px' }, h('button', { class: 'primary', onclick: async () => {
        const d = formData(f);
        d.respondent_is_member = d.respondent_is_member !== 'false';
        d.assignee_id = d.assignee_id ? Number(d.assignee_id) : null;
        await api.patch(`/api/cases/${c.id}`, d); toast('저장되었습니다.'); reload();
      } }, '저장')) : null,
      c.meetings.length ? h('div', {}, h('h3', {}, '상정된 회의'), ...c.meetings.map(m => h('div', {},
        h('a', { href: `#/meetings/${m.id}` }, m.title), ` (${fmtDT(m.scheduled_at)}) — ${m.decision}`))) : null);
  }

  function evidence() {
    const f = h('div', { class: 'form-grid' },
      field('URL', input('url', '', { placeholder: 'https://' })),
      field('사무소명(광고상 표시)', input('office_name', c.respondent_office)),
      field('채증 일자', input('captured_at', new Date().toISOString().slice(0, 10), { type: 'date' })),
      field('캡처 파일 (이미지·PDF)', h('input', { type: 'file', name: 'file', accept: 'image/*,.pdf,.hwp,.hwpx,.docx' })),
      field('광고 문구 (캡처 내 텍스트를 붙여넣으면 자동 스크리닝)', textarea('ad_text', '', { rows: 4 }), 'full'),
      field('메모', input('note'), 'full'));
    const decide = async (fd, decision) => { await api.patch(`/api/findings/${fd.id}`, { decision }); reload(); };
    return h('div', {},
      canEdit() ? h('div', { class: 'panel' }, h('h2', {}, '채증 자료 추가'),
        h('p', { class: 'small muted' }, '사무소명과 광고 내용이 정확히 보이도록 캡처하세요. 파일의 SHA-256 해시가 기록되어 사후 변조 여부를 확인할 수 있습니다.'),
        f, h('div', { class: 'row', style: 'margin-top:10px' }, h('button', { class: 'primary', onclick: async (e) => {
          const fd = new FormData();
          fd.append('case_id', c.id);
          f.querySelectorAll('input[name], textarea[name]').forEach(el => {
            if (el.type === 'file') { if (el.files[0]) fd.append('file', el.files[0]); }
            else if (el.value.trim()) fd.append(el.name, el.value.trim());
          });
          const btn = e.currentTarget; btn.disabled = true;
          try { const r = await api.upload('/api/evidence', fd); toast(`채증 자료 등록 — 위반 의심 ${r.findings.length}건`); reload(); }
          catch (err) { toast(err.message, true); btn.disabled = false; }
        } }, '등록 및 스크리닝'))) : null,
      h('div', { class: 'panel' }, h('h2', {}, '채증 자료'),
        c.evidence.length ? h('table', {}, h('thead', {}, h('tr', {}, ...['#', '채증일', 'URL / 파일', '광고 문구', '무결성(SHA-256)', ''].map(t => h('th', {}, t)))),
          h('tbody', {}, ...c.evidence.map(e => h('tr', {},
            h('td', {}, e.id), h('td', { class: 'nowrap' }, e.captured_at),
            h('td', {}, e.url ? h('div', {}, h('a', { href: e.url, target: '_blank', rel: 'noopener noreferrer' }, e.url.slice(0, 50))) : null,
              e.file_name ? h('a', { href: `/api/evidence/${e.id}/file`, target: '_blank' }, `📎 ${e.file_name} (${bytes(e.size)})`) : null),
            h('td', { class: 'small' }, (e.ad_text || '-').slice(0, 160)),
            h('td', { class: 'small muted', title: e.sha256 || '' }, e.sha256 ? e.sha256.slice(0, 16) + '…' : '-'),
            h('td', {}, isAdmin() ? h('button', { class: 'small danger', onclick: async () => {
              if (!confirmBox('채증 자료를 삭제할까요? (삭제 기록은 감사로그에 남습니다)')) return;
              await api.del(`/api/evidence/${e.id}`); reload();
            } }, '삭제') : null))))) : empty('등록된 채증 자료가 없습니다.')),
      h('div', { class: 'panel' }, h('h2', {}, '광고규정 1차 스크리닝 결과'),
        h('p', { class: 'small muted' }, '규칙 기반 자동 분류입니다. 담당자가 [위반 소지 인정/해당 없음]을 판단하면 공문·회의자료에 인정된 항목만 반영됩니다.'),
        findingsList(c.findings.map(f => ({ ...f, refs: f.refs.map(r => ({ ...r, citation: `${r.article_no}${r.item}` })) })), { onDecide: decide })));
  }

  function analysis() {
    const out = h('div');
    const useAi = h('input', { type: 'checkbox', disabled: !meta.ai_available });
    const applyArticle = async (articleId, reason) => { await api.post(`/api/cases/${c.id}/articles`, { article_id: articleId, reason }); toast('적용 조문에 추가했습니다.'); reload(); };
    const linkPrec = async (pid) => { await api.post(`/api/cases/${c.id}/precedents`, { precedent_id: pid }); toast('참고 선례로 연결했습니다.'); reload(); };
    const run = async (btn) => {
      btn.disabled = true; mount(out, h('div', { class: 'muted' }, useAi.checked ? 'AI 분석 중… (최대 1~2분)' : '분석 중…'));
      try { const r = await api.post(`/api/cases/${c.id}/analyze`, { use_ai: useAi.checked }); mount(out, analysisView(r, { onApplyArticle: applyArticle, onLinkPrecedent: linkPrec })); }
      catch (e) { mount(out, h('div', { class: 'alert danger' }, e.message)); }
      finally { btn.disabled = false; }
    };
    return h('div', {},
      h('div', { class: 'panel' }, h('h2', {}, '적용 조문'),
        c.articles.length ? h('div', { class: 'card-list' }, ...c.articles.map(a => h('div', { class: 'item' },
          h('div', { class: 'head' }, h('b', {}, a.citation), h('span', { class: 'spacer' }),
            canEdit() ? h('button', { class: 'small', onclick: async () => { await api.del(`/api/cases/${c.id}/articles/${a.id}`); reload(); } }, '제외') : null),
          a.reason ? h('div', { class: 'small muted' }, a.reason) : null,
          h('details', {}, h('summary', {}, '원문'), h('div', { class: 'quote' }, a.body))))) : empty('아직 적용 조문이 없습니다. 아래 분석을 실행해 후보를 적용하세요.'),
        h('h3', {}, '참고 선례'),
        c.precedents.length ? h('div', {}, ...c.precedents.map(p => h('div', { class: 'row' }, `· ${p.title} → ${p.sanction_type || '-'}`,
          canEdit() ? h('button', { class: 'small', onclick: async () => { await api.del(`/api/cases/${c.id}/precedents/${p.id}`); reload(); } }, '제외') : null))) : empty('연결된 선례가 없습니다.')),
      h('div', { class: 'panel' }, h('h2', {}, '사실관계 → 조문·선례 매칭'),
        h('p', { class: 'small muted' }, '사실관계·채증 광고 문구를 바탕으로 등록된 법령·회규 원문과 선례 DB 안에서만 근거를 찾습니다.'),
        h('div', { class: 'row' }, h('label', { class: 'row', style: 'margin:0' }, useAi, ' AI 근거 제한 분석 포함', meta.ai_available ? '' : ' (API 키 미설정)'),
          h('button', { class: 'primary', onclick: (e) => run(e.currentTarget) }, '분석 실행')),
        out));
  }

  function documents() {
    return h('div', { class: 'panel' },
      h('div', { class: 'row' }, h('h2', { style: 'margin:0' }, '공문'), h('span', { class: 'spacer' }),
        canEdit() ? h('button', { class: 'primary', onclick: () => composeDocument({ caseId: c.id, defaultCode: suggestTemplate(c), onSaved: (did) => { reload(); openDocument(did, reload); } }) }, '+ 공문 자동 작성') : null),
      h('p', { class: 'small muted' }, '소명 요청부터 결과 통보까지 모든 절차는 공문 발송 기록으로 근거를 남깁니다(작성 → 결재 → 발송 기록).'),
      c.documents.length ? h('table', {}, h('thead', {}, h('tr', {}, ...['시행번호', '제목', '상태', '발송일', '작성일'].map(t => h('th', {}, t)))),
        h('tbody', {}, ...c.documents.map(d => h('tr', { class: 'clickable', onclick: () => openDocument(d.id, reload) },
          h('td', {}, d.doc_no || '-'), h('td', {}, d.subject), h('td', {}, badge(({ DRAFT: '초안', APPROVED: '결재 완료', SENT: '발송', CANCELLED: '취소' })[d.status], d.status)),
          h('td', {}, fmtDT(d.sent_at)), h('td', {}, fmtDT(d.created_at)))))) : empty('작성된 공문이 없습니다.'));
  }

  function history() {
    const note = textarea('note', '', { rows: 3, placeholder: '통화 내용, 추가 확인 사항 등' });
    return h('div', { class: 'panel' },
      canEdit() ? h('div', {}, field('처리 메모 추가', note), h('button', { style: 'margin-top:8px', onclick: async () => {
        if (!note.value.trim()) return; await api.post(`/api/cases/${c.id}/notes`, { note: note.value.trim() }); reload();
      } }, '메모 기록')) : null,
      h('h3', {}, '처리 경과 (삭제·수정 불가 기록)'),
      h('ul', { class: 'timeline' }, ...c.events.slice().reverse().map(e => h('li', { class: e.type },
        h('div', { class: 'small muted' }, `${fmtDT(e.ts)} · ${e.user_name || '-'} · ${({ CREATED: '접수', STATUS: '단계 변경', NOTE: '메모', DOC: '공문', MAIL: '발송', EVIDENCE: '채증', ARTICLE: '근거' })[e.type] || e.type}`),
        e.type === 'STATUS' ? h('div', { class: 'st' }, `${meta.statuses[e.from_status] || ''} → ${meta.statuses[e.to_status]}`) : null,
        e.note ? h('div', { style: 'white-space:pre-wrap' }, e.note) : null))));
  }

  render();
  mount(view, head, body);
}

function suggestTemplate(c) {
  return ({ RECEIVED: 'SUPPLEMENT_REQUEST', REVIEW: 'SUPPLEMENT_REQUEST', PENDING_APPROVAL: 'EXPLANATION_REQUEST', EXPLANATION_REQUESTED: 'EXPLANATION_REQUEST',
    EXPLANATION_REVIEW: 'CLOSURE_NOTICE', COMMITTEE: 'COMMITTEE_NOTICE', CORRECTION_ORDERED: 'CORRECTION_ORDER', DISCIPLINE: 'DISCIPLINE_REFERRAL',
    EXTERNAL: 'EXTERNAL_REFERRAL', CLOSED: 'COMPLAINANT_RESULT' })[c.status];
}

function transitionDialog(c, reload) {
  if (!c.allowed_transitions.length) { toast('변경 가능한 단계가 없습니다.', true); return; }
  const to = select('to', c.allowed_transitions.map(t => [t.to, t.label]), c.allowed_transitions[0].to);
  const hint = h('div', { class: 'small muted' });
  const note = textarea('note', '', { rows: 3 });
  const due = input('due_date', '', { type: 'date' });
  const dueWrap = field('기한 (비우면 기본값 적용: 소명 14일 / 시정 30일)', due);
  const upd = () => {
    const t = c.allowed_transitions.find(x => x.to === to.value);
    mount(hint, t.note_required ? `필수 기재: ${t.note_required}` : '사유는 선택 입력입니다.');
    dueWrap.style.display = ['EXPLANATION_REQUESTED', 'CORRECTION_ORDERED', 'DISCIPLINE'].includes(to.value) ? '' : 'none';
    dueWrap.querySelector('label').textContent = to.value === 'DISCIPLINE' ? '이의신청 기한 (징계결정서 송달일 + 30일)' : '기한 (비우면 기본값 적용: 소명 14일 / 시정 30일)';
  };
  to.addEventListener('change', upd);
  const b = h('div', {}, h('p', {}, `현재 단계: `, h('b', {}, c.status_label)), field('변경할 단계', to), hint, field('사유·근거 (처리 경과에 영구 기록)', note), dueWrap);
  upd();
  modal('처리 단계 변경', b, { actions: [{ label: '변경', primary: true, onClick: async () => {
    await api.post(`/api/cases/${c.id}/transition`, { to: to.value, note: note.value.trim() || null, due_date: due.value || null });
    toast('단계가 변경되었습니다.'); reload();
  } }] });
}
