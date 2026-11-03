/**
 * 회원업무 자동화 — 전체 코드 (2단계부터 사용)
 * ─────────────────────────────────────────────
 * 붙여넣는 곳: 확장 프로그램 > Apps Script > Code.gs
 *             (1단계 코드를 모두 지우고 이 코드 전체를 붙여넣기)
 *
 * 시트(탭) 이름은 아래 SHEET 에서 바꿀 수 있습니다.
 * 개인정보는 이 시트 안에서만 처리되며, 외부(AI 등)로 보내지 않습니다.
 */

const SHEET = {
  APPLY: '추천신청',   // 구글폼 응답 시트 (이름이 다르면 여기만 바꾸세요)
  TEMPLATE: '메일양식', // A1: 제목 / B1: 제목 내용, A2: 본문 / B2: 본문 내용
  LOG: '발송이력',
  UNSELECTED: '미선정자',
  TRAINING: '연수',
  PUBLIC: '공익',
  FEE: '회비',
  STATUS: '통합현황',
  BOARD: '현황보드',
};
const SENDER_NAME = '대한변리사회';

/* ───────────── 메뉴 ───────────── */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🗂 회원업무')
    .addItem('오늘 날짜 넣기', 'addTodayDate')
    .addSeparator()
    .addItem('① 추천: 중복 신청 확인', 'menuCheckDuplicates')
    .addItem('② 추천: 선정 메일 시험 발송(나에게)', 'menuSendTestMail')
    .addItem('③ 추천: 선정 메일 실제 발송', 'menuSendSelectedMails')
    .addItem('④ 추천: 미선정자 목록 만들기', 'menuListUnselected')
    .addSeparator()
    .addItem('⑤ 현황: 연수·공익·회비 통합하기', 'menuBuildStatus')
    .addSeparator()
    .addItem('작업 패널 열기', 'openPanel')
    .addToUi();
}

function addTodayDate() {
  const cell = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet().getActiveCell();
  cell.setValue(Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd'));
}

/* 메뉴용: 실행 결과를 알림창으로 보여줍니다. */
function menuCheckDuplicates() { alert_(checkDuplicates()); }
function menuSendTestMail() { alert_(sendTestMail()); }
function menuListUnselected() { alert_(listUnselected()); }
function menuBuildStatus() { alert_(buildStatus()); }
function menuSendSelectedMails() {
  const ui = SpreadsheetApp.getUi();
  const preview = countMailTargets();
  if (preview === 0) { ui.alert('보낼 대상이 없습니다.\n[선정] 칸에 체크했는지, 이미 [발송완료]가 아닌지 확인하세요.'); return; }
  const ok = ui.alert('실제 발송', preview + '명에게 선정 안내 메일을 보냅니다. 진행할까요?', ui.ButtonSet.YES_NO);
  if (ok !== ui.Button.YES) { ui.alert('발송을 취소했습니다.'); return; }
  alert_(sendSelectedMails());
}

/* ───────────── 1. 회원 추천: 중복 신청 확인 ───────────── */
function checkDuplicates() {
  const sh = getSheet_(SHEET.APPLY);
  const col = prepareApplySheet_(sh);
  const n = sh.getLastRow() - 1;
  if (n < 1) return '신청 데이터가 없습니다.';
  const width = sh.getLastColumn();
  const rows = sh.getRange(2, 1, n, width).getValues();

  // 등록번호(없으면 성명+연락처)로 같은 사람을 묶습니다.
  const groups = {};
  rows.forEach(function (r, i) {
    const key = personKey_(r, col);
    if (!key) return;
    (groups[key] = groups[key] || []).push(i);
  });

  const notes = rows.map(function () { return ['']; });
  const colors = rows.map(function () { return new Array(width).fill(null); });
  let people = 0, sameOrg = 0;
  Object.keys(groups).forEach(function (key) {
    const idx = groups[key];
    if (idx.length < 2) return;
    people++;
    const orgs = idx.map(function (i) { return String(rows[i][col['추천기관']] || '(기관 미기재)'); });
    const orgCount = {};
    orgs.forEach(function (o) { orgCount[o] = (orgCount[o] || 0) + 1; });
    idx.forEach(function (i) {
      const myOrg = String(rows[i][col['추천기관']] || '(기관 미기재)');
      const dupSame = orgCount[myOrg] > 1;
      if (dupSame) sameOrg++;
      notes[i][0] = (dupSame ? '동일 기관 중복 · ' : '') + '중복 ' + idx.length + '건: ' + orgs.join(', ');
      colors[i] = new Array(width).fill(dupSame ? '#f4cccc' : '#fff2cc');
    });
  });
  sh.getRange(2, 1, n, width).setBackgrounds(colors);
  sh.getRange(2, col['비고'] + 1, n, 1).setValues(notes);
  if (people === 0) return '중복 신청자가 없습니다. (총 ' + n + '건 확인)';
  return '중복 신청자 ' + people + '명을 찾았습니다.\n· 노란색: 여러 기관에 신청\n· 분홍색: 같은 기관에 두 번 이상 신청(' + sameOrg + '건)\n[비고] 칸에서 내용을 확인하세요.';
}

/* ───────────── 2. 회원 추천: 선정 메일 ───────────── */
function countMailTargets() {
  const sh = getSheet_(SHEET.APPLY);
  const col = prepareApplySheet_(sh);
  return mailTargets_(sh, col).length;
}

/** 첫 번째 대상의 메일을 '나에게' 보내 모양을 확인합니다. 상태는 바뀌지 않습니다. */
function sendTestMail() {
  const sh = getSheet_(SHEET.APPLY);
  const col = prepareApplySheet_(sh);
  const targets = mailTargets_(sh, col);
  if (targets.length === 0) return '보낼 대상이 없습니다. [선정] 칸에 체크했는지 확인하세요.';
  const me = Session.getEffectiveUser().getEmail();
  const mail = buildMail_(targets[0].row, col);
  MailApp.sendEmail({ to: me, subject: '[시험] ' + mail.subject, body: mail.body, name: SENDER_NAME });
  return '시험 메일을 ' + me + ' 로 보냈습니다.\n받은편지함에서 제목·본문을 확인한 뒤 [③ 실제 발송]을 실행하세요.\n(실제 대상: ' + targets.length + '명)';
}

/** [선정]에 체크되고 아직 [발송완료]가 아닌 사람에게 메일을 보내고 기록합니다. */
function sendSelectedMails() {
  const sh = getSheet_(SHEET.APPLY);
  const col = prepareApplySheet_(sh);
  const targets = mailTargets_(sh, col);
  if (targets.length === 0) return '보낼 대상이 없습니다.';
  const quota = MailApp.getRemainingDailyQuota();
  if (targets.length > quota) {
    return '오늘 남은 메일 발송 한도(' + quota + '건)보다 대상(' + targets.length + '명)이 많습니다.\n일부만 선정하거나 내일 다시 실행하세요.';
  }
  const log = getOrCreateSheet_(SHEET.LOG, ['발송일시', '성명', '등록번호', '이메일', '추천기관', '제목', '결과']);
  let ok = 0, fail = 0;
  targets.forEach(function (t) {
    const r = t.row;
    const now = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm:ss');
    const email = String(r[col['이메일']] || '').trim();
    const mail = buildMail_(r, col);
    let result;
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      result = '실패: 이메일 형식 오류';
    } else {
      try {
        MailApp.sendEmail({ to: email, subject: mail.subject, body: mail.body, name: SENDER_NAME });
        result = '발송완료';
      } catch (e) {
        result = '실패: ' + e.message;
      }
    }
    if (result === '발송완료') ok++; else fail++;
    sh.getRange(t.sheetRow, col['발송상태'] + 1).setValue(result);
    sh.getRange(t.sheetRow, col['발송일시'] + 1).setValue(now);
    log.appendRow([now, r[col['성명']], r[col['등록번호']], email, r[col['추천기관']], mail.subject, result]);
  });
  return '발송 완료 ' + ok + '건' + (fail ? ', 실패 ' + fail + '건 ([발송상태] 칸 확인)' : '') + '.\n[발송이력] 탭에 기록했습니다.';
}

/* ───────────── 3. 회원 추천: 미선정자 목록 ───────────── */
function listUnselected() {
  const sh = getSheet_(SHEET.APPLY);
  const col = prepareApplySheet_(sh);
  const n = sh.getLastRow() - 1;
  if (n < 1) return '신청 데이터가 없습니다.';
  const rows = sh.getRange(2, 1, n, sh.getLastColumn()).getValues();
  const out = rows.filter(function (r) { return r[col['선정']] !== true && personKey_(r, col); })
    .map(function (r) { return [r[col['추천기관']], r[col['성명']], r[col['등록번호']], r[col['이메일']]]; });
  const target = getOrCreateSheet_(SHEET.UNSELECTED, ['추천기관', '성명', '등록번호', '이메일'], true);
  if (out.length) target.getRange(2, 1, out.length, 4).setValues(out);
  return '미선정자 ' + out.length + '명을 [' + SHEET.UNSELECTED + '] 탭에 정리했습니다.';
}

/* ───────────── 4. 연수·공익·회비 통합 현황 ───────────── */
function buildStatus() {
  const people = {};
  const get = function (reg) {
    return people[reg] = people[reg] || { reg: reg, name: '', office: '', training: false, req: '', done: '', short: 0, publicMissing: false, fee: 0 };
  };

  const tr = readTable_(SHEET.TRAINING);
  if (tr) {
    const c = requireCols_(tr, SHEET.TRAINING, [['등록번호'], ['성명'], ['사무소한글명', '사무소명', '사무소']]);
    tr.rows.forEach(function (r) {
      const reg = normReg_(r[c[0]]); if (!reg) return;
      const p = get(reg); p.training = true; p.name = p.name || r[c[1]]; p.office = String(r[c[2]] || '').trim();
    });
  }
  const pb = readTable_(SHEET.PUBLIC);
  if (pb) {
    // 공익 시스템에서 내려받은 파일은 등록번호 열 이름이 '변리사'로 되어 있어 둘 다 허용합니다.
    const c = requireCols_(pb, SHEET.PUBLIC, [['등록번호', '변리사'], ['성명'], ['의무시간'], ['수행시간']]);
    pb.rows.forEach(function (r) {
      const reg = normReg_(r[c[0]]); if (!reg) return;
      const req = Number(r[c[2]]) || 0, done = Number(r[c[3]]) || 0;
      const short = Math.max(0, req - done);
      if (short <= 0) return;                 // 이미 채운 사람은 미이수가 아님
      const p = get(reg); p.name = p.name || r[c[1]];
      p.req = req; p.done = done; p.short = short; p.publicMissing = true;
    });
  }
  const fe = readTable_(SHEET.FEE);
  if (fe) {
    const c = requireCols_(fe, SHEET.FEE, [['등록번호'], ['성명'], ['미납액', '미납금액']]);
    fe.rows.forEach(function (r) {
      const reg = normReg_(r[c[0]]); if (!reg) return;
      const amount = Number(String(r[c[2]]).replace(/[^0-9.-]/g, '')) || 0;
      if (amount <= 0) return;
      const p = get(reg); p.name = p.name || r[c[1]]; p.fee = amount;
    });
  }
  if (!tr && !pb && !fe) return '[연수], [공익], [회비] 탭이 하나도 없습니다. 내려받은 파일을 각 탭에 붙여넣으세요.';

  // 지난번 통합 결과와 비교(신규/계속/해소)
  const prev = {};
  const prevTable = readTable_(SHEET.STATUS);
  if (prevTable && prevTable.header.indexOf('등록번호') >= 0) {
    const pi = prevTable.header.indexOf('등록번호');
    prevTable.rows.forEach(function (r) { const k = normReg_(r[pi]); if (k) prev[k] = true; });
  }

  const list = Object.keys(people).map(function (k) { return people[k]; });
  list.forEach(function (p) {
    p.count = (p.training ? 1 : 0) + (p.publicMissing ? 1 : 0) + (p.fee > 0 ? 1 : 0);
    p.change = Object.keys(prev).length ? (prev[p.reg] ? '계속' : '신규') : '';
  });
  list.sort(function (a, b) { return b.count - a.count || b.short - a.short || Number(a.reg) - Number(b.reg); });
  const resolved = Object.keys(prev).filter(function (k) { return !people[k]; });

  const header = ['등록번호', '성명', '사무소', '연수 미이수', '공익 의무시간', '공익 수행시간', '공익 부족시간', '회비 미납액', '해당 항목 수', '지난번 대비'];
  const sh = getOrCreateSheet_(SHEET.STATUS, header, true);
  const values = list.map(function (p) {
    return [p.reg, p.name, p.office, p.training ? 'O' : '', p.req, p.done, p.publicMissing ? p.short : '', p.fee || '', p.count, p.change];
  });
  if (values.length) {
    sh.getRange(2, 1, values.length, header.length).setValues(values);
    const colors = list.map(function (p) {
      const c = p.count >= 3 ? '#f4cccc' : p.count === 2 ? '#fce5cd' : null;
      return new Array(header.length).fill(c);
    });
    sh.getRange(2, 1, values.length, header.length).setBackgrounds(colors);
    sh.getRange(2, 8, values.length, 1).setNumberFormat('#,##0');
  }
  sh.setFrozenRows(1);

  // 요약 보드
  const count = function (f) { return list.filter(f).length; };
  const stats = [
    ['전체 대상(1개 이상 해당)', list.length],
    ['연수 미이수', count(function (p) { return p.training; })],
    ['공익 미이수', count(function (p) { return p.publicMissing; })],
    ['회비 미납', count(function (p) { return p.fee > 0; })],
    ['2개 이상 해당', count(function (p) { return p.count >= 2; })],
    ['3개 모두 해당', count(function (p) { return p.count === 3; })],
    ['지난번 대비 신규', count(function (p) { return p.change === '신규'; })],
    ['지난번 대비 해소', resolved.length],
  ];
  const board = getOrCreateSheet_(SHEET.BOARD, ['항목', '인원'], true);
  board.getCharts().forEach(function (ch) { board.removeChart(ch); });
  board.getRange(2, 1, stats.length, 2).setValues(stats);
  board.getRange(stats.length + 3, 1, 1, 2).setValues([['갱신 일시', Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm')]]);
  board.getRange(1, 1, 1, 2).setFontWeight('bold');
  const chart = board.newChart()
    .setChartType(Charts.ChartType.BAR)
    .addRange(board.getRange(3, 1, 3, 2))   // 연수·공익·회비 3줄
    .setPosition(2, 4, 0, 0)
    .setOption('title', '항목별 인원')
    .setOption('legend', { position: 'none' })
    .build();
  board.insertChart(chart);

  return '통합 완료: 대상 ' + list.length + '명 (2개 이상 ' + stats[4][1] + '명)\n[' + SHEET.STATUS + '] 탭과 [' + SHEET.BOARD + '] 탭을 확인하세요.';
}

/* ───────────── 5. 작업 패널(오른쪽 사이드바) ───────────── */
function openPanel() {
  const html = HtmlService.createHtmlOutputFromFile('Panel').setTitle('회원업무 패널');
  SpreadsheetApp.getUi().showSidebar(html);
}

/* ───────────── 공통 도우미 (이름 끝의 _ 는 '내부용' 표시) ───────────── */
function alert_(msg) { SpreadsheetApp.getUi().alert(msg); }

function getSheet_(name) {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if (!sh) throw new Error('[' + name + '] 탭을 찾을 수 없습니다. 탭 이름을 확인하세요.');
  return sh;
}

function getOrCreateSheet_(name, header, reset) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  if (reset) sh.clear();
  if (reset || sh.getLastRow() === 0) {
    sh.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold').setBackground('#eef2f8');
    sh.setFrozenRows(1);
  }
  return sh;
}

/** 추천신청 시트에 [선정]·[비고]·[발송상태]·[발송일시] 열이 없으면 만들고, 열 위치를 돌려줍니다. */
function prepareApplySheet_(sh) {
  const width = Math.max(sh.getLastColumn(), 1);
  const header = sh.getRange(1, 1, 1, width).getValues()[0].map(function (h) { return String(h).trim(); });
  ['선정', '비고', '발송상태', '발송일시'].forEach(function (name) {
    if (header.indexOf(name) < 0) {
      header.push(name);
      sh.getRange(1, header.length).setValue(name).setFontWeight('bold');
    }
  });
  const col = {};
  header.forEach(function (h, i) { if (h) col[h] = i; });
  ['성명', '등록번호', '이메일', '추천기관'].forEach(function (need) {
    if (col[need] === undefined) throw new Error('[' + sh.getName() + '] 탭 1행에 [' + need + '] 열이 필요합니다.');
  });
  const n = sh.getLastRow() - 1;
  if (n > 0) {
    const sel = sh.getRange(2, col['선정'] + 1, n, 1);
    const vals = sel.getValues();
    if (vals.some(function (v) { return v[0] !== true && v[0] !== false; })) {
      sel.setValues(vals.map(function (v) { return [v[0] === true]; }));
      sel.insertCheckboxes();
    }
  }
  return col;
}

function mailTargets_(sh, col) {
  const n = sh.getLastRow() - 1;
  if (n < 1) return [];
  const rows = sh.getRange(2, 1, n, sh.getLastColumn()).getValues();
  const out = [];
  rows.forEach(function (r, i) {
    if (r[col['선정']] === true && String(r[col['발송상태']]) !== '발송완료') out.push({ row: r, sheetRow: i + 2 });
  });
  return out;
}

function buildMail_(r, col) {
  const t = getSheet_(SHEET.TEMPLATE).getRange(1, 2, 2, 1).getValues();
  const fill = function (s) {
    return String(s).replace(/\{([^}]+)\}/g, function (m, key) {
      return col[key] !== undefined ? String(r[col[key]]) : m;
    });
  };
  return { subject: fill(t[0][0]), body: fill(t[1][0]) };
}

function personKey_(r, col) {
  const reg = normReg_(r[col['등록번호']]);
  if (reg) return 'R' + reg;
  const name = String(r[col['성명']] || '').trim();
  const phone = col['연락처'] !== undefined ? String(r[col['연락처']] || '').replace(/\D/g, '') : '';
  return name ? 'N' + name + phone : '';
}

function normReg_(v) {
  const s = String(v === null || v === undefined ? '' : v).replace(/\D/g, '');
  return s ? String(Number(s)) : '';
}

function readTable_(name) {
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(name);
  if (!sh || sh.getLastRow() < 1) return null;
  const all = sh.getDataRange().getValues();
  // 첫 줄이 제목(예: '7차 연수 미이수자')이면 건너뛰고 실제 머리행을 찾습니다.
  let h = 0;
  while (h < Math.min(all.length, 5) && all[h].filter(function (x) { return x !== '' && x !== null; }).length < 2) h++;
  return { header: all[h].map(function (x) { return String(x).trim(); }), rows: all.slice(h + 1) };
}

function requireCols_(table, name, choices) {
  return choices.map(function (alts) {
    for (let i = 0; i < alts.length; i++) {
      const idx = table.header.indexOf(alts[i]);
      if (idx >= 0) return idx;
    }
    throw new Error('[' + name + '] 탭에 [' + alts.join(' 또는 ') + '] 열이 필요합니다.');
  });
}
