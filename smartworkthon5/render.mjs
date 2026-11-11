// 배너 출력: node render.mjs [파일명.html ...]
//  - output/<이름>.pdf        인쇄용 (실제 mm 크기, 벡터·글꼴 포함)
//  - output/<이름>_인쇄용.jpg  인쇄소용 고해상도 (약 150dpi)
//  - output/<이름>_미리보기.png 화면 확인용
import { createRequire } from 'module';
import { readdirSync } from 'fs';
import path from 'path';
const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const dir = path.dirname(new URL(import.meta.url).pathname);
const files = process.argv.slice(2).length ? process.argv.slice(2)
  : readdirSync(dir).filter(f => /^\d\d_.*\.html$/.test(f)).sort();

const browser = await chromium.launch();
import { readFileSync } from 'fs';
const qrPlaceholder = readFileSync(path.join(dir, 'assets', 'review_qr.svg'), 'utf8').includes('QR 자리');
for (const f of files) {
  const name = f.replace(/\.html$/, '');
  const url = 'file://' + path.join(dir, f);
  // 캔버스 크기 읽기 (1px = 1mm)
  const probe = await browser.newPage();
  await probe.goto(url, { waitUntil: 'networkidle' });
  await probe.evaluate(() => document.fonts.ready);
  const { w, h } = await probe.evaluate(() => {
    const r = document.querySelector('.canvas').getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) };
  });
  await probe.close();

  const shot = async (scale, out, type) => {
    const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: scale });
    const p = await ctx.newPage();
    await p.goto(url, { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    await p.locator('.canvas').screenshot({ path: path.join(dir, 'output', out), type, ...(type === 'jpeg' ? { quality: 92 } : {}) });
    await ctx.close();
  };
  await shot(2, `${name}_미리보기.png`, 'png');
  await shot(6, `${name}_인쇄용.jpg`, 'jpeg');   // 1mm = 6px ≈ 152dpi
  if (w > h) await shot(1, `${name}_화면용_${w}x${h}px.png`, 'png');  // 가로형은 화면 송출용 원본 크기도

  // 인쇄용 PDF: 1px → 1mm 로 확대
  const p = await browser.newPage();
  await p.goto(url, { waitUntil: 'networkidle' });
  await p.addStyleTag({ content: `@page{size:${w}mm ${h}mm;margin:0} html{zoom:${96/25.4}} html,body{background:none}` });
  await p.evaluate(() => document.fonts.ready);
  await p.pdf({ path: path.join(dir, 'output', `${name}.pdf`), width: `${w}mm`, height: `${h}mm`, printBackground: true, pageRanges: '1' });
  await p.close();
  console.log(`${name}: ${w}×${h}mm 완료`);
  if (qrPlaceholder && readFileSync(path.join(dir, f), 'utf8').includes('review_qr.svg'))
    console.log('  ⚠ QR이 아직 빈 자리입니다 — 인쇄 전에 python3 review-form/make_qr.py <구글폼 주소> 실행');
}
await browser.close();
