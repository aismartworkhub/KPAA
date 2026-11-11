"""구글폼 주소로 QR(벡터 SVG)을 만든다.
   python3 review-form/make_qr.py https://forms.gle/XXXX
   → assets/review_qr.svg (배너 04에 들어가는 QR), review-form/form_url.txt
   이후 node render.mjs 04_후기이벤트_X배너.html 로 다시 출력"""
import sys, os, segno
here = os.path.dirname(os.path.abspath(__file__))
url = sys.argv[1].strip()
assert url.startswith('https://'), 'https:// 로 시작하는 주소를 넣어 주세요'
qr = segno.make(url, error='q')            # 오류 복원 25% — 인쇄 얼룩·구김에도 읽힘
qr.save(os.path.join(here, '..', 'assets', 'review_qr.svg'), kind='svg', scale=10, border=2, dark='#0A1433', light='#FFFFFF', xmldecl=False)
open(os.path.join(here, 'form_url.txt'), 'w').write(url + '\n')
print('QR 생성:', url, '| 버전', qr.version, '| 모듈', qr.symbol_size(border=0)[0])
