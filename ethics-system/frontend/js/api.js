// API 호출 래퍼 — 세션 쿠키 + CSRF 헤더, 오류 메시지 표준화
let csrf = null;
export function setCsrf(t) { csrf = t; }

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

async function request(method, url, body, { form = false, raw = false } = {}) {
  const opts = { method, credentials: 'same-origin', headers: {} };
  if (method !== 'GET' && csrf) opts.headers['X-CSRF-Token'] = csrf;
  if (body !== undefined) {
    if (form) opts.body = body;
    else { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
  }
  let res;
  try { res = await fetch(url, opts); }
  catch { throw new ApiError(0, '서버에 연결할 수 없습니다. 네트워크를 확인하세요.'); }
  if (res.status === 401 && !url.endsWith('/auth/login') && !url.endsWith('/auth/me')) {
    window.dispatchEvent(new CustomEvent('auth-expired'));
  }
  if (!res.ok) {
    let msg = `요청 실패 (${res.status})`;
    try { const j = await res.json(); if (j.detail) msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail); } catch {}
    throw new ApiError(res.status, msg);
  }
  if (raw) return res;
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

export const api = {
  get: (u) => request('GET', u),
  post: (u, b) => request('POST', u, b ?? {}),
  put: (u, b) => request('PUT', u, b),
  patch: (u, b) => request('PATCH', u, b),
  del: (u) => request('DELETE', u),
  upload: (u, formData) => request('POST', u, formData, { form: true }),
  async download(u, fallbackName) {
    const res = await request('GET', u, undefined, { raw: true });
    const blob = await res.blob();
    const cd = res.headers.get('content-disposition') || '';
    const m = cd.match(/filename\*=UTF-8''([^;]+)/) || cd.match(/filename="?([^";]+)"?/);
    const name = m ? decodeURIComponent(m[1]) : fallbackName;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  },
};

export function qs(params) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== null && v !== '') p.set(k, v); });
  const s = p.toString();
  return s ? `?${s}` : '';
}
