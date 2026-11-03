// Apps Script 코드 검증용 모의 실행기 (구글 서버 없이 핵심 로직 확인)
// 실행: node appscript/tests/gas_mock_test.mjs
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import assert from 'node:assert/strict';

const here = path.dirname(new URL(import.meta.url).pathname);
const code = fs.readFileSync(path.join(here, '../code/회원업무_전체코드.gs'), 'utf8');
const first = fs.readFileSync(path.join(here, '../code/01_첫자동화.gs'), 'utf8');
const fixture = JSON.parse(fs.readFileSync(path.join(here, 'practice_fixture.json'), 'utf8'));

function makeEnv(data) {
  const sent = [], alerts = [], menus = [];
  let confirmAnswer = 'YES';
  class Range {
    constructor(sh, r, c, nr = 1, nc = 1) { Object.assign(this, { sh, r, c, nr, nc }); }
    _cells(fn) { for (let i = 0; i < this.nr; i++) for (let j = 0; j < this.nc; j++) fn(this.r - 1 + i, this.c - 1 + j, i, j); }
    getValues() { const out = []; for (let i = 0; i < this.nr; i++) { const row = []; for (let j = 0; j < this.nc; j++) row.push(this.sh._get(this.r - 1 + i, this.c - 1 + j)); out.push(row); } return out; }
    getValue() { return this.getValues()[0][0]; }
    setValues(v) { assert.equal(v.length, this.nr, 'setValues 행 수 불일치'); v.forEach(row => assert.equal(row.length, this.nc, 'setValues 열 수 불일치')); this._cells((r, c, i, j) => this.sh._set(r, c, v[i][j])); return this; }
    setValue(v) { this._cells((r, c) => this.sh._set(r, c, v)); return this; }
    setBackgrounds(b) { assert.equal(b.length, this.nr); this._cells((r, c, i, j) => { this.sh.bg[`${r},${c}`] = b[i][j]; }); return this; }
    setBackground(b) { this._cells((r, c) => { this.sh.bg[`${r},${c}`] = b; }); return this; }
    setFontWeight() { return this; }
    setNumberFormat() { return this; }
    insertCheckboxes() { this._cells((r, c) => { this.sh.checkbox.add(`${r},${c}`); }); return this; }
  }
  class Sheet {
    constructor(name, rows = []) { this.name = name; this.rows = rows.map(r => [...r]); this.bg = {}; this.checkbox = new Set(); this.charts = []; this.frozen = 0; }
    _get(r, c) { const v = this.rows[r]?.[c]; return v === undefined || v === null ? '' : v; }
    _set(r, c, v) { while (this.rows.length <= r) this.rows.push([]); this.rows[r][c] = v; }
    getName() { return this.name; }
    getLastRow() { let n = 0; this.rows.forEach((row, i) => { if (row.some(v => v !== '' && v !== null && v !== undefined)) n = i + 1; }); return n; }
    getLastColumn() { let n = 0; this.rows.forEach(row => row.forEach((v, j) => { if (v !== '' && v !== null && v !== undefined) n = Math.max(n, j + 1); })); return n; }
    getRange(r, c, nr = 1, nc = 1) { assert.ok(r >= 1 && c >= 1 && nr >= 1 && nc >= 1, `잘못된 범위 ${r},${c},${nr},${nc}`); return new Range(this, r, c, nr, nc); }
    getDataRange() { return new Range(this, 1, 1, Math.max(1, this.getLastRow()), Math.max(1, this.getLastColumn())); }
    clear() { this.rows = []; this.bg = {}; this.checkbox = new Set(); return this; }
    setFrozenRows(n) { this.frozen = n; }
    appendRow(row) { this.rows.splice(this.getLastRow(), 0, [...row]); return this; }
    getCharts() { return [...this.charts]; }
    removeChart(ch) { this.charts = this.charts.filter(x => x !== ch); }
    insertChart(ch) { this.charts.push(ch); }
    newChart() { const spec = {}; const b = { setChartType: t => (spec.type = t, b), addRange: r => (spec.range = r, b), setPosition: () => b, setOption: (k, v) => (spec[k] = v, b), build: () => spec }; return b; }
  }
  const sheets = Object.fromEntries(Object.entries(data).map(([k, v]) => [k, new Sheet(k, v)]));
  let active = sheets['추천신청'];
  const ss = {
    getSheetByName: n => sheets[n] || null,
    insertSheet: n => (sheets[n] = new Sheet(n)),
    getActiveSheet: () => active,
  };
  const ui = {
    alert: (...a) => { alerts.push(a.length === 1 ? a[0] : a[1]); return a.length > 1 ? (confirmAnswer === 'YES' ? 'YES' : 'NO') : 'OK'; },
    ButtonSet: { YES_NO: 'YES_NO' }, Button: { YES: 'YES', NO: 'NO' },
    createMenu: (title) => { const m = { title, items: [], addItem: (l, f) => (m.items.push([l, f]), m), addSeparator: () => m, addToUi: () => menus.push(m) }; return m; },
    showSidebar: (h) => alerts.push('SIDEBAR:' + h.title),
  };
  const ctx = {
    SpreadsheetApp: { getActiveSpreadsheet: () => ss, getUi: () => ui },
    MailApp: { sendEmail: (o) => { if (/fail/.test(o.to)) throw new Error('mock failure'); sent.push(o); }, getRemainingDailyQuota: () => ctx._quota },
    Session: { getScriptTimeZone: () => 'Asia/Seoul', getEffectiveUser: () => ({ getEmail: () => 'me@example.com' }) },
    Utilities: { formatDate: (d, tz, f) => f.replace('yyyy', '2026').replace('MM', '11').replace('dd', '04').replace('HH', '15').replace('mm', '00').replace('ss', '00') },
    HtmlService: { createHtmlOutputFromFile: (f) => ({ setTitle: t => ({ title: t, file: f }) }) },
    Charts: { ChartType: { BAR: 'BAR' } },
    _quota: 100,
  };
  vm.createContext(ctx);
  return { ctx, sheets, sent, alerts, menus, setConfirm: v => (confirmAnswer = v), setActive: s => (active = s) };
}

let passed = 0;
function test(name, fn) { try { fn(); passed++; console.log('OK  ', name); } catch (e) { console.log('FAIL', name, '\n   ', e.message); process.exitCode = 1; } }
const clone = () => JSON.parse(JSON.stringify(fixture));

test('1단계: 메뉴 생성 + 오늘 날짜 넣기', () => {
  const env = makeEnv(clone());
  vm.runInContext(first, env.ctx);
  env.ctx.onOpen();
  assert.equal(env.menus[0].items[0][1], 'addTodayDate');
  env.sheets['추천신청'].getActiveCell = () => env.sheets['추천신청'].getRange(40, 1);
  env.ctx.addTodayDate();
  assert.equal(env.sheets['추천신청'].rows[39][0], '2026-11-04');
});

const env = makeEnv(clone());
vm.runInContext(code, env.ctx);
const A = env.sheets['추천신청'];
const H = () => A.rows[0];
const col = n => H().indexOf(n);

test('전체 코드: 메뉴 항목의 함수가 모두 존재', () => {
  env.ctx.onOpen();
  for (const [, fn] of env.menus[0].items) assert.equal(typeof env.ctx[fn], 'function', fn);
});

test('Panel.html 버튼이 부르는 함수가 모두 존재(내부용 _ 아님)', () => {
  const html = fs.readFileSync(path.join(here, '../code/Panel.html'), 'utf8');
  const names = [...html.matchAll(/run\('(\w+)'/g)].map(m => m[1]).concat(['countMailTargets']);
  for (const n of names) { assert.equal(typeof env.ctx[n], 'function', n); assert.ok(!n.endsWith('_')); }
});

test('중복 확인: 열 자동 추가·체크박스·중복 표시', () => {
  const msg = env.ctx.checkDuplicates();
  for (const c of ['선정', '비고', '발송상태', '발송일시']) assert.ok(col(c) >= 0, c + ' 열 없음');
  assert.match(msg, /중복 신청자 4명/);
  const notes = A.rows.slice(1).map(r => r[col('비고')]).filter(Boolean);
  assert.equal(notes.length, 8);
  assert.equal(notes.filter(n => n.startsWith('동일 기관')).length, 2);
  assert.ok(A.checkbox.size === A.getLastRow() - 1, '체크박스 수');
  assert.equal(A.rows[1][col('선정')], false);
});

test('중복 확인 재실행: 비고·색이 갱신되고 누적되지 않음', () => {
  env.ctx.checkDuplicates();
  const notes = A.rows.slice(1).map(r => r[col('비고')]).filter(Boolean);
  assert.equal(notes.length, 8);
  assert.equal(H().filter(h => h === '비고').length, 1);
});

test('메일: 대상 없으면 안내', () => {
  assert.match(env.ctx.sendTestMail(), /대상이 없습니다/);
});

test('메일: 시험 발송은 나에게만, 상태 변경 없음', () => {
  [2, 3, 4].forEach(r => { A.rows[r - 1][col('선정')] = true; });
  A.rows[4][col('선정')] = true; A.rows[4][col('이메일')] = 'not-an-email'; // 5행: 형식 오류
  A.rows[5][col('선정')] = true; A.rows[5][col('이메일')] = 'fail@example.com'; // 6행: 발송 실패
  const msg = env.ctx.sendTestMail();
  assert.equal(env.sent.length, 1);
  assert.equal(env.sent[0].to, 'me@example.com');
  assert.match(env.sent[0].subject, /^\[시험\] \[대한변리사회\] .+ 추천 선정 안내$/);
  assert.match(env.sent[0].body, /회원님께/);
  assert.ok(!/\{성명\}/.test(env.sent[0].body), '치환 안 됨');
  assert.match(msg, /실제 대상: 5명/);
  assert.equal(A.rows[1][col('발송상태')] || '', '');
});

test('메일: 한도 초과 시 발송 안 함', () => {
  env.ctx._quota = 2;
  assert.match(env.ctx.sendSelectedMails(), /한도/);
  assert.equal(env.sent.length, 1);
  env.ctx._quota = 100;
});

test('메일: 실제 발송 — 성공·형식오류·실패 기록, 이력 탭', () => {
  const msg = env.ctx.sendSelectedMails();
  assert.match(msg, /발송 완료 3건, 실패 2건/);
  assert.equal(env.sent.length, 4);
  assert.equal(A.rows[1][col('발송상태')], '발송완료');
  assert.equal(A.rows[4][col('발송상태')], '실패: 이메일 형식 오류');
  assert.match(A.rows[5][col('발송상태')], /^실패: mock failure/);
  assert.equal(A.rows[1][col('발송일시')], '2026-11-04 15:00:00');
  const log = env.sheets['발송이력'];
  assert.equal(log.rows[0][0], '발송일시');
  assert.equal(log.getLastRow(), 6);
});

test('메일: 재실행 시 발송완료 건은 다시 보내지 않음', () => {
  const before = env.sent.length;
  env.ctx.sendSelectedMails();
  assert.equal(env.sent.length - before, 0, '실패 건만 재시도 대상'); // 실패 2건은 주소가 그대로라 다시 실패
});

test('메뉴 실제 발송: 아니오 선택 시 취소', () => {
  A.rows[7][col('선정')] = true;
  env.setConfirm('NO');
  const before = env.sent.length;
  env.ctx.menuSendSelectedMails();
  assert.equal(env.sent.length, before);
  assert.match(env.alerts.at(-1), /취소/);
  env.setConfirm('YES');
});

test('미선정자 목록', () => {
  const msg = env.ctx.listUnselected();
  const n = A.getLastRow() - 1 - A.rows.slice(1).filter(r => r[col('선정')] === true).length;
  assert.match(msg, new RegExp(`미선정자 ${n}명`));
  assert.equal(env.sheets['미선정자'].getLastRow(), n + 1);
});

test('통합 현황: 제목행 건너뛰기, 변리사 열 인식, 이미 채운 사람 제외', () => {
  const msg = env.ctx.buildStatus();
  const st = env.sheets['통합현황'];
  const h = st.rows[0];
  const rows = st.rows.slice(1).filter(r => r.length);
  // 기대값 직접 계산
  const reg = v => String(Number(v));
  const tr = new Set(fixture['연수'].slice(2).map(r => reg(r[1])));
  const pb = new Set(fixture['공익'].slice(2).filter(r => Math.max(0, r[3] - r[4]) > 0).map(r => reg(r[2])));
  const fee = new Set(fixture['회비'].slice(1).map(r => reg(r[0])));
  const union = new Set([...tr, ...pb, ...fee]);
  assert.equal(rows.length, union.size);
  const two = [...union].filter(k => (tr.has(k) + pb.has(k) + fee.has(k)) >= 2).length;
  assert.match(msg, new RegExp(`대상 ${union.size}명 \\(2개 이상 ${two}명\\)`));
  // 정렬: 해당 항목 수 내림차순
  const cnt = rows.map(r => r[h.indexOf('해당 항목 수')]);
  assert.deepEqual(cnt, [...cnt].sort((a, b) => b - a));
  // 사무소 공백 제거
  assert.ok(rows.every(r => !String(r[2]).endsWith(' ')));
  // 공익 충족자는 없어야 함
  const satisfied = fixture['공익'].slice(2).filter(r => r[3] - r[4] <= 0).map(r => reg(r[2]));
  for (const s of satisfied) { const row = rows.find(r => String(r[0]) === s); if (row) assert.equal(row[h.indexOf('공익 부족시간')], ''); }
  const board = env.sheets['현황보드'];
  assert.equal(board.rows[1][1], union.size);
  assert.equal(board.charts.length, 1);
  assert.equal(board.charts[0].range.r, 3);
});

test('통합 현황 재실행: 지난번 대비 해소·신규 계산, 차트 중복 없음', () => {
  // 회비 1명 납부 처리(삭제) + 새 미납자 추가
  const fe = env.sheets['회비'];
  const removed = String(fe.rows[1][0]);
  fe.rows.splice(1, 1);
  fe.rows.push([99999, '신*규', 300000, '2026-11-15']);
  env.ctx.buildStatus();
  const st = env.sheets['통합현황'];
  const h = st.rows[0];
  const newRow = st.rows.find(r => String(r[0]) === '99999');
  assert.equal(newRow[h.indexOf('지난번 대비')], '신규');
  const board = env.sheets['현황보드'];
  const resolvedRow = board.rows.find(r => r[0] === '지난번 대비 해소');
  const stillThere = st.rows.some(r => String(r[0]) === removed);
  assert.equal(resolvedRow[1], stillThere ? 0 : 1);
  assert.equal(board.charts.length, 1);
});

test('필수 열 없으면 알기 쉬운 오류', () => {
  const e2 = makeEnv({ 추천신청: [['타임스탬프', '성명', '이메일']], 메일양식: [] });
  vm.runInContext(code, e2.ctx);
  assert.throws(() => e2.ctx.checkDuplicates(), /\[등록번호\] 열이 필요합니다/);
  const e3 = makeEnv({ 공익: [['차수', '성명', '번호', '의무시간', '수행시간'], ['3차', 'a', 1, 2, 0]] });
  vm.runInContext(code, e3.ctx);
  assert.throws(() => e3.ctx.buildStatus(), /\[등록번호 또는 변리사\] 열이 필요합니다/);
  const e4 = makeEnv({});
  vm.runInContext(code, e4.ctx);
  assert.match(e4.ctx.buildStatus(), /하나도 없습니다/);
});

test('작업 패널 열기', () => {
  env.ctx.openPanel();
  assert.equal(env.alerts.at(-1), 'SIDEBAR:회원업무 패널');
});

console.log(`\n${passed} passed`);
