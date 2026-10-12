import { createRequire } from 'module';
// 실행: BASE_URL=http://localhost:8000 node tests_e2e/ui_flow.mjs ./shots  (admin 초기 비밀번호 Admin!2345pw, --demo 데이터 필요)
const require = createRequire(process.env.PLAYWRIGHT_REQUIRE_FROM || import.meta.url);
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL || 'http://localhost:8000';
const shots = process.argv[2] || '.';
const errors = [];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('response', r => { if (r.status() >= 500) errors.push(`HTTP ${r.status()} ${r.url()}`); });
const step = async (name, fn) => { try { await fn(); console.log('OK  ', name); } catch (e) { console.log('FAIL', name, e.message.split('\n')[0]); errors.push(name + ': ' + e.message.split('\n')[0]); } };
const toastText = async () => (await page.locator('#toast').innerText()).trim();

await page.goto(BASE + '/');
await step('login', async () => {
  await page.fill('input[name=username]', 'admin');
  await page.fill('input[name=password]', 'Admin!2345pw');
  await page.click('button[type=submit]');
  await page.waitForSelector('.modal');   // forced password change
});
await step('forced password change', async () => {
  await page.fill('.modal input[name=current]', 'Admin!2345pw');
  await page.fill('.modal input[name=new]', 'NewPass!2026x');
  await page.fill('.modal input[name=new2]', 'NewPass!2026x');
  await page.click('.modal button.primary');
  await page.waitForSelector('.modal', { state: 'detached' });
});
await step('dashboard', async () => { await page.waitForSelector('text=처리 단계별 현황'); await page.screenshot({ path: `${shots}/01_dashboard.png`, fullPage: true }); });
await step('cases list', async () => { await page.goto(BASE + '/#/cases'); await page.waitForSelector('table tbody tr'); await page.screenshot({ path: `${shots}/02_cases.png`, fullPage: true }); });
await step('case detail', async () => {
  await page.click('table tbody tr:last-child'); // first demo AD case (ordered desc)
  await page.waitForSelector('.stepper'); await page.screenshot({ path: `${shots}/03_case_overview.png`, fullPage: true });
});
await step('evidence tab', async () => { await page.click('.tabs button:has-text("채증")'); await page.waitForSelector('text=광고규정 1차 스크리닝 결과'); await page.screenshot({ path: `${shots}/04_case_evidence.png`, fullPage: true }); });
await step('confirm finding', async () => { await page.locator('button:has-text("위반 소지 인정")').first().click(); await page.waitForSelector('.badge.CONFIRMED'); });
await step('analysis tab + run', async () => {
  await page.click('.tabs button:has-text("근거 분석")');
  await page.click('button:has-text("분석 실행")');
  await page.waitForSelector('text=적용 후보 조문');
  await page.screenshot({ path: `${shots}/05_case_analysis.png`, fullPage: true });
  await page.locator('button:has-text("사건에 적용")').first().click();
  await page.waitForTimeout(600);
  await page.click('.tabs button:has-text("근거 분석")');
  await page.waitForSelector('button:has-text("제외")');
});
await step('transition REVIEW -> PENDING_APPROVAL -> EXPLANATION_REQUESTED', async () => {
  for (const [to, note] of [['REVIEW', ''], ['PENDING_APPROVAL', ''], ['EXPLANATION_REQUESTED', '담당 이사 홍길동, 2026-10-12 전자결재']]) {
    await page.click('button:has-text("단계 변경")');
    await page.selectOption('.modal select[name=to]', to);
    if (note) await page.fill('.modal textarea[name=note]', note);
    await page.click('.modal button.primary');
    await page.waitForSelector('.modal', { state: 'detached' });
    await page.waitForTimeout(300);
  }
  await page.waitForSelector('.stepper .s.cur:has-text("소명 요청")');
});
await step('compose explanation letter', async () => {
  await page.click('.tabs button:has-text("공문")');
  await page.click('button:has-text("공문 자동 작성")');
  await page.waitForSelector('.modal textarea[name=body]');
  await page.waitForFunction(() => document.querySelector('.modal textarea[name=body]').value.includes('소명'));
  await page.fill('.modal input[name=doc_no]', '대한변리사회-9999');
  await page.click('.modal button:has-text("다시 자동 작성")');
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${shots}/06_compose.png`, fullPage: true });
  await page.click('.modal button:has-text("초안 저장")');
  await page.waitForSelector('.modal h2:has-text("공문 —")');
  await page.screenshot({ path: `${shots}/07_document.png`, fullPage: true });
});
await step('approve blocked by missing items', async () => {
  page.once('dialog', d => d.accept('담당 이사 홍길동, 2026-10-12'));
  await page.click('.modal button:has-text("결재 완료 처리")');
  await page.waitForTimeout(500);
  const t = await toastText();
  if (!t.includes('확인 필요')) throw new Error('expected missing-item block, got: ' + t);
});
await step('close modals', async () => { while (await page.locator('.modal').count()) { await page.locator('.modal button:has-text("닫기")').last().click(); } });
await step('settings: contact + approval line', async () => {
  await page.goto(BASE + '/#/admin');
  await page.click('.tabs button:has-text("기본 설정")');
  await page.fill('input[name=contact_phone]', '02-3486-0000');
  await page.fill('input[name=contact_email]', 'ad@kpaa.example');
  await page.fill('input[name=approval_line]', '차장 이대운 실장 OOO 사무총장 OOO');
  await page.click('button:has-text("저장")');
  await page.waitForTimeout(500);
});
await step('new letter -> approve -> send manual', async () => {
  await page.goto(BASE + '/#/cases');
  await page.click('table tbody tr:last-child');
  await page.click('.tabs button:has-text("공문")');
  await page.click('button:has-text("공문 자동 작성")');
  await page.waitForFunction(() => document.querySelector('.modal textarea[name=body]')?.value.includes('소명'));
  await page.fill('.modal input[name=doc_no]', '대한변리사회-10001');
  await page.click('.modal button:has-text("다시 자동 작성")');
  await page.waitForTimeout(400);
  // 남은 확인 필요(변리사 성명 등) 직접 채우기
  const body = await page.inputValue('.modal textarea[name=body]');
  await page.fill('.modal textarea[name=body]', body.replace(/\{\{확인 필요: [^}]+\}\}/g, '가상인'));
  await page.click('.modal button:has-text("초안 저장")');
  await page.waitForSelector('.modal h2:has-text("공문 —")');
  page.once('dialog', d => d.accept('담당 이사 홍길동, 2026-10-12 전자결재'));
  await page.click('.modal button:has-text("결재 완료 처리")');
  await page.waitForSelector('.modal .badge.APPROVED');
  await page.click('.modal button:has-text("발송 기록")');
  await page.fill('.modal input[name=sent_ref]', '그룹웨어 메일 [소명요청] 2026-10-12 10:30');
  await page.locator('.modal').last().locator('button.primary').click();
  await page.waitForSelector('.modal .badge.SENT');
  await page.screenshot({ path: `${shots}/08_sent.png`, fullPage: true });
  while (await page.locator('.modal').count()) { await page.locator('.modal button:has-text("닫기")').last().click(); }
});
await step('history shows MAIL', async () => { await page.click('.tabs button:has-text("처리 경과")'); await page.waitForSelector('.timeline li.MAIL'); await page.screenshot({ path: `${shots}/09_history.png`, fullPage: true }); });
await step('docx download', async () => {
  await page.goto(BASE + '/#/documents'); await page.waitForSelector('table tbody tr');
  await page.click('table tbody tr:first-child');
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('.modal button:has-text(".docx")')]);
  const p = await dl.path(); if (!p) throw new Error('no download');
  while (await page.locator('.modal').count()) { await page.locator('.modal button:has-text("닫기")').last().click(); }
});
await step('monitoring quick screen', async () => {
  await page.goto(BASE + '/#/monitoring');
  await page.fill('textarea[name=text]', '업계 최초! 특허 등록률 97.5%, 상표출원 반값 할인 이벤트. 국제변리사 직접 상담');
  await page.click('button:has-text("스크리닝")');
  await page.waitForSelector('.card-list .item');
  await page.screenshot({ path: `${shots}/10_monitoring.png`, fullPage: true });
});
await step('regs match', async () => {
  await page.goto(BASE + '/#/regs');
  await page.fill('textarea[name=facts]', '변리사가 수임 사건 의뢰인의 영업비밀을 동의 없이 제3자에게 알려줌');
  await page.click('button:has-text("매칭")');
  await page.waitForSelector('text=적용 후보 조문');
  await page.screenshot({ path: `${shots}/11_regs.png`, fullPage: true });
});
await step('precedents', async () => { await page.goto(BASE + '/#/precedents'); await page.fill('textarea[name=text]', '업계 1위 광고'); await page.click('button:has-text("검색")'); await page.waitForSelector('text=정리된 선례'); await page.screenshot({ path: `${shots}/12_precedents.png`, fullPage: true }); });
await step('meeting create + agenda + minutes', async () => {
  // 사건 #2(국제변리사)를 위원회 상정 상태로
  await page.goto(BASE + '/#/cases'); await page.locator('table tbody tr').nth(1).click();
  for (const [to, note] of [['REVIEW', ''], ['COMMITTEE', '']]) {
    await page.click('button:has-text("단계 변경")'); await page.selectOption('.modal select[name=to]', to);
    if (note) await page.fill('.modal textarea[name=note]', note);
    await page.click('.modal button.primary'); await page.waitForSelector('.modal', { state: 'detached' }); await page.waitForTimeout(300);
  }
  await page.goto(BASE + '/#/meetings');
  await page.click('button:has-text("회의 등록")');
  await page.fill('.modal input[name=title]', '2026년 제3차 광고심사위원회');
  await page.fill('.modal input[name=scheduled_at]', '2026-10-20T15:00');
  await page.fill('.modal textarea', '김위원장, 위원장\n이위원, 위원\n박위원, 위원');
  await page.click('.modal button.primary');
  await page.waitForSelector('text=안건 추가');
  await page.selectOption('select >> nth=0', { index: 1 });
  await page.click('button:has-text("추가")');
  await page.waitForSelector('.card-list .item');
  await page.selectOption('.card-list .item select[name=decision]', 'CORRECTION');
  await page.fill('.card-list .item input[name=vote_for]', '3');
  await page.fill('.card-list .item input[name=vote_against]', '0');
  await page.fill('.card-list .item input[name=decision_note]', '30일 내 홈페이지 표기 시정');
  await page.click('.card-list .item button:has-text("저장")');
  await page.waitForTimeout(500);
  await page.click('button:has-text("회의자료 자동 작성")');
  await page.waitForSelector('.modal pre.doc');
  await page.screenshot({ path: `${shots}/13_agenda.png`, fullPage: true });
  await page.locator('.modal button:has-text("닫기")').last().click();
  page.once('dialog', d => d.accept());
  await page.click('button:has-text("의결 결과 사건에 반영")');
  await page.waitForSelector('.modal .alert.ok');
  await page.locator('.modal button:has-text("닫기")').last().click();
  await page.click('.tabs button:has-text("녹취")');
  await page.fill('textarea[name=transcript]', '김위원장 00:01\n제1호 안건 심의를 시작하겠습니다.\n이위원 00:40\n국제변리사 명칭은 법적 근거가 없어 제4조 제10호 위반 소지가 크다고 판단합니다.\n박위원 01:20\n직원을 상표전문가로 표기한 것도 제9호 문제로 보입니다.\n김위원장 02:10\n그럼 30일 내 시정 요구하기로 의결하겠습니다. 찬성 3명 반대 0명입니다. 사무국은 결과를 통보하기로 합니다.');
  await page.click('button:has-text("정리 실행")');
  await page.waitForSelector('text=위원별 핵심 발언');
  await page.screenshot({ path: `${shots}/14_minutes.png`, fullPage: true });
  await page.click('button:has-text("저장") >> nth=0');
  await page.waitForTimeout(500);
});
await step('mobile layout', async () => { await page.setViewportSize({ width: 390, height: 844 }); await page.goto(BASE + '/#/'); await page.waitForSelector('text=처리 단계별 현황'); await page.screenshot({ path: `${shots}/15_mobile.png`, fullPage: true }); });
await browser.close();
console.log('\nERRORS:', errors.length ? '\n' + errors.join('\n') : 'none');
