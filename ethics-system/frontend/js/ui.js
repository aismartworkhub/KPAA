// DOM 헬퍼 — 모든 텍스트는 textContent 로 넣어 XSS를 차단한다.
export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === 'class') el.className = v;
    else if (k === 'style') el.style.cssText = v;
    else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
    else if (k === 'value') el.value = v;
    else if (k === 'checked') el.checked = !!v;
    else if (k === 'selected') el.selected = !!v;
    else if (k === 'disabled') el.disabled = !!v;
    else el.setAttribute(k, v === true ? '' : v);
  }
  append(el, children);
  return el;
}
function append(el, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}
export function clear(el) { while (el.firstChild) el.removeChild(el.firstChild); return el; }
export function mount(el, ...children) { clear(el); append(el, children); return el; }

export function toast(msg, err = false) {
  const box = document.getElementById('toast');
  const t = h('div', { class: 't' + (err ? ' err' : '') }, msg);
  box.append(t);
  setTimeout(() => t.remove(), err ? 6000 : 3000);
}

export function modal(title, body, { wide = false, actions = [] } = {}) {
  const back = h('div', { class: 'modal-back' });
  const close = () => back.remove();
  const foot = h('div', { class: 'foot' },
    ...actions.map(a => h('button', { class: a.primary ? 'primary' : (a.danger ? 'danger' : ''), onclick: async (e) => {
      const btn = e.currentTarget; btn.disabled = true;
      try { const r = await a.onClick(close); if (r !== false && a.close !== false) close(); }
      catch (err) { toast(err.message, true); }
      finally { btn.disabled = false; }
    } }, a.label)),
    h('button', { onclick: close }, '닫기'));
  const box = h('div', { class: 'modal' + (wide ? ' wide' : '') }, h('h2', {}, title), body, foot);
  back.append(box);
  back.addEventListener('mousedown', (e) => { if (e.target === back) close(); });
  document.body.append(back);
  return { close, box };
}

export function field(label, input, cls = '') {
  return h('div', { class: cls }, h('label', {}, label), input);
}
export function input(name, value = '', attrs = {}) { return h('input', { name, value: value ?? '', ...attrs }); }
export function textarea(name, value = '', attrs = {}) { const t = h('textarea', { name, ...attrs }); t.value = value ?? ''; return t; }
export function select(name, options, value, attrs = {}) {
  // options: [[value, label], ...]
  return h('select', { name, ...attrs }, ...options.map(([v, l]) => h('option', { value: v, selected: String(v) === String(value ?? '') }, l)));
}
export function formData(root) {
  const out = {};
  root.querySelectorAll('input[name], select[name], textarea[name]').forEach(el => {
    if (el.type === 'checkbox') out[el.name] = el.checked;
    else if (el.type === 'file') return;
    else out[el.name] = el.value.trim() === '' ? null : el.value.trim();
  });
  return out;
}
export function badge(text, cls = '') { return h('span', { class: `badge ${cls}` }, text); }
export function fmtDate(s) { return s ? String(s).slice(0, 10) : '-'; }
export function fmtDT(s) { return s ? String(s).slice(0, 16).replace('T', ' ') : '-'; }
export function bytes(n) { if (n == null) return '-'; if (n < 1024) return `${n} B`; if (n < 1048576) return `${(n / 1024).toFixed(1)} KB`; return `${(n / 1048576).toFixed(1)} MB`; }
export function empty(msg) { return h('div', { class: 'empty' }, msg); }
export function confirmBox(msg) { return window.confirm(msg); }

// 공문 본문에서 {{확인 필요: …}} 를 강조 표시
export function docView(text) {
  const pre = h('pre', { class: 'doc' });
  const parts = String(text || '').split(/(\{\{확인 필요: [^}]+\}\})/);
  parts.forEach(p => pre.append(p.startsWith('{{확인 필요') ? h('span', { class: 'miss' }, p) : document.createTextNode(p)));
  return pre;
}

export function tabs(defs, onChange, active) {
  const bar = h('div', { class: 'tabs' });
  defs.forEach(([key, label]) => bar.append(h('button', { class: key === active ? 'active' : '', onclick: () => onChange(key) }, label)));
  return bar;
}
