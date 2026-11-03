// 카카오톡·SNS 미리보기 이미지 생성: node appscript/src/make_og.mjs  →  appscript/og_image.jpg (1200x630)
// Playwright 필요 (PLAYWRIGHT_REQUIRE_FROM 로 설치 위치 지정 가능)
import { createRequire } from 'module';
import path from 'node:path';
const require = createRequire(process.env.PLAYWRIGHT_REQUIRE_FROM || import.meta.url);
const { chromium } = require('playwright');
const here = path.dirname(new URL(import.meta.url).pathname);
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
await p.goto('file://' + path.join(here, 'og.html'));
await p.waitForTimeout(300);
await p.screenshot({ path: path.join(here, '..', 'og_image.jpg'), type: 'jpeg', quality: 88 });
await b.close();
console.log('wrote og_image.jpg');
