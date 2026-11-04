// 교안 점검: node check_lesson.mjs <교안 폴더(index.html 있는 곳)> <스크린샷 저장 폴더>
// - PC(1280) + 휴대폰(390·360)에서 모든 탭: 가로 넘침, 잘린 요소, 콘솔 오류
// - 복사 버튼 동작, 휴대폰 그림 탭 확대(라이트박스), 촬영 목록 생성
// - 번호 대응(경고): 그림 한 장 안의 같은 번호 중복, 그림 번호가 따라 하기 항목 수보다 큼
// - 그림 안: 번호 대상이 팝업에 가려짐·팝업이 그림 밖으로 넘침(오류), 번호 배지 겹침(경고) / PC 상단 탭 두 줄
// - 한글 글꼴 설치 여부(없으면 스크린샷·육안 점검이 □로 보임)
// Playwright 필요. 전역 설치(npm root -g)도 자동으로 찾는다. 다른 위치면 PLAYWRIGHT_REQUIRE_FROM 지정.
import { createRequire } from 'module';
import { execSync } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
function loadPlaywright() {
  const tries = [process.env.PLAYWRIGHT_REQUIRE_FROM, import.meta.url];
  try { tries.push(execSync('npm root -g', { encoding: 'utf8' }).trim() + '/'); } catch {}
  for (const t of tries.filter(Boolean)) { try { return createRequire(t)('playwright'); } catch {} }
  console.error('Playwright를 찾지 못했습니다. npm i -g playwright 후 다시 실행하거나, 브라우저 없이 python3 check_lesson.py 로 점검하세요.');
  process.exit(2);
}
const { chromium, devices } = loadPlaywright();
try {
  const ko = execSync('fc-list :lang=ko family', { encoding: 'utf8' }).trim();
  if (!ko) console.log('⚠ 한글 글꼴이 없습니다 — 스크린샷의 한글이 □로 보일 수 있습니다(예: apt-get install -y fonts-noto-cjk).');
} catch {}

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
  if (label === 'desktop' && navH > 70) problems.push(`[desktop] 상단 탭이 두 줄(${navH}px) — 탭 이름·브랜드 글자를 줄이기`);
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
    const outside = await p.evaluate(() => [...document.querySelectorAll('main.page section.step')].filter(s => !s.closest('.wrap')).map(s => s.id.slice(1)));
    if (outside.length) problems.push(`단계 카드가 본문 상자(wrap) 밖에 있음: STEP ${outside.join(', ')} — wrap(...) 괄호 위치 확인`);
    const dup = await p.evaluate(() => { const s = [...document.querySelectorAll('figure.shot')].map(f => f.dataset.shot); return s.filter((x, i) => s.indexOf(x) !== i); });
    if (dup.length) problems.push(`[desktop] 그림 ID 중복: ${[...new Set(dup)].join(', ')}`);
    // 글 번호 ↔ 그림 번호 대응
    const marks = await p.evaluate(() => [...document.querySelectorAll('section.step')].map(st => {
      const todo = st.querySelectorAll('ol.do > li').length;
      return { no: st.id.slice(1), todo, figs: [...st.querySelectorAll('figure.shot')].map(f => ({ id: f.dataset.shot, ns: [...f.querySelectorAll('.mk')].map(m => +m.dataset.n).filter(Boolean) })) };
    }));
    const notes = [];
    for (const st of marks) for (const f of st.figs) {
      const d = f.ns.filter((n, i) => f.ns.indexOf(n) !== i);
      if (d.length) notes.push(`STEP ${st.no} 그림 ${f.id}: 같은 번호 ${[...new Set(d)].join(',')}가 두 곳 — '누를 곳 + 결과'처럼 의도한 게 아니면 하나 지우기`);
      const mx = Math.max(0, ...f.ns);
      if (mx > st.todo) notes.push(`STEP ${st.no} 그림 ${f.id}: 번호 ${mx} > 따라 하기 ${st.todo}개 — 글 번호와 대응 확인`);
    }
    // 그림 안 겹침·잘림: 번호 대상이 팝업에 가려짐, 팝업이 그림 밖으로 넘침, 번호 배지끼리 겹침
    for (const id of ids) {
      await p.evaluate(i => document.querySelector(`.tab[data-p="${i}"]`).click(), id);
      await p.waitForTimeout(150);
      const figsOnPage = await p.locator('.page.show figure.shot').all();
      for (const fg of figsOnPage) {
        await fg.scrollIntoViewIfNeeded();
        const r = await fg.evaluate(f => {
          const out = { covered: [], spill: [], overlap: [] };
          const mock = f.querySelector('.mock'); if (!mock || mock.offsetParent === null) return out;
          const box = mock.getBoundingClientRect();
          const mks = [...f.querySelectorAll('.mk')];
          for (const m of mks) {
            const rc = m.getBoundingClientRect();
            const x = Math.min(rc.left + Math.min(rc.width, 30) / 2, box.right - 2), y = rc.top + rc.height / 2;
            if (rc.width < 1 || y < 0 || y > innerHeight) continue;
            const hit = document.elementFromPoint(x, y);
            if (hit && !m.contains(hit) && !hit.contains(m)) out.covered.push(m.dataset.n);
          }
          mock.querySelectorAll('.dd,.dlg,.sidebar,.cv-pop,[class*="pop"],[class*="peek"],[class*="modal"]').forEach(el => {
            const rc = el.getBoundingClientRect();
            if (rc.width && (rc.bottom > box.bottom + 2 || rc.right > box.right + 2 || rc.left < box.left - 2)) out.spill.push(String(el.className).split(' ')[0]);
          });
          const badges = mks.map(m => { const rc = m.getBoundingClientRect(); return { n: m.dataset.n, x: rc.right, y: rc.top }; });
          for (let i = 0; i < badges.length; i++) for (let j = i + 1; j < badges.length; j++)
            if (Math.abs(badges[i].x - badges[j].x) < 16 && Math.abs(badges[i].y - badges[j].y) < 16) out.overlap.push(badges[i].n + '·' + badges[j].n);
          return out;
        });
        const sid = await fg.getAttribute('data-shot');
        if (r.covered.length) problems.push(`그림 ${sid}: 번호 ${[...new Set(r.covered)].join(',')}의 대상이 다른 요소(팝업 등)에 가려짐`);
        if (r.spill.length) problems.push(`그림 ${sid}: 팝업·메뉴가 그림 밖으로 넘쳐 잘림(${[...new Set(r.spill)].join(',')}) — 위치(top/left/right)나 그림 높이 조정`);
        if (r.overlap.length) notes.push(`그림 ${sid}: 번호 배지가 겹침(${r.overlap.join(', ')})`);
      }
    }
    if (notes.length) console.log('⚠ ' + notes.join('\n⚠ '));
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
