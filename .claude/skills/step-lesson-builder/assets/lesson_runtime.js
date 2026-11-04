// lessonkit 런타임: 탭 전환 · 복사 버튼 · 실제 캡처 자동 교체 · 촬영 목록 · 휴대폰 맞춤 축소/탭 확대
const tabs = document.querySelectorAll('.tab');
var go = function (id, push){
  document.querySelectorAll('.page').forEach(p => p.classList.toggle('show', p.id === id));
  tabs.forEach(t => t.classList.toggle('on', t.dataset.p === id));
  if (push !== false) history.replaceState(null, '', '#' + id);
  window.scrollTo(0, 0);
};
tabs.forEach(t => t.addEventListener('click', () => go(t.dataset.p)));
const _go = go;
go = function (id, push) { _go(id, push); const t = document.querySelector('.tab.on'); if (t) t.scrollIntoView({ inline: 'center', block: 'nearest' }); requestAnimationFrame(fitMocks); };
document.querySelectorAll('[data-go]').forEach(a => a.addEventListener('click', e => { e.preventDefault(); go(a.dataset.go); }));
const PAGE_IDS = [__PAGE_IDS__];
{ const h = (location.hash || '').slice(1); go(PAGE_IDS.includes(h) ? h : PAGE_IDS[0], false); }

async function copyText(text, btn){
  try { await navigator.clipboard.writeText(text); }
  catch (e) { const ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
  const old = btn.textContent; btn.textContent = '복사됨 ✓'; btn.classList.add('done');
  setTimeout(() => { btn.textContent = old; btn.classList.remove('done'); }, 1600);
}
document.querySelectorAll('[data-copy]').forEach(b => b.addEventListener('click', () => copyText(document.getElementById(b.dataset.copy).textContent, b)));
document.querySelectorAll('[data-copy-text]').forEach(b => b.addEventListener('click', () => {
  const box = b.parentElement.cloneNode(true); box.querySelector('button').remove(); copyText(box.textContent.trim(), b);
}));

// 실제 캡처(shots/<ID>.png)가 있으면 모형 대신 표시
const list = document.getElementById('shotlist');
const rows = [];
document.querySelectorAll('figure.shot').forEach(f => {
  const id = f.dataset.shot; rows.push([id, f.dataset.cap]);
  const img = new Image();
  img.onload = () => {
    const box = () => { const m = f.querySelector('.mock'); return m.parentElement.classList.contains('mock-fit') ? m.parentElement : m; };
    img.alt = f.dataset.cap; f.insertBefore(img, box()); box().style.display = 'none';
    const t = document.createElement('button'); t.className = 'tog'; t.textContent = '모형 보기';
    t.onclick = (e) => { e.stopPropagation(); const b = box(); const showMock = b.style.display === 'none'; b.style.display = showMock ? '' : 'none'; img.style.display = showMock ? 'none' : ''; t.textContent = showMock ? '실제 화면 보기' : '모형 보기'; fitMocks(); };
    f.querySelector('figcaption').appendChild(t);
  };
  img.src = 'shots/' + id + '.png';
});

// ── 휴대폰: 모형 화면을 화면 폭에 맞게 축소, 탭하면 원래 크기로 크게 보기 ──
const DESIGN_W = 560;
function fitMocks() {
  document.querySelectorAll('.page.show figure.shot').forEach(f => {
    const mock = f.querySelector('.mock');
    if (!mock) return;
    let wrap = mock.parentElement.classList.contains('mock-fit') ? mock.parentElement : null;
    if ((wrap || mock).style.display === 'none') return;
    const avail = f.clientWidth;
    if (avail >= DESIGN_W) {
      if (wrap) { wrap.replaceWith(mock); mock.style.cssText = ''; }
      f.classList.remove('zoomable');
      return;
    }
    if (!wrap) { wrap = document.createElement('div'); wrap.className = 'mock-fit'; mock.replaceWith(wrap); wrap.appendChild(mock); }
    mock.style.width = DESIGN_W + 'px';
    const scale = avail / DESIGN_W;
    mock.style.transform = 'scale(' + scale + ')';
    wrap.style.height = Math.ceil(mock.offsetHeight * scale) + 'px';
    f.classList.add('zoomable');
  });
}
function openLightbox(f) {
  const lb = document.createElement('div'); lb.className = 'lightbox';
  const top = document.createElement('div'); top.className = 'lb-top';
  const cap = document.createElement('span'); cap.textContent = f.dataset.cap + ' (좌우로 밀어 보기)';
  const close = document.createElement('button'); close.textContent = '닫기 ✕';
  top.append(cap, close);
  const body = document.createElement('div'); body.className = 'lb-body';
  const img = f.querySelector(':scope > img');
  if (img && img.style.display !== 'none') { const c = img.cloneNode(); c.style.display = ''; body.appendChild(c); }
  else { const m = f.querySelector('.mock').cloneNode(true); m.style.transform = ''; m.style.position = 'relative'; m.style.width = DESIGN_W + 'px'; body.appendChild(m); }
  lb.append(top, body); document.body.appendChild(lb); document.body.style.overflow = 'hidden';
  const shut = () => { lb.remove(); document.body.style.overflow = ''; };
  close.onclick = shut; lb.addEventListener('click', e => { if (e.target === lb) shut(); });
}
document.querySelectorAll('figure.shot').forEach(f => f.addEventListener('click', e => {
  if (e.target.closest('.tog')) return;
  if (f.classList.contains('zoomable') || window.innerWidth <= 860) openLightbox(f);
}));
window.addEventListener('resize', fitMocks);
window.addEventListener('load', fitMocks);
fitMocks();

if (list) {
  const t = document.createElement('table'); t.className = 't';
  t.innerHTML = '<tr><th>화면 ID(파일 이름)</th><th>찍을 화면</th></tr>';
  rows.forEach(([id, cap]) => { const tr = t.insertRow(); tr.insertCell().textContent = id + '.png'; tr.insertCell().textContent = cap; });
  list.appendChild(t);
}
