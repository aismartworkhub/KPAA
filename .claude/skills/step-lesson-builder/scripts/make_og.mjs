// 카카오톡·SNS 미리보기 이미지(1200x630) 렌더링
// node make_og.mjs <미리보기 HTML 파일> <출력 파일(.jpg|.png)>
import { createRequire } from 'module';
import path from 'node:path';
const require = createRequire(process.env.PLAYWRIGHT_REQUIRE_FROM || import.meta.url);
const { chromium } = require('playwright');
const [src, dst] = process.argv.slice(2).map(p => path.resolve(p));
if (!src || !dst) { console.error('사용법: node make_og.mjs og.html og_image.jpg'); process.exit(1); }
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
await p.goto('file://' + src);
await p.waitForTimeout(300);
await p.screenshot({ path: dst, ...(dst.endsWith('.jpg') ? { type: 'jpeg', quality: 88 } : {}) });
await b.close();
console.log('wrote', dst);
