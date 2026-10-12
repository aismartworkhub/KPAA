import { api, qs } from '../api.js';
import { h, mount, badge, fmtDT, empty, modal, field, input, select, textarea, toast, docView, confirmBox } from '../ui.js';
import { canEdit } from '../state.js';

const ST = { DRAFT: '초안', APPROVED: '결재 완료', SENT: '발송', CANCELLED: '취소' };

export async function openDocument(id, onChange) {
  const d = await api.get(`/api/documents/${id}`);
  const editable = canEdit() && d.status === 'DRAFT';
  const docNo = input('doc_no', d.doc_no, { disabled: !editable, placeholder: '대한변리사회-0000' });
  const subj = input('subject', d.subject, { disabled: !editable });
  const recip = input('recipient', d.recipient, { disabled: !editable });
  const email = input('recipient_email', d.recipient_email, { disabled: !editable, type: 'email' });
  const body = textarea('body', d.body, { rows: 22, class: 'mono', disabled: !editable });
  const pv = h('div', {}, docView(d.body));
  body.addEventListener('input', () => mount(pv, docView(body.value)));
  const info = h('div', { class: 'row small muted' }, badge(ST[d.status], d.status),
    d.approved_at ? `결재 ${fmtDT(d.approved_at)} (${d.approver_note})` : null,
    d.sent_at ? `· 발송 ${fmtDT(d.sent_at)} / ${d.sent_via === 'SMTP' ? '메일 자동' : '수동 기록'} / 근거 ${d.sent_ref}` : null);
  const missing = d.missing.length ? h('div', { class: 'alert warn' }, `확인 필요 항목 ${d.missing.length}건이 남아 있어 결재할 수 없습니다: ${[...new Set(d.missing)].join(', ')}`) : null;
  const actions = [];
  if (editable) {
    actions.push({ label: '수정 저장', onClick: async () => {
      await api.put(`/api/documents/${id}`, { doc_no: docNo.value || null, subject: subj.value, recipient: recip.value || null, recipient_email: email.value || null, body: body.value });
      toast('저장되었습니다.'); onChange?.(); return false;
    } });
    actions.push({ label: '결재 완료 처리', primary: true, onClick: async (close) => {
      await api.put(`/api/documents/${id}`, { doc_no: docNo.value || null, subject: subj.value, recipient: recip.value || null, recipient_email: email.value || null, body: body.value });
      const note = prompt('결재권자와 결재일을 입력하세요 (예: 담당 이사 홍길동, 2026-10-12 전자결재)');
      if (!note) return false;
      await api.post(`/api/documents/${id}/approve`, { note });
      toast('결재 완료로 기록했습니다.'); onChange?.(); close(); openDocument(id, onChange); return false;
    } });
  }
  if (canEdit() && d.status === 'APPROVED') {
    actions.push({ label: '발송 기록', primary: true, onClick: async (close) => { sendDialog(d, () => { onChange?.(); close(); openDocument(id, onChange); }); return false; } });
  }
  if (canEdit() && (d.status === 'DRAFT' || d.status === 'APPROVED')) {
    actions.push({ label: '취소', danger: true, onClick: async () => {
      if (!confirmBox('이 공문을 취소 처리할까요?')) return false;
      await api.post(`/api/documents/${id}/cancel`); onChange?.();
    } });
  }
  actions.push({ label: '.docx 내려받기', onClick: async () => { await api.download(`/api/documents/${id}/docx`, 'document.docx'); return false; } });
  modal(`공문 — ${d.subject}`, h('div', {}, info, missing,
    h('div', { class: 'form-grid' }, field('시행번호', docNo), field('수신 메일', email), field('제목', subj, 'full'), field('수신(표시)', recip, 'full')),
    editable ? field('본문', body) : null,
    h('h3', {}, '미리보기'), pv), { wide: true, actions });
}

function sendDialog(d, done) {
  const method = select('method', [['MANUAL', '그룹웨어 등으로 발송 후 기록'], ['SMTP', d.smtp_configured ? '시스템에서 메일 발송(.docx 첨부)' : '시스템 메일 발송 (SMTP 미설정)']], 'MANUAL');
  const sentAt = input('sent_at', new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16), { type: 'datetime-local' });
  const ref = input('sent_ref', '', { placeholder: '발송 메일 제목·Message-ID·등기번호 등' });
  const manual = h('div', {}, field('실제 발송 일시', sentAt), field('발송 근거', ref));
  method.addEventListener('change', () => { manual.style.display = method.value === 'MANUAL' ? '' : 'none'; });
  modal('발송 기록', h('div', {},
    h('p', { class: 'small muted' }, '징계 등 불이익 처분의 근거가 되므로 실제 발송 내역을 정확히 기록하세요. 기록 후에는 수정할 수 없습니다.'),
    h('div', {}, `수신: ${d.recipient || '-'} <${d.recipient_email || '메일 없음'}>`),
    field('발송 방법', method), manual), { actions: [{ label: '기록', primary: true, onClick: async () => {
      if (method.value === 'SMTP' && !d.smtp_configured) throw new Error('SMTP가 설정되지 않았습니다. 관리자에게 문의하거나 수동 기록을 사용하세요.');
      await api.post(`/api/documents/${d.id}/send`, { method: method.value, sent_at: sentAt.value ? sentAt.value.replace('T', ' ') + ':00' : null, sent_ref: ref.value || null });
      toast('발송이 기록되었습니다.'); done();
    } }] });
}

export default async function documents(view) {
  const p = Object.fromEntries(new URLSearchParams(location.hash.split('?')[1] || ''));
  const list = await api.get('/api/documents' + qs({ status: p.status }));
  const reload = () => documents(view);
  mount(view,
    h('div', { class: 'page-head' }, h('div', {}, h('h1', {}, '공문 관리'), h('p', {}, '자동 작성된 공문의 결재·발송 기록을 관리합니다. 새 공문은 사건 화면 또는 위원회 화면에서 작성합니다.'))),
    h('div', { class: 'panel row' }, ...[['', '전체'], ['DRAFT', '초안'], ['APPROVED', '결재 완료(미발송)'], ['SENT', '발송'], ['CANCELLED', '취소']].map(([v, l]) =>
      h('a', { class: 'btn small' + ((p.status || '') === v ? ' primary' : ''), href: '#/documents' + qs({ status: v }) }, l))),
    h('div', { class: 'panel', style: 'padding:0;overflow-x:auto' }, list.length ? h('table', {},
      h('thead', {}, h('tr', {}, ...['시행번호', '사건', '제목', '수신', '상태', '발송', '작성'].map(t => h('th', {}, t)))),
      h('tbody', {}, ...list.map(d => h('tr', { class: 'clickable', onclick: () => openDocument(d.id, reload) },
        h('td', {}, d.doc_no || '-'), h('td', { class: 'nowrap' }, d.case_no || (d.meeting_id ? '위원회' : '-')), h('td', {}, d.subject), h('td', {}, d.recipient || '-'),
        h('td', {}, badge(ST[d.status], d.status)), h('td', { class: 'nowrap' }, fmtDT(d.sent_at)), h('td', { class: 'nowrap' }, fmtDT(d.created_at))))))
      : empty('공문이 없습니다.')));
}
