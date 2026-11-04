"""미리보기 이미지(1200x630) 만들기 — 브라우저 없이도 동작(Claude 대화창용).
1) Playwright(Python)가 있으면 og.html(assets/og_template.html을 채운 것)을 그대로 렌더링
2) 없으면 Pillow로 같은 디자인을 직접 그림(한글 글꼴 자동 탐색)

사용 A (HTML 렌더링): python3 make_og.py --html og.html --out og_image.jpg
사용 B (Pillow로 그리기):
  python3 make_og.py --out og_image.jpg --eyebrow "대한변리사회 회원서비스실 · 실습 교안" \
     --title "구글 시트 + Apps Script로" --accent "회원 업무 자동화" \
     --desc "화면 순서대로 따라 하면 중복 확인부터 메일 발송까지" \
     --tags "🔁 중복 확인,✉️ 선정 메일,📊 통합 현황" --card-title "오늘 따라 할 순서" --steps "실습 시트 만들기|메뉴 추가·권한 승인|버튼으로 자동 처리"
--html을 줬는데 Playwright가 없으면 B 방식에 필요한 값이 없으므로 오류를 알려준다.
"""
import argparse
import glob
import re
import subprocess
import sys
from pathlib import Path

W, H = 1200, 630


def render_html(html_path, out):
    src = Path(html_path).read_text(encoding="utf-8")
    left = re.findall(r"\{\{[^}]+\}\}", src)
    if left:
        sys.exit(f"og.html에 채우지 않은 자리표시가 있습니다: {left[:5]}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        pg.goto(Path(html_path).resolve().as_uri())
        pg.wait_for_timeout(300)
        kw = {"type": "jpeg", "quality": 88} if str(out).lower().endswith((".jpg", ".jpeg")) else {}
        pg.screenshot(path=str(out), **kw)
        b.close()


def find_font(bold=True):
    names = ["NotoSansCJK-Bold", "NotoSansKR-Bold", "NanumGothicBold", "NanumBarunGothicBold", "malgunbd"] if bold else \
            ["NotoSansCJK-Regular", "NotoSansKR-Regular", "NanumGothic", "NanumBarunGothic", "malgun"]
    cands = []
    for pat in ("/usr/share/fonts/**/*", "/usr/local/share/fonts/**/*", str(Path.home() / ".fonts/**/*"),
                "/Library/Fonts/*", "/System/Library/Fonts/**/*", "C:/Windows/Fonts/*"):
        cands += glob.glob(pat, recursive=True)
    for n in names:
        for c in cands:
            if n.lower() in Path(c).name.lower():
                return c
    try:  # fontconfig에 한글 글꼴을 물어본다
        r = subprocess.run(["fc-list", ":lang=ko", "file"], capture_output=True, text=True, timeout=10).stdout.split("\n")
        files = [x.split(":")[0] for x in r if x.strip()]
        files.sort(key=lambda x: (0 if ("bold" in x.lower()) == bold else 1, 0 if "unifont" not in x.lower() else 2))
        if files:
            return files[0]
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def draw_pillow(a, out):
    from PIL import Image, ImageDraw, ImageFont
    fb, fr = find_font(True), find_font(False) or find_font(True)
    if not fb:
        sys.exit("한글 글꼴을 찾지 못했습니다. 글꼴(예: fonts-noto-cjk, 나눔고딕)을 설치하거나 --html 방식을 쓰세요.")
    F = lambda path, size: ImageFont.truetype(path, size)
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):          # 남색 대각선 그라데이션
        for x in range(0, W, 4):
            t = (x / W * 0.6 + y / H * 0.4)
            c = (int(8 + 21 * t), int(21 + 37 * t), int(54 + 68 * t))
            for k in range(4):
                if x + k < W:
                    px[x + k, y] = c
    d = ImageDraw.Draw(img)
    gold, white, soft = (232, 205, 138), (255, 255, 255), (220, 226, 240)
    # 배지
    fe = F(fb, 21)
    tw = d.textlength(a.eyebrow, font=fe)
    d.rounded_rectangle([70, 68, 70 + tw + 40, 112], radius=22, outline=(150, 165, 200), width=2, fill=(40, 60, 105))
    d.text((90, 76), a.eyebrow, font=fe, fill=white)
    # 제목: 오른쪽 카드와 겹치지 않게 폭에 맞춰 글자 크기 자동 조정
    maxw = 640
    size = 58
    while size > 36 and max(d.textlength(a.title, font=F(fb, size)), d.textlength(a.accent, font=F(fb, size))) > maxw:
        size -= 2
    ft = F(fb, size)
    d.text((70, 140), a.title, font=ft, fill=white)
    d.text((70, 140 + int(size * 1.22)), a.accent, font=ft, fill=gold)
    y = 140 + int(size * 2.6) + 16
    fd = F(fr, 25)
    line, lines = "", []
    for word in a.desc.split(" "):        # 설명 줄바꿈
        if d.textlength((line + " " + word).strip(), font=fd) > maxw:
            lines.append(line); line = word
        else:
            line = (line + " " + word).strip()
    lines.append(line)
    for ln in lines[:2]:
        d.text((70, y), ln, font=fd, fill=soft); y += 38
    # 태그
    fg = F(fb, 20)
    x = 70
    for tag in [t.strip() for t in a.tags.split(",") if t.strip()][:3]:
        tag = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]", "", tag).strip()  # 이모지는 글꼴에 없을 수 있어 제거
        w = d.textlength(tag, font=fg) + 32
        d.rounded_rectangle([x, 528, x + w, 572], radius=10, fill=(35, 55, 100), outline=(90, 110, 155))
        d.text((x + 16, 537), tag, font=fg, fill=white); x += w + 12
    # 오른쪽 카드: 단계 요약
    cx, cy, cw = 760, 110, 380
    steps = [s.strip() for s in a.steps.split("|") if s.strip()][:4]
    ch = 70 + 56 * len(steps)
    d.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=16, fill=white)
    d.text((cx + 22, cy + 20), a.card_title, font=F(fb, 21), fill=(11, 31, 75))
    fs = F(fr, 19)
    for i, s in enumerate(steps):
        yy = cy + 66 + i * 56
        d.ellipse([cx + 22, yy, cx + 54, yy + 32], fill=(229, 50, 45))
        num = str(i + 1)
        d.text((cx + 38 - d.textlength(num, font=F(fb, 18)) / 2, yy + 5), num, font=F(fb, 18), fill=white)
        d.text((cx + 68, yy + 4), s, font=fs, fill=(32, 33, 36))
        if i < len(steps) - 1:
            d.line([cx + 22, yy + 44, cx + cw - 22, yy + 44], fill=(235, 235, 235), width=1)
    kw = {"quality": 88} if str(out).lower().endswith((".jpg", ".jpeg")) else {}
    img.save(out, **kw)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--html")
    ap.add_argument("--eyebrow", default="실습 교안")
    ap.add_argument("--title", default="")
    ap.add_argument("--accent", default="")
    ap.add_argument("--desc", default="")
    ap.add_argument("--tags", default="")
    ap.add_argument("--card-title", dest="card_title", default="따라 할 순서")
    ap.add_argument("--steps", default="")
    a = ap.parse_args()
    if a.html:
        try:
            render_html(a.html, a.out)
            print("wrote", a.out, "(HTML 렌더링)")
            sys.exit(0)
        except ImportError:
            if not a.title:
                sys.exit("Playwright가 없어 HTML을 렌더링할 수 없습니다. --title/--accent 등을 주면 Pillow로 그립니다.")
    draw_pillow(a, a.out)
    print("wrote", a.out, "(Pillow)")
