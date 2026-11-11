"""AISH 로고(PNG)를 색상별로 벡터(SVG)로 변환한다.
   python3 trace_logo.py  → aish_logo.svg(원래 색), aish_logo_white.svg(어두운 배경용)"""
import numpy as np, potrace, os
from PIL import Image
here = os.path.dirname(os.path.abspath(__file__))
im = Image.open(os.path.join(here, 'aish_logo_원본.png')).convert('RGB')
S = 5
big = np.asarray(im.resize((im.width*S, im.height*S), Image.LANCZOS)).astype(float)
cols = {'navy': (0,47,103), 'cyan': (22,193,243), 'gray': (135,136,139), 'white': (255,255,255)}
names = list(cols)
d = np.stack([((big - np.array(cols[n]))**2).sum(-1) for n in names])
lab = d.argmin(0)
ys, xs = np.where(lab != names.index('white'))
y0, y1, x0, x1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1
pad = 4*S; y0-=pad; x0-=pad; y1+=pad; x1+=pad
lab = lab[y0:y1, x0:x1]
H, W = lab.shape
paths = {}
for n in ['navy', 'cyan', 'gray']:
    bm = potrace.Bitmap(lab != names.index(n))  # potracer: 0(어두움)=칠할 영역
    pl = bm.trace(turdsize=40, alphamax=1.0, opticurve=True, opttolerance=0.2)
    parts = []
    for c in pl:
        parts.append(f"M{c.start_point.x:.1f},{c.start_point.y:.1f}")
        for s in c.segments:
            if s.is_corner:
                parts.append(f"L{s.c.x:.1f},{s.c.y:.1f}L{s.end_point.x:.1f},{s.end_point.y:.1f}")
            else:
                parts.append(f"C{s.c1.x:.1f},{s.c1.y:.1f} {s.c2.x:.1f},{s.c2.y:.1f} {s.end_point.x:.1f},{s.end_point.y:.1f}")
        parts.append('Z')
    paths[n] = ''.join(parts)
def svg(fill):
    body = ''.join(f'<path fill="{fill[n]}" fill-rule="evenodd" d="{paths[n]}"/>' for n in ['gray','navy','cyan'])
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}">{body}</svg>'
open(os.path.join(here,'aish_logo.svg'),'w').write(svg({'navy':'#002F67','cyan':'#16C1F3','gray':'#87888B'}))
open(os.path.join(here,'aish_logo_white.svg'),'w').write(svg({'navy':'#FFFFFF','cyan':'#16C1F3','gray':'#D5DCEE'}))
print('viewBox', W, H, 'ratio', round(W/H,3))
