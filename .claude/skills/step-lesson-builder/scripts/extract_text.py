"""올려준 자료에서 텍스트 뽑기 — 교안 재료(회의록·업무 절차·요청 메일·규정·엑셀) 파악용.
사용: python3 extract_text.py <파일> [<파일> ...]
지원: .hwp(한글 5.0) .hwpx .pdf .docx .xlsx/.xlsm .csv .txt .md
- 엑셀은 시트별로 머리행·행 수·앞부분 몇 줄만 보여준다(개인정보가 많을 수 있으므로 전체를 출력하지 않는다).
- 필요한 패키지가 없으면 설치 명령을 안내한다: pip install olefile pypdf python-docx openpyxl
"""
import html
import re
import struct
import sys
import zipfile
import zlib
from pathlib import Path


def hwp(path):
    import olefile
    ole = olefile.OleFileIO(str(path))
    try:
        hdr = ole.openstream("FileHeader").read()
        if hdr[36] & 0x02:
            return "(암호가 걸린 HWP — 읽을 수 없음)"
        comp = bool(hdr[36] & 1)
        secs = sorted((s for s in ole.listdir() if s[0] == "BodyText"), key=lambda s: int(s[1].replace("Section", "")))
        out = []
        for s in secs:
            d = ole.openstream(s).read()
            if comp:
                d = zlib.decompress(d, -15)
            i = 0
            while i + 4 <= len(d):
                h = struct.unpack_from("<I", d, i)[0]; i += 4
                tag, size = h & 0x3FF, (h >> 20) & 0xFFF
                if size == 0xFFF:
                    size = struct.unpack_from("<I", d, i)[0]; i += 4
                if tag == 67:
                    raw, j, ch = d[i:i + size], 0, []
                    while j + 2 <= len(raw):
                        c = struct.unpack_from("<H", raw, j)[0]
                        if c in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23):
                            j += 16; continue
                        if c in (10, 13):
                            ch.append("\n")
                        elif c >= 32:
                            ch.append(chr(c))
                        j += 2
                    out.append("".join(ch))
                i += size
        return "".join(out)
    finally:
        ole.close()


def hwpx(path):
    z = zipfile.ZipFile(str(path))
    out = []
    for n in sorted(x for x in z.namelist() if re.match(r"Contents/section\d+\.xml$", x)):
        xml = z.read(n).decode("utf-8", "replace")
        for para in xml.split("</hp:p>"):
            t = "".join(re.findall(r"<hp:t(?:\s[^>]*)?>([^<]*)</hp:t>", para))
            if t.strip():
                out.append(html.unescape(t))
    return "\n".join(out)


def pdf(path):
    from pypdf import PdfReader
    r = PdfReader(str(path))
    return "\n".join(f"[{i}쪽]\n{(p.extract_text() or '').strip()}" for i, p in enumerate(r.pages, 1))


def docx_(path):
    import docx
    d = docx.Document(str(path))
    parts = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            parts.append(" | ".join(c.text for c in row.cells))
    return "\n".join(parts)


def xlsx(path, preview=5):
    import openpyxl
    wb = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        rows = [r for r in ws.iter_rows(values_only=True) if any(v not in (None, "") for v in r)]
        out.append(f"=== 시트 [{ws.title}] {len(rows)}행 ===")
        for r in rows[:preview]:
            out.append(" | ".join("" if v is None else str(v) for v in r))
        if len(rows) > preview:
            out.append(f"… (나머지 {len(rows) - preview}행 생략 — 개인정보 보호를 위해 미리보기만 표시)")
    return "\n".join(out)


def text(path):
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", "replace")


HANDLERS = {".hwp": hwp, ".hwpx": hwpx, ".pdf": pdf, ".docx": docx_, ".xlsx": xlsx, ".xlsm": xlsx,
            ".csv": text, ".txt": text, ".md": text}

if __name__ == "__main__":
    for f in sys.argv[1:]:
        p = Path(f)
        fn = HANDLERS.get(p.suffix.lower())
        print(f"\n##### {p.name}")
        if not fn:
            print("(지원하지 않는 형식)"); continue
        try:
            print(fn(p))
        except ImportError as e:
            print(f"(패키지 필요: {e.name}) → pip install olefile pypdf python-docx openpyxl")
        except Exception as e:  # 자료 하나가 깨져도 나머지는 계속
            print(f"(읽기 실패: {e})")
