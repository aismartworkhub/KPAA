// 가상 사례집 PDF 만들기: node claude-work/src/make_pdf.mjs
import { createRequire } from 'module';
import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
const require = createRequire(execSync('npm root -g').toString().trim() + '/');
const { chromium } = require('playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const b = await chromium.launch();
const p = await b.newPage();
await p.goto('file://' + path.join(here, 'casebook.html'));
await p.pdf({ path: path.join(here, '..', 'practice', '09_가상사례집_발췌.pdf'), format: 'A4', printBackground: true, preferCSSPageSize: true });
await b.close();
console.log('wrote practice/09_가상사례집_발췌.pdf');
