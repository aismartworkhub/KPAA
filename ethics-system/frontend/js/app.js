import { api, setCsrf } from './api.js';
import { h, mount, toast, field, input } from './ui.js';
import { state } from './state.js';
import dashboard from './views/dashboard.js';
import cases from './views/cases.js';
import caseDetail from './views/caseDetail.js';
import monitoring from './views/monitoring.js';
import regs from './views/regs.js';
import precedents from './views/precedents.js';
import documents from './views/documents.js';
import meetings from './views/meetings.js';
import meetingDetail from './views/meetingDetail.js';
import admin from './views/admin.js';

const NAV = [
  ['#/', '대시보드'],
  ['#/cases', '사건 관리'],
  ['#/monitoring', '광고 모니터링'],
  ['#/regs', '규정·근거 매칭'],
  ['#/precedents', '징계 선례·사례집'],
  ['#/documents', '공문 관리'],
  ['#/meetings', '위원회 회의'],
  ['#/admin', '관리'],
];

const ROUTES = [
  [/^#\/?$/, dashboard],
  [/^#\/cases$/, cases],
  [/^#\/cases\/(\d+)$/, caseDetail],
  [/^#\/monitoring$/, monitoring],
  [/^#\/regs$/, regs],
  [/^#\/precedents$/, precedents],
  [/^#\/documents$/, documents],
  [/^#\/meetings$/, meetings],
  [/^#\/meetings\/(\d+)$/, meetingDetail],
  [/^#\/admin$/, admin],
];

const root = document.getElementById('app');

async function loadMeta() {
  state.meta = await api.get('/api/meta');
}

function layout() {
  const content = h('div', { class: 'content', id: 'view' });
  const nav = h('nav', { class: 'sidebar' },
    h('div', { class: 'logo' }, '윤리·징계·광고', h('small', {}, '대한변리사회 회원서비스실')),
    ...NAV.map(([href, label]) => h('a', { href, 'data-href': href }, label)));
  const top = h('div', { class: 'topbar' },
    h('div', { class: 'muted small' }, state.meta?.ai_available ? 'AI 보조: 사용 가능(근거 제한 모드)' : 'AI 보조: 미설정 — 규칙·검색 기능으로 동작'),
    h('div', { class: 'row' },
      h('span', { class: 'who' }, `${state.user.name} (${({ admin: '관리자', staff: '담당자', viewer: '조회' })[state.user.role]})`),
      h('button', { class: 'small', onclick: changePasswordDialog }, '비밀번호 변경'),
      h('button', { class: 'small', onclick: logout }, '로그아웃')));
  mount(root, h('div', { class: 'layout' }, nav, h('div', { class: 'main' }, top, content)));
}

function highlightNav() {
  const hash = (location.hash || '#/').split('?')[0];
  document.querySelectorAll('.sidebar a').forEach(a => {
    const href = a.dataset.href;
    a.classList.toggle('active', href === '#/' ? (hash === '#/' || hash === '#') : hash.startsWith(href));
  });
}

async function route() {
  if (!state.user) return;
  if (!document.getElementById('view')) layout();
  highlightNav();
  const hash = (location.hash || '#/').split('?')[0];
  const view = document.getElementById('view');
  for (const [re, fn] of ROUTES) {
    const m = hash.match(re);
    if (m) {
      mount(view, h('div', { class: 'muted' }, '불러오는 중…'));
      try { await fn(view, ...m.slice(1)); }
      catch (e) { mount(view, h('div', { class: 'alert danger' }, e.message)); }
      window.scrollTo(0, 0);
      return;
    }
  }
  mount(view, h('div', { class: 'alert warn' }, '페이지를 찾을 수 없습니다.'));
}

function loginView(msg) {
  const user = input('username', '', { autocomplete: 'username', required: true });
  const pw = input('password', '', { type: 'password', autocomplete: 'current-password', required: true });
  const err = h('div');
  const form = h('form', { class: 'login', onsubmit: async (e) => {
    e.preventDefault();
    try {
      const r = await api.post('/api/auth/login', { username: user.value.trim(), password: pw.value });
      setCsrf(r.csrf_token); state.user = r.user;
      await start();
    } catch (ex) { mount(err, h('div', { class: 'alert danger' }, ex.message)); }
  } },
    h('h1', {}, '윤리·징계·광고 업무지원 시스템'),
    h('p', {}, '대한변리사회 회원서비스실'),
    msg ? h('div', { class: 'alert warn' }, msg) : null,
    field('아이디', user), field('비밀번호', pw), err,
    h('div', { style: 'margin-top:14px' }, h('button', { class: 'primary', type: 'submit', style: 'width:100%;justify-content:center' }, '로그인')),
    h('p', { class: 'small', style: 'margin-top:14px' }, '사건·민원 정보는 비공개 자료입니다. 업무 목적 외 열람·반출을 금합니다.'));
  mount(root, h('div', { class: 'login-wrap' }, form));
  user.focus();
}

function changePasswordDialog(forced = false) {
  const cur = input('current', '', { type: 'password', autocomplete: 'current-password' });
  const nw = input('new', '', { type: 'password', autocomplete: 'new-password' });
  const nw2 = input('new2', '', { type: 'password', autocomplete: 'new-password' });
  import('./ui.js').then(({ modal }) => {
    modal(forced === true ? '최초 로그인 — 비밀번호 변경 필요' : '비밀번호 변경', h('div', {},
      forced === true ? h('div', { class: 'alert warn' }, '초기 비밀번호를 사용 중입니다. 계속하려면 비밀번호를 변경하세요.') : null,
      field('현재 비밀번호', cur), field('새 비밀번호 (10자 이상, 영문·숫자·특수문자 중 2종 이상)', nw), field('새 비밀번호 확인', nw2)),
    { actions: [{ label: '변경', primary: true, onClick: async () => {
      if (nw.value !== nw2.value) throw new Error('새 비밀번호가 서로 다릅니다.');
      await api.post('/api/auth/password', { current_password: cur.value, new_password: nw.value });
      state.user.must_change_pw = 0; toast('비밀번호가 변경되었습니다.');
    } }] });
  });
}

async function logout() {
  try { await api.post('/api/auth/logout'); } catch {}
  state.user = null; loginView();
}

async function start() {
  await loadMeta();
  layout();
  await route();
  if (state.user.must_change_pw) changePasswordDialog(true);
}

window.addEventListener('hashchange', route);
window.addEventListener('auth-expired', () => { if (state.user) { state.user = null; loginView('세션이 만료되었습니다. 다시 로그인하세요.'); } });
window.addEventListener('meta-changed', loadMeta);

(async () => {
  try {
    const r = await api.get('/api/auth/me');
    setCsrf(r.csrf_token); state.user = r.user;
    await start();
  } catch { loginView(); }
})();
