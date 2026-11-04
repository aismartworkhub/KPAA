// 교안 점검: node check_lesson.mjs <교안 폴더(index.html 있는 곳)> <스크린샷 저장 폴더>
// - PC(1280) + 휴대폰(390·360)에서 모든 탭: 가로 넘침, 잘린 요소, 콘솔 오류
// - 복사 버튼 동작, 휴대폰 그림 탭 확대(라이트박스), 촬영 목록 생성
// Playwright 필요. 설치 위치가 다르면 PLAYWRIGHT_REQUIRE_FROM 환경변수로 지정.
import { createRequire } from 'module';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const require = createRequire(process.env.PLAYWRIGHT_REQUIRE_FROM || import.meta.url);
const { chromium, devices } = require('playwright');

const dir = path.resolve(process.argv[2] || '.');
const out = path.resolve(process.argv[3] || './lesson-check');
fs.mkdirSync(out, { recursive: true });
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml' };
const server = http.createServer((req, res) => {
  const p = path.join(dir, decodeURIComponent(req.url.split('?')[0]).replace(/\/$/, '/index.html'));
  if (!p.startsWith(dir) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' }); fs.createReadStream(p).pipe(res);
}).listen(0);
const base = `http://127.0.0.1:${server.address().port}/index.html`;

const problems = [];
const b = await chromium.launch();
const configs = [['desktop', { viewport: { width: 1280, height: 900 } }], ['iphone', devices['iPhone 13']], ['galaxy', { ...devices['Galaxy S9+'], viewport: { width: 360, height: 740 } }]];
for (const [label, opt] of configs) {
  const ctx = await b.newContext({ ...opt, permissions: label === 'desktop' ? ['clipboard-read', 'clipboard-write'] : [] });
  const p = await ctx.newPage();
  p.on('pageerror', e => problems.push(`[${label}] 스크립트 오류: ${e.message}`));
  p.on('console', m => { if (m.type() === 'error' && !/404|Failed to load resource/.test(m.text())) problems.push(`[${label}] 콘솔: ${m.text()}`); });
  await p.goto(base);
  const ids = await p.evaluate(() => [...document.querySelectorAll('.tab')].map(t => t.dataset.p));
  const navH = await p.evaluate(() => Math.round(document.querySelector('.nav').getBoundingClientRect().height));
  if (label !== 'desktop' && navH > 80) problems.push(`[${label}] 상단 탭 높이 ${navH}px — 휴대폰에서 너무 큼`);
  for (const id of ids) {
    await p.evaluate(i => document.querySelector(`.tab[data-p="${i}"]`).click(), id);
    await p.waitForTimeout(250);
    const r = await p.evaluate(() => {
      const vw = document.documentElement.clientWidth;
      const over = new Set();
      document.querySelectorAll('.page.show *').forEach(el => {
        const rc = el.getBoundingClientRect();
        if (rc.width && rc.right > vw + 1 && !el.closest('pre') && !el.closest('.mock') && !el.closest('table.t') && !el.closest('.tabs')) over.add(el.tagName + (el.className ? '.' + String(el.className).split(' ')[0] : ''));
      });
      return { docW: document.documentElement.scrollWidth, vw, over: [...over].slice(0, 5), figs: document.querySelectorAll('.page.show figure.shot').length };
    });
    if (r.docW > r.vw + 1) problems.push(`[${label}] ${id}: 화면이 옆으로 밀림(${r.docW}px > ${r.vw}px)`);
    if (r.over.length) problems.push(`[${label}] ${id}: 오른쪽이 잘리는 요소 ${r.over.join(', ')}`);
    await p.screenshot({ path: `${out}/${label}_${id}.png`, fullPage: label === 'desktop' });
  }
  if (label === 'desktop') {
    const btn = p.locator('button[data-copy]').first();
    if (await btn.count()) {
      const tab = await btn.evaluate(e => e.closest('.page').id);
      await p.evaluate(i => document.querySelector(`.tab[data-p="${i}"]`).click(), tab);
      await btn.click();
      const clip = await p.evaluate(() => navigator.clipboard.readText());
      if (!clip || clip.length < 5) problems.push('[desktop] 코드 전체 복사 결과가 비어 있음');
    }
    const shots = await p.locator('#shotlist tr').count();
    const figsTotal = await p.locator('figure.shot').count();
    if (figsTotal && shots !== figsTotal + 1) problems.push(`[desktop] 촬영 목록 ${shots - 1}행 ≠ 그림 ${figsTotal}개 (부록에 shot_list_section() 필요)`);
    const dup = await p.evaluate(() => { const s = [...document.querySelectorAll('figure.shot')].map(f => f.dataset.shot); return s.filter((x, i) => s.indexOf(x) !== i); });
    if (dup.length) problems.push(`[desktop] 그림 ID 중복: ${[...new Set(dup)].join(', ')}`);
    console.log(`그림 ${figsTotal}개, 탭 ${ids.length}개`);
  } else {
    const f = p.locator('.page.show figure.shot').first();
    let pageWithFig = null;
    for (const id of ids) {
      await p.evaluate(i => document.querySelector(`.tab[data-p="${i}"]`).click(), id);
      if (await p.locator('.page.show figure.shot').count()) { pageWithFig = id; break; }
    }
    if (pageWithFig) {
      const fg = p.locator('.page.show figure.shot').first();
      await fg.scrollIntoViewIfNeeded(); await p.waitForTimeout(200);
      const zoomable = await fg.evaluate(e => e.classList.contains('zoomable'));
      if (!zoomable) problems.push(`[${label}] 그림이 화면 폭에 맞춰지지 않음(zoomable 아님)`);
      await fg.tap();
      if (!(await p.locator('.lightbox').count())) problems.push(`[${label}] 그림을 탭해도 크게 보기가 열리지 않음`);
      else { await p.screenshot({ path: `${out}/${label}_zoom.png` }); await p.click('.lightbox .lb-top button'); }
    }
  }
  console.log(`[${label}] 탭 ${ids.length}개 점검, 상단 탭 높이 ${navH}px`);
  await ctx.close();
}
await b.close(); server.close();
if (problems.length) { console.log('\n문제 ' + problems.length + '건:\n- ' + problems.join('\n- ')); process.exitCode = 1; }
else console.log('\n문제 없음 ✓  스크린샷: ' + out);
